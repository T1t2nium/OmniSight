"""faster-whisper speech-to-text wrapper — CPU-bound, runs in thread pool."""

import asyncio
import logging
import os

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """Wraps faster-whisper WhisperModel for async transcription.

    The model runs synchronously and blocks the GIL, so all transcription
    calls are dispatched via asyncio.to_thread.

    Set HF_ENDPOINT env var or hf_endpoint in .env to use a mirror
    (e.g. https://hf-mirror.com for users in China).
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str | None = None,
        device: str = "cpu",
        hf_endpoint: str | None = None,
    ) -> None:
        # Apply HF mirror BEFORE creating WhisperModel (CTranslate2 reads
        # HF_ENDPOINT from the environment when downloading model files).
        if hf_endpoint:
            os.environ.setdefault("HF_ENDPOINT", hf_endpoint)
            logger.info("Using HF endpoint: %s", hf_endpoint)

        # Enable faster Rust-based downloads if available
        os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

        self._model_size = model_size
        compute_type = "float16" if device == "cuda" else "auto"
        logger.info(
            "Loading faster-whisper model '%s' (device=%s, compute_type=%s)...",
            model_size, device, compute_type,
        )

        # WhisperModel handles downloading automatically via CTranslate2.
        # On first run, model.bin (~3GB for large-v3) will be downloaded
        # from HuggingFace. Set HF_ENDPOINT to a mirror for faster downloads.
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
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
            # Disable language-biased thresholds that filter out Chinese speech.
            no_speech_threshold=None,
            log_prob_threshold=None,
            compression_ratio_threshold=None,
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
