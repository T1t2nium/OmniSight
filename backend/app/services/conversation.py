"""AI pipeline orchestrator — chains transcription → LLM → TTS → response streaming.

PR 4: Added Piper TTS sentence-level streaming with interrupt support.
Instead of having the frontend run SpeechSynthesis on the final LLM text,
the backend synthesizes PCM16 audio per-sentence and sends it via WebSocket.
"""

import asyncio
import base64
import logging
import re
import time
from typing import Awaitable, Callable

import httpx
import numpy as np

from app.services.transcriber import AudioTranscriber
from app.services.ollama_client import OllamaClient
from app.services.tts import PiperTTS, split_sentences
from app.services.sherpa_tts import SherpaTTS

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
        tts: PiperTTS | SherpaTTS | None = None,
    ) -> None:
        self._transcriber = transcriber
        self._ollama = ollama
        self._tts = tts

    @property
    def tts_provider(self) -> str:
        """Return 'sherpa', 'piper', or 'browser' so the frontend knows what to expect."""
        if self._tts and self._tts.ready:
            if isinstance(self._tts, SherpaTTS):
                return "sherpa"
            return "piper"
        return "browser"

    async def process_utterance(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        latest_frame_b64: str | None,
        history: list[dict] | None,
        send_fn: Callable[[str, dict], Awaitable[None]],
        status_fn: Callable[[str], Awaitable[None]],
    ) -> list[dict]:
        """Run the full AI pipeline on a single user utterance.

        Steps:
        1. Send 'thinking' status + tts_info (tells frontend which TTS to expect)
        2. Convert PCM16 → float32 numpy array
        3. Transcribe via faster-whisper (in thread pool)
        4. Send transcript to frontend
        5. Stream Ollama response as llm_response deltas, detect sentences
        6. Concurrent TTS synthesis for collected sentences
        7. Send 'idle' status on completion

        Returns:
            Updated conversation history for the next turn.
        """
        await status_fn("thinking")

        try:
            # ---- Tell frontend which TTS provider to expect ----
            await send_fn("tts_info", {"provider": self.tts_provider})

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
            t0 = time.perf_counter()
            await send_fn("transcript", {
                "text": text,
                "language": language,
                "duration_ms": duration * 1000,
            })
            t1 = time.perf_counter()
            logger.debug("Timing: send transcript took %.3fs", t1 - t0)

            # ---- Step 5: Add user message to history ----
            history = history or []
            history.append({"role": "user", "content": text})

            # ---- Step 6: Stream LLM + feed TTS queue ----
            # Producer-consumer: LLM pushes complete sentences into a queue;
            # a single TTS worker consumes them sequentially. This decouples
            # LLM streaming from TTS synthesis — the worker starts on the
            # first sentence while the LLM may still be generating later ones.
            await status_fn("speaking")
            t2 = time.perf_counter()
            logger.debug("Timing: setup before Ollama took %.3fs", t2 - t1)
            full_response = ""
            tts_pending_text = ""

            tts_ready = self._tts and self._tts.ready
            tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
            worker_task: asyncio.Task | None = None

            async def _tts_worker() -> None:
                """Consume sentences from queue, synthesize, send. Runs until sentinel."""
                while True:
                    sentence = await tts_queue.get()
                    if sentence is None:
                        tts_queue.task_done()
                        return
                    try:
                        await self._synthesize_and_send(sentence, send_fn)
                    finally:
                        tts_queue.task_done()

            if tts_ready:
                worker_task = asyncio.create_task(_tts_worker())

            try:
                # PR 5: Retry once on transient Ollama errors
                t3 = time.perf_counter()
                logger.info(
                    "Starting Ollama chat (image=%s, %.1f KB)",
                    "yes" if latest_frame_b64 else "no",
                    len(latest_frame_b64) / 1024 if latest_frame_b64 else 0,
                )
                for attempt in range(2):
                    try:
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

                            # Push complete sentences to TTS worker (non-blocking)
                            if tts_ready:
                                sentences, tts_pending_text = split_sentences(tts_pending_text)
                                for s in sentences:
                                    await tts_queue.put(s)
                        break  # Success — exit retry loop
                    except (httpx.TimeoutException, httpx.ConnectError) as e:
                        if attempt == 0:
                            logger.warning(
                                "Ollama transient error — retrying in 1s: %s", e
                            )
                            await asyncio.sleep(1)
                        else:
                            raise  # Final attempt failed — propagate

                # ---- Step 7: Flush remaining text + wait for TTS ----
                if tts_ready:
                    if tts_pending_text.strip():
                        await tts_queue.put(tts_pending_text.strip())
                    await tts_queue.put(None)  # sentinel
                    await tts_queue.join()     # wait until all sentences processed

            finally:
                # On cancellation or error, ensure worker stops
                if worker_task and not worker_task.done():
                    if tts_ready:
                        await tts_queue.put(None)  # unblock worker
                    worker_task.cancel()
                    try:
                        await worker_task
                    except asyncio.CancelledError:
                        pass

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
            # PR 5: do NOT re-raise — the outer asyncio.create_task has no
            # await-er, so the exception would only surface as an unhandled
            # Task exception in logs. The error message above is sufficient.
        finally:
            await status_fn("idle")

        return history

    async def _synthesize_and_send(
        self, text: str, send_fn: Callable[[str, dict], Awaitable[None]],
    ) -> None:
        """Synthesize a sentence via TTS, normalize volume, and send as tts_audio."""
        if not self._tts or not text.strip():
            return

        # Strip Markdown and non-speakable characters
        clean_text = _clean_for_tts(text)
        if not clean_text.strip():
            return

        # Log stripped characters for OOV diagnosis
        stripped = set(text) - set(clean_text) - {' ', '\n', '\r', '\t'}
        if stripped:
            logger.debug(
                "TTS cleaned: %d chars stripped: %r",
                len(text) - len(clean_text),
                ''.join(sorted(stripped))[:80],
            )
        else:
            logger.debug("TTS text (clean): %r", text[:100])

        try:
            pcm_bytes, sr = await self._tts.synthesize(clean_text)
            if not pcm_bytes:
                return

            # Normalize PCM16 peak level to avoid volume fluctuations
            pcm_bytes = _normalize_pcm16(pcm_bytes)

            pcm_b64 = base64.b64encode(pcm_bytes).decode("ascii")
            await send_fn("tts_audio", {
                "data": pcm_b64,
                "sample_rate": sr,
                "channels": 1,
                "text": clean_text,
            })
            logger.debug("TTS sent: %r (%d bytes, %d Hz)", clean_text[:60], len(pcm_bytes), sr)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("TTS synthesis failed for %r: %s", clean_text[:80], exc)


# ---- TTS text clean-up ----

# Markdown / formatting characters that Piper reads as literal text.
_TTS_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # Bold / italic markers
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),   # **bold** → bold
    (re.compile(r"\*(.+?)\*"),     r"\1"),   # *italic* → italic
    (re.compile(r"__(.+?)__"),     r"\1"),   # __bold__ → bold
    # List markers
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),   # - item → item
    (re.compile(r"^\s*\d+[.)]\s*", re.MULTILINE), ""), # 1. item → item
    # Standalone formatting chars (run after removing paired ones)
    (re.compile(r"\*+"), ""),   # leftover *** or *
    (re.compile(r"_{2,}"), ""), # leftover ___
    (re.compile(r"~{2,}"), ""), # ~~strikethrough~~
    # HTML/markdown remnants
    (re.compile(r"<[^>]+>"), ""),   # <tag>
    (re.compile(r"`{1,3}[^`]*`{1,3}"), ""),  # `code` or ```block```
    # Strip unwanted characters before they reach the TTS engine
    (re.compile(r"："), ""),    # fullwidth colon — not pronounceable
    (re.compile(r"[-—–]"), ""),  # dashes (hyphen, em-dash, en-dash)
    # Multiple spaces → single space
    (re.compile(r" {2,}"), " "),
    # Repeated punctuation cleanup
    (re.compile(r"\.{3,}"), "…"),  # …… → …
    (re.compile(r"！{2,}"), "！"),
    (re.compile(r"？{2,}"), "？"),
]

# Unicode ranges to KEEP in TTS text (everything else is stripped)
_TTS_ALLOWED_BLOCKS = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (Chinese)
    (0x3400, 0x4DBF),   # CJK Extension A
    (0x2000, 0x206F),   # General Punctuation
    (0x3000, 0x303F),   # CJK Symbols/Punctuation
    (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth Forms
    (0x0000, 0x007F),   # Basic Latin (ASCII)
    (0x0080, 0x00FF),   # Latin-1 Supplement
    (0x0100, 0x024F),   # Latin Extended
    (0xFE30, 0xFE4F),   # CJK Compatibility Forms
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
]


def _clean_for_tts(text: str) -> str:
    """Remove formatting and non-speakable characters from TTS text.

    Strips Markdown, HTML, emoji, control chars, and rare Unicode that
    the TTS lexicon cannot pronounce (causing OOV warnings).
    """
    result = text
    for pattern, replacement in _TTS_REPLACEMENTS:
        result = pattern.sub(replacement, result)

    # Filter to only characters the TTS engine can pronounce:
    # CJK Unified Ideographs (common Chinese), ASCII letters/numbers,
    # Chinese/English punctuation, and whitespace.
    cleaned_chars: list[str] = []
    for ch in result:
        cp = ord(ch)
        # Whitespace → space
        if ch in (' ', '\n', '\r', '\t', '　'):
            cleaned_chars.append(' ')
            continue
        # ASCII printable (letters, digits, basic punctuation)
        if 0x20 <= cp <= 0x7E:
            cleaned_chars.append(ch)
            continue
        # CJK Unified Ideographs — only the main block (common Chinese)
        if 0x4E00 <= cp <= 0x9FFF:
            cleaned_chars.append(ch)
            continue
        # CJK punctuation (。、，！？：；""''）
        if 0x3000 <= cp <= 0x303F:
            cleaned_chars.append(ch)
            continue
        # Fullwidth punctuation and Latin (！＂＃＄％)
        if 0xFF00 <= cp <= 0xFF0F:
            cleaned_chars.append(ch)
            continue
        # Fullwidth digits and uppercase (０１２３ＡＢＣ)
        if 0xFF10 <= cp <= 0xFF3F:
            cleaned_chars.append(ch)
            continue
        # Fullwidth lowercase (ａｂｃ)
        if 0xFF41 <= cp <= 0xFF5E:
            cleaned_chars.append(ch)
            continue
        # Everything else: emoji, symbols, rare CJK, control chars → dropped

    result = ''.join(cleaned_chars)
    # Collapse whitespace
    result = re.sub(r'\s+', ' ', result)
    return result.strip()

# Remove the Unicode block list since we inline the logic above
_TTS_ALLOWED_BLOCKS = []  # kept for backward compat, unused


def _normalize_pcm16(pcm_bytes: bytes, target_peak: float = 0.85) -> bytes:
    """Peak-normalize PCM16 audio to smooth inter-sentence volume.

    Args:
        pcm_bytes: Raw PCM16 (int16 little-endian) audio data.
        target_peak: Target peak level (0.0–1.0, default 0.85).

    Returns:
        Normalized PCM16 bytes at the target peak level.
    """
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    peak = float(np.max(np.abs(samples)))
    if peak < 100:  # silence or near-silence — don't amplify noise
        return pcm_bytes
    gain = target_peak * 32767.0 / peak
    normalized = np.clip(samples * gain, -32767, 32767).astype(np.int16)
    return normalized.tobytes()
