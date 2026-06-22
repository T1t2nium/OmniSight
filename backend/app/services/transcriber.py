"""faster-whisper speech-to-text wrapper — CPU-bound, runs in thread pool.

Downloads models from ModelScope (魔搭, China-native, fast) with automatic
fallback to HuggingFace. Model loading + download runs in a background thread
so the event loop stays responsive (Ctrl+C works during download).
"""

import asyncio
import logging
import os

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_MODELSCOPE_REPO = "keepitsimple/faster-whisper-{model_size}"


class AudioTranscriber:
    """Wraps faster-whisper WhisperModel for async transcription.

    Model is loaded lazily on first use — startup is instant, and
    long downloads run in a thread pool so the event loop stays alive.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str | None = None,
        device: str = "cpu",
    ) -> None:
        self._model_size = model_size
        self._language = language
        self._device = device
        self._model: WhisperModel | None = None

    async def _ensure_model(self) -> None:
        """Load (and download if needed) the WhisperModel in a background thread."""
        if self._model is not None:
            return

        model_path = self._download_from_modelscope(self._model_size)
        model_id = model_path or self._model_size
        compute_type = "float16" if self._device == "cuda" else "auto"
        source = "ModelScope" if model_path else "HuggingFace"

        logger.info(
            "Loading faster-whisper '%s' from %s (device=%s, compute_type=%s)...",
            self._model_size, source, self._device, compute_type,
        )

        # Run the (possibly very slow) model download + load in a thread.
        # This keeps the asyncio event loop responsive so Ctrl+C works.
        self._model = await asyncio.to_thread(
            WhisperModel,
            model_id,
            device=self._device,
            compute_type=compute_type,
        )
        logger.info("faster-whisper model ready")

    def _download_from_modelscope(self, model_size: str) -> str | None:
        """Download model from ModelScope (魔搭). Returns local path or None."""
        try:
            from modelscope import snapshot_download
        except ImportError:
            return None

        repo_id = _MODELSCOPE_REPO.format(model_size=model_size)
        try:
            logger.info(
                "Downloading '%s' from ModelScope: %s ...", model_size, repo_id,
            )
            model_dir = snapshot_download(repo_id)
            logger.info("ModelScope download complete: %s", model_dir)
            return model_dir
        except Exception as exc:
            logger.warning("ModelScope download failed: %s", exc)
            return None

    async def transcribe(
        self, audio: np.ndarray
    ) -> tuple[str, str, float]:
        """Transcribe a float32 audio array (16kHz, normalized -1..1).

        Loads the model on first call (download + init runs in thread pool).
        """
        await self._ensure_model()

        segments, info = await asyncio.to_thread(
            self._model.transcribe,
            audio,
            language=self._language,
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
