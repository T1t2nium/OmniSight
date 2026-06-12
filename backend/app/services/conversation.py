"""AI pipeline orchestrator — chains transcription → LLM → response streaming."""

import asyncio
import logging
from typing import Awaitable, Callable

import numpy as np

from app.services.transcriber import AudioTranscriber
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# Minimum audio length in samples to skip empty utterances (<20ms at 16kHz = 320 samples)
MIN_AUDIO_SAMPLES = 320


class AIPipelineError(Exception):
    """Raised when any stage of the AI pipeline fails."""


class ConversationOrchestrator:
    """Coordinates the full speech → vision → reply pipeline.

    Usage:
        orchestrator = ConversationOrchestrator(transcriber, ollama_client)
        await orchestrator.process_utterance(
            pcm_bytes=raw_pcm16,
            sample_rate=16000,
            latest_frame_b64=frame_jpeg_base64,
            history=conversation_history,
            send_fn=lambda type, payload: ws.send_json(...),
            status_fn=lambda status: ws.send_json(...),
        )
    """

    def __init__(
        self, transcriber: AudioTranscriber, ollama: OllamaClient
    ) -> None:
        self._transcriber = transcriber
        self._ollama = ollama

    async def process_utterance(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        latest_frame_b64: str | None,
        history: list[dict] | None,
        send_fn: Callable[[str, dict], Awaitable[None]],
        status_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """Run the full AI pipeline on a single user utterance.

        Steps:
        1. Send 'thinking' status
        2. Convert PCM16 → float32 numpy array
        3. Transcribe via faster-whisper (in thread pool)
        4. Send transcript to frontend
        5. Stream Ollama response as llm_response deltas
        6. Send 'idle' status on completion
        """
        await status_fn("thinking")

        try:
            # ---- Step 2: PCM16 → float32 ----
            audio_array = (
                np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Debug: save raw audio to disk for quality inspection
            _dump_debug_audio(pcm_bytes)

            # ---- Step 3: Transcribe ----
            text, language, duration = await self._transcriber.transcribe(audio_array)
            if not text:
                logger.info("Empty transcript — skipping LLM call")
                await status_fn("idle")
                return

            logger.info(
                "Transcript [%s] (%.1fs): %s", language, duration, text[:200]
            )

            # ---- Step 4: Send transcript ----
            await send_fn("transcript", {
                "text": text,
                "language": language,
                "duration_ms": duration * 1000,
            })

            # ---- Step 5: Add user message to history ----
            history = history or []
            history.append({"role": "user", "content": text})

            # ---- Step 6: Stream Ollama response ----
            full_response = ""
            async for chunk in self._ollama.chat(
                text, image_base64=latest_frame_b64, history=history
            ):
                full_response += chunk["delta"]
                await send_fn("llm_response", {
                    "delta": chunk["delta"],
                    "done": chunk["done"],
                    "total_duration": chunk.get("total_duration", 0.0),
                })

            # ---- Step 7: Store assistant response for next turn ----
            if full_response:
                history.append({"role": "assistant", "content": full_response})

        except asyncio.CancelledError:
            logger.info("AI pipeline cancelled for session")
            await status_fn("idle")
            raise
        except Exception as exc:
            logger.exception("AI pipeline error")
            await send_fn("error", {"message": f"AI error: {exc}"})
            raise AIPipelineError(str(exc)) from exc
        finally:
            await status_fn("idle")


def _dump_debug_audio(pcm_bytes: bytes) -> None:
    """Save raw PCM16 audio to a debug WAV file for quality inspection."""
    import wave
    import time
    from pathlib import Path

    debug_dir = Path("debug_audio")
    debug_dir.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = debug_dir / f"utterance_{timestamp}.wav"

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(16000)
        wf.writeframes(pcm_bytes)

    logger.info("Debug audio saved: %s (%.1f KB)", path, len(pcm_bytes) / 1024)

