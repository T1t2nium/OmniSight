"""AI pipeline orchestrator — chains transcription → LLM → TTS → response streaming.

PR 4: Added Piper TTS sentence-level streaming with interrupt support.
Instead of having the frontend run SpeechSynthesis on the final LLM text,
the backend synthesizes PCM16 audio per-sentence and sends it via WebSocket.
"""

import asyncio
import base64
import logging
from typing import Awaitable, Callable

import numpy as np

from app.services.transcriber import AudioTranscriber
from app.services.ollama_client import OllamaClient
from app.services.tts import PiperTTS, split_sentences

logger = logging.getLogger(__name__)

# Minimum audio length in samples to skip empty utterances (<20ms at 16kHz = 320 samples)
MIN_AUDIO_SAMPLES = 320


class AIPipelineError(Exception):
    """Raised when any stage of the AI pipeline fails."""


class ConversationOrchestrator:
    """Coordinates the full speech → vision → reply → speak pipeline.

    Usage:
        orchestrator = ConversationOrchestrator(transcriber, ollama_client, tts)
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
        self,
        transcriber: AudioTranscriber,
        ollama: OllamaClient,
        tts: PiperTTS | None = None,
    ) -> None:
        self._transcriber = transcriber
        self._ollama = ollama
        self._tts = tts

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
        6. For each complete sentence: synthesize TTS → send tts_audio
        7. Send remaining text as final TTS chunk
        8. Send 'idle' status on completion

        Cancellation (interrupt): if the asyncio task is cancelled mid-flight
        (e.g., user starts speaking again), the CancelledError propagates
        cleanly — subprocesses are killed, partial TTS is discarded.
        """
        await status_fn("thinking")

        try:
            # ---- Step 2: PCM16 → float32 ----
            audio_array = (
                np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )

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

            # ---- Step 6: Stream Ollama response (NEVER block on TTS) ----
            await status_fn("speaking")
            full_response = ""
            tts_pending_text = ""
            tts_sentences: list[str] = []  # collect, synthesize AFTER stream

            async for chunk in self._ollama.chat(
                text, image_base64=latest_frame_b64, history=history
            ):
                full_response += chunk["delta"]
                tts_pending_text += chunk["delta"]

                await send_fn("llm_response", {
                    "delta": chunk["delta"],
                    "done": chunk["done"],
                    "total_duration": chunk.get("total_duration", 0.0),
                })

                # Detect sentence boundaries but DON'T await TTS here —
                # Piper subprocess calls would block the LLM stream.
                if self._tts and self._tts.ready:
                    sentences, tts_pending_text = split_sentences(tts_pending_text)
                    tts_sentences.extend(sentences)

            # ---- Step 7: Synthesize TTS AFTER LLM stream is complete ----
            if tts_pending_text.strip():
                tts_sentences.append(tts_pending_text.strip())
            for sentence in tts_sentences:
                await self._synthesize_and_send(sentence, send_fn)

            # ---- Step 8: Store assistant response for next turn ----
            if full_response:
                history.append({"role": "assistant", "content": full_response})

        except asyncio.CancelledError:
            logger.info("AI pipeline cancelled (interrupt)")
            await status_fn("idle")
            raise
        except Exception as exc:
            logger.exception("AI pipeline error")
            await send_fn("error", {"message": f"AI error: {exc}"})
            raise AIPipelineError(str(exc)) from exc
        finally:
            await status_fn("idle")

    async def _synthesize_and_send(
        self, text: str, send_fn: Callable[[str, dict], Awaitable[None]],
    ) -> None:
        """Synthesize a sentence via Piper TTS and send as tts_audio."""
        if not self._tts or not text.strip():
            return

        try:
            pcm_bytes, sr = await self._tts.synthesize(text)
            if not pcm_bytes:
                return

            pcm_b64 = base64.b64encode(pcm_bytes).decode("ascii")
            await send_fn("tts_audio", {
                "data": pcm_b64,
                "sample_rate": sr,
                "channels": 1,
                "text": text,
            })
            logger.debug("TTS sent: %r (%d bytes, %d Hz)", text[:60], len(pcm_bytes), sr)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("TTS synthesis failed for %r: %s", text[:80], exc)
            # Non-fatal: TTS failure shouldn't break the text pipeline
