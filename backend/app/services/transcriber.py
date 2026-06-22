"""faster-whisper speech-to-text wrapper — CPU-bound, runs in thread pool."""

import asyncio
import logging
import os
import sys

import numpy as np
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

logger = logging.getLogger(__name__)

# HuggingFace repo for faster-whisper CTranslate2 models
_MODEL_REPO = "Systran/faster-whisper-{model_size}"


class AudioTranscriber:
    """Wraps faster-whisper WhisperModel for async transcription.

    Pre-downloads the model via huggingface_hub (with visible progress bar)
    before handing the cached path to WhisperModel, so users can see
    download progress instead of staring at a frozen terminal.

    The model runs synchronously and blocks the GIL, so all transcription
    calls are dispatched via asyncio.to_thread.
    """

    def __init__(self, model_size: str = "base", language: str | None = None, device: str = "cpu") -> None:
        self._model_size = model_size

        # — Pre-download model with progress bar —
        repo_id = _MODEL_REPO.format(model_size=model_size)
        logger.info(
            "Downloading faster-whisper '%s' from %s (first time may take 5-15 min for large models)...",
            model_size, repo_id,
        )
        try:
            model_dir = snapshot_download(
                repo_id=repo_id,
                resume_download=True,
                tqdm_class=None,  # auto-detect: uses tqdm if installed
            )
            logger.info("Model files cached at: %s", model_dir)
        except Exception as exc:
            logger.warning(
                "Pre-download failed (%s), falling back to built-in downloader. "
                "Progress may not be visible.",
                exc,
            )
            model_dir = None

        # — Load WhisperModel —
        compute_type = "float16" if device == "cuda" else "auto"
        logger.info(
            "Loading faster-whisper model '%s' (device=%s, compute_type=%s)...",
            model_size, device, compute_type,
        )
        # If we pre-downloaded, tell CTranslate2 to look there first.
        # download_root is where CTranslate2 searches for model files.
        if model_dir:
            # The parent of the snapshot dir is the HF cache root for this model
            download_root = os.path.dirname(model_dir)
        else:
            download_root = None

        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
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
