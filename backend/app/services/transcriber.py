"""faster-whisper speech-to-text wrapper — CPU-bound, runs in thread pool.

Downloads models from ModelScope (魔搭, China-native, fast) with automatic
fallback to HuggingFace for users outside China.
"""

import asyncio
import logging
import os

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# ModelScope model IDs for faster-whisper (same files as HF, hosted in China)
_MODELSCOPE_REPO = "keepitsimple/faster-whisper-{model_size}"


class AudioTranscriber:
    """Wraps faster-whisper WhisperModel for async transcription.

    Downloads models via ModelScope by default (fast in China).
    Falls back to HuggingFace if ModelScope is unavailable.

    The model runs synchronously and blocks the GIL, so all transcription
    calls are dispatched via asyncio.to_thread.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str | None = None,
        device: str = "cpu",
        use_modelscope: bool = True,
    ) -> None:
        self._model_size = model_size
        compute_type = "float16" if device == "cuda" else "auto"

        # — Try ModelScope download first —
        model_path: str | None = None
        if use_modelscope:
            model_path = self._download_from_modelscope(model_size)

        if model_path:
            logger.info("Loading from ModelScope cache: %s", model_path)
        else:
            logger.info(
                "Loading faster-whisper '%s' via HuggingFace (device=%s, compute_type=%s)...",
                model_size, device, compute_type,
            )

        self._model = WhisperModel(
            model_path or model_size,
            device=device,
            compute_type=compute_type,
        )
        self._language = language
        logger.info("faster-whisper model ready")

    def _download_from_modelscope(self, model_size: str) -> str | None:
        """Download model from ModelScope. Returns local path or None."""
        try:
            from modelscope.hub import snapshot_download
        except ImportError:
            logger.info("ModelScope SDK not installed, using HuggingFace")
            return None

        repo_id = _MODELSCOPE_REPO.format(model_size=model_size)
        cache_dir = os.path.join(
            os.path.expanduser("~"), ".cache", "modelscope", "hub"
        )
        try:
            logger.info(
                "Downloading faster-whisper '%s' from ModelScope: %s",
                model_size, repo_id,
            )
            model_dir = snapshot_download(
                repo_id,
                cache_dir=cache_dir,
            )
            logger.info("ModelScope download complete: %s", model_dir)
            return model_dir
        except Exception as exc:
            logger.warning(
                "ModelScope download failed (%s), falling back to HuggingFace",
                exc,
            )
            return None

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
