"""Sherpa-onnx TTS service — local ONNX-based text-to-speech.

Uses sherpa-onnx (https://github.com/k2-fsa/sherpa-onnx) with the
matcha-icefall-zh-baker model. Chinese text processing is fully built-in
(FST normalization + lexicon), no runtime espeak-ng dependency.

This avoids the root cause of Chinese G2P quality issues in Piper and
Kokoro — both of which rely on espeak-ng for runtime phonemization.

Sentence streaming: the orchestrator detects sentence boundaries in the
LLM output, calls synthesize() per sentence, and sends each PCM16 chunk
to the frontend for playback via Web Audio API.

Model: matcha-icefall-zh-baker (Apache 2.0, 73 MB, 22050 Hz).
"""

import asyncio
import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# sherpa-onnx model archive for matcha-icefall-zh-baker
# Download: scripts/download-sherpa-tts.ps1
# Source: https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models
REQUIRED_MODEL_FILES = [
    "model-steps-3.onnx",      # acoustic model
    "vocos-22khz-univ.onnx",   # vocoder
    "lexicon.txt",             # Chinese word→phoneme lexicon
    "tokens.txt",              # token list
]
REQUIRED_MODEL_DIRS = [
    "dict",                    # multi-word pronunciation dictionary
]


class SherpaTTSError(Exception):
    """Raised when sherpa-onnx TTS synthesis or initialization fails."""


class SherpaTTS:
    """Async wrapper around sherpa-onnx OfflineTts (matcha-icefall-zh-baker).

    Uses sherpa-onnx Python API for direct ONNX inference. The model is
    loaded in a thread pool during initialize() to avoid blocking the
    event loop. Synthesis also runs in a thread pool.

    Usage:
        tts = SherpaTTS(model_dir="backend/models/sherpa-voices/matcha-icefall-zh-baker")
        await tts.initialize()
        pcm_bytes, sample_rate = await tts.synthesize("你好世界")
    """

    def __init__(
        self,
        model_dir: str = "",
        speed: float = 1.0,
        num_threads: int = 4,
    ) -> None:
        """
        Args:
            model_dir: Path to the extracted matcha-icefall-zh-baker model archive.
            speed: Speech speed (0.5–2.0, default 1.0).
            num_threads: ONNX Runtime thread count for CPU inference.
        """
        self._model_dir = model_dir
        self._speed = speed
        self._num_threads = num_threads
        self._tts = None  # sherpa_onnx.OfflineTts instance
        self._ready = False

    # ---- public API ----

    @property
    def ready(self) -> bool:
        """True if the model is loaded and ready for synthesis."""
        return self._ready

    @property
    def sample_rate(self) -> int:
        """Native sample rate of matcha-icefall-zh-baker output (22050 Hz)."""
        return 22050

    async def initialize(self) -> None:
        """Load the sherpa-onnx model and validate with a smoke test.

        The model is loaded in a thread pool because ONNX Runtime's
        session creation is synchronous.

        Raises SherpaTTSError if model files are missing or invalid.
        """
        # Validate model directory and required files
        if not self._model_dir:
            raise SherpaTTSError(
                "sherpa-onnx model directory not configured. "
                "Set SHERPA_MODEL_DIR in .env.\n"
                "Download: scripts/download-sherpa-tts.ps1"
            )
        model_path = Path(self._model_dir)
        if not model_path.is_dir():
            raise SherpaTTSError(
                f"sherpa-onnx model directory not found: {self._model_dir}"
            )
        for fname in REQUIRED_MODEL_FILES:
            fpath = model_path / fname
            if not fpath.is_file():
                raise SherpaTTSError(
                    f"Missing model file: {fpath}\n"
                    f"Re-download from: https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models"
                )
        for dname in REQUIRED_MODEL_DIRS:
            dpath = model_path / dname
            if not dpath.is_dir():
                logger.warning("Optional model directory missing: %s", dpath)

        # Load model in thread pool (synchronous ONNX session creation)
        try:
            self._tts = await asyncio.to_thread(self._load_model)
        except Exception as exc:
            logger.exception("sherpa-onnx model loading failed")
            raise SherpaTTSError(
                f"sherpa-onnx initialization failed: {type(exc).__name__}: {exc}"
            ) from exc

        # Smoke test
        try:
            pcm, _ = await self.synthesize("你好")
            if not pcm or len(pcm) < 500:
                raise SherpaTTSError(
                    f"sherpa-onnx smoke test produced too little output ({len(pcm)} bytes)"
                )
        except SherpaTTSError:
            raise
        except Exception as exc:
            logger.exception("sherpa-onnx smoke test failed")
            raise SherpaTTSError(
                f"sherpa-onnx smoke test failed: {type(exc).__name__}: {exc}"
            ) from exc

        self._ready = True
        logger.info(
            "sherpa-onnx TTS ready: model=matcha-icefall-zh-baker, "
            "sample_rate=%d Hz, num_threads=%d",
            self.sample_rate,
            self._num_threads,
        )

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Synthesize text to PCM16 audio bytes.

        Args:
            text: The text to speak. Empty/silent strings return empty audio.

        Returns:
            (pcm16_bytes, sample_rate) — raw 16-bit mono PCM at 22050 Hz.
        """
        if not text or not text.strip():
            return b"", self.sample_rate

        if not self._tts:
            raise SherpaTTSError(
                "sherpa-onnx TTS not initialized. Call initialize() first."
            )

        logger.debug("sherpa-onnx synthesizing: %r", text[:80])

        try:
            audio = await asyncio.to_thread(
                self._tts.generate,
                text,
                sid=0,           # matcha-icefall-zh-baker has single speaker
                speed=self._speed,
            )
            # audio.samples: numpy float32 array in [-1, 1]
            # audio.sample_rate: int (22050 for matcha-icefall-zh-baker)
            pcm_bytes = _float32_to_pcm16(audio.samples)
            return pcm_bytes, audio.sample_rate

        except asyncio.CancelledError:
            logger.debug("sherpa-onnx synthesis cancelled")
            raise
        except Exception as exc:
            logger.exception("sherpa-onnx synthesis failed")
            raise SherpaTTSError(
                f"sherpa-onnx synthesis failed: {type(exc).__name__}: {exc}"
            ) from exc

    def _load_model(self):
        """Load sherpa-onnx OfflineTts instance (called in thread pool)."""
        import sherpa_onnx

        model_dir = self._model_dir

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=str(Path(model_dir) / "model-steps-3.onnx"),
                    vocoder=str(Path(model_dir) / "vocos-22khz-univ.onnx"),
                    lexicon=str(Path(model_dir) / "lexicon.txt"),
                    tokens=str(Path(model_dir) / "tokens.txt"),
                    dict_dir=str(Path(model_dir) / "dict"),
                ),
                provider="cpu",
                num_threads=self._num_threads,
            ),
            max_num_sentences=1,  # sentence-level for streaming
        )

        return sherpa_onnx.OfflineTts(config)


# ---- Helpers ----

def _float32_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float32 audio samples in [-1, 1] to PCM16 bytes.

    Clips values outside [-1, 1] to prevent overflow.
    """
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()
