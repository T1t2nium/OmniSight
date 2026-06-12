"""faster-whisper speech-to-text wrapper — CPU-bound, runs in thread pool."""

import asyncio
import logging
import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """Wraps faster-whisper WhisperModel for async transcription.

    The model runs synchronously and blocks the GIL, so all calls are
    dispatched via asyncio.to_thread to avoid stalling the event loop.
    """

    def __init__(self, model_size: str = "base", language: str | None = None) -> None:
        logger.info(
            "Loading faster-whisper model '%s' (device=cpu, compute_type=auto)...",
            model_size,
        )
        self._model = WhisperModel(model_size, device="cpu", compute_type="auto")
        self._language = language
        logger.info("faster-whisper model ready")

    async def transcribe(
        self, audio: np.ndarray
    ) -> tuple[str, str, float]:
        """Transcribe a float32 audio array (16kHz, normalized -1..1).

        Returns:
            text: Transcribed text (stripped).
            language: Detected language code (e.g. 'en', 'zh').
            duration: Audio duration in seconds reported by the model.

        Runs in a thread pool to avoid blocking the asyncio event loop.
        """
        segments, info = await asyncio.to_thread(
            self._model.transcribe,
            audio,
            language=self._language,
        )
        text = "".join(seg.text for seg in segments)
        full_text = text.strip()
        if not full_text:
            logger.warning(
                "Empty transcript — audio_duration=%.1fs, detected_language=%s",
                info.duration, info.language,
            )
        return full_text, info.language, info.duration

    @property
    def language(self) -> str | None:
        return self._language
