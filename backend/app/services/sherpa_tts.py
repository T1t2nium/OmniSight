"""Sherpa-onnx TTS service — local ONNX-based text-to-speech.

Uses sherpa-onnx (https://github.com/k2-fsa/sherpa-onnx) with the
vits-melo-tts-zh_en model by default. Chinese text processing is fully
built-in (FST normalization + lexicon), no runtime espeak-ng dependency.

This avoids the root cause of Chinese G2P quality issues in Piper and
Kokoro — both of which rely on espeak-ng for runtime phonemization.

Model auto-detection: if model.onnx exists → VITS; if model-steps-3.onnx
exists → Matcha (requires separate vocoder download).

Sentence streaming: the orchestrator detects sentence boundaries in the
LLM output, calls synthesize() per sentence, and sends each PCM16 chunk
to the frontend for playback via Web Audio API.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _fix_onnxruntime_dll() -> None:
    """Replace sherpa-onnx's bundled ORT 1.17 DLL with the system ORT >=1.20.

    sherpa-onnx 1.13.x ships with onnxruntime 1.17.1, but recent models
    require ORT 1.20+ (API version 24). We copy the system ORT DLL over
    the bundled one so model loading doesn't segfault.
    """
    try:
        import onnxruntime as ort
        import sherpa_onnx as _s

        ort_dll = Path(ort.__file__).parent / "capi" / "onnxruntime.dll"
        bundled_dll = Path(_s.__file__).parent / "lib" / "onnxruntime.dll"

        if not ort_dll.is_file() or not bundled_dll.is_file():
            return

        # Only replace if the system DLL is newer (different size)
        if ort_dll.stat().st_size != bundled_dll.stat().st_size:
            logger.info(
                "Patching ORT DLL: %d MB → %d MB",
                bundled_dll.stat().st_size // 1048576,
                ort_dll.stat().st_size // 1048576,
            )
            # Backup original
            bak = bundled_dll.with_suffix(".dll.bak")
            if not bak.exists():
                shutil.copy2(bundled_dll, bak)
            shutil.copy2(ort_dll, bundled_dll)
            logger.info("ORT DLL patched successfully")
    except Exception:
        logger.debug("ORT DLL patch skipped (non-critical)", exc_info=True)


# Auto-fix ORT DLL on module import
_fix_onnxruntime_dll()

# Required files per model type
VITS_REQUIRED_FILES = ["model.onnx", "lexicon.txt", "tokens.txt"]
MATCHA_REQUIRED_FILES = ["model-steps-3.onnx", "lexicon.txt", "tokens.txt"]
REQUIRED_MODEL_DIRS = ["dict"]


class SherpaTTSError(Exception):
    """Raised when sherpa-onnx TTS synthesis or initialization fails."""


class SherpaTTS:
    """Async wrapper around sherpa-onnx OfflineTts.

    Auto-detects model type from the model directory:
    - model.onnx → VITS (vits-melo-tts-zh_en, 44100 Hz, 163 MB)
    - model-steps-3.onnx → Matcha (matcha-icefall-zh-baker, 22050 Hz, 73 MB)

    Uses sherpa-onnx Python API for direct ONNX inference. The model is
    loaded in a thread pool during initialize().

    Usage:
        tts = SherpaTTS(model_dir="backend/models/sherpa-voices/vits-melo-tts-zh_en")
        await tts.initialize()
        pcm_bytes, sample_rate = await tts.synthesize("你好世界")
    """

    def __init__(
        self,
        model_dir: str = "",
        vocoder_dir: str = "",
        speed: float = 1.0,
        num_threads: int = 4,
    ) -> None:
        """
        Args:
            model_dir: Path to the model archive directory.
            vocoder_dir: For Matcha models — directory containing vocos-22khz-univ.onnx.
            speed: Speech speed (0.5–2.0, default 1.0).
            num_threads: ONNX Runtime thread count for CPU inference.
        """
        self._model_dir = model_dir
        self._vocoder_dir = vocoder_dir or str(
            Path(model_dir).parent if model_dir else ""
        )
        self._speed = speed
        self._num_threads = num_threads
        self._tts = None
        self._ready = False
        self._model_type = ""  # "vits" or "matcha"
        self._sample_rate = 0  # set during initialize()

    # ---- public API ----

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    async def initialize(self) -> None:
        """Detect model type, load the sherpa-onnx model, smoke test."""

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

        # Detect model type
        if (model_path / "model.onnx").is_file():
            self._model_type = "vits"
            required = VITS_REQUIRED_FILES
        elif (model_path / "model-steps-3.onnx").is_file():
            self._model_type = "matcha"
            required = MATCHA_REQUIRED_FILES
        else:
            raise SherpaTTSError(
                f"No recognized model file found in {self._model_dir}. "
                f"Expected model.onnx (VITS) or model-steps-3.onnx (Matcha)."
            )

        for fname in required:
            if not (model_path / fname).is_file():
                raise SherpaTTSError(
                    f"Missing model file: {model_path / fname}\n"
                    f"Re-download from: https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models"
                )
        for dname in REQUIRED_MODEL_DIRS:
            if not (model_path / dname).is_dir():
                logger.warning("Optional model directory missing: %s", model_path / dname)

        # Matcha needs a separate vocoder
        if self._model_type == "matcha":
            vocoder_filename = "vocos-22khz-univ.onnx"
            vocoder_path = Path(self._vocoder_dir) / vocoder_filename
            if not vocoder_path.is_file():
                vocoder_path = model_path.parent / vocoder_filename
            if not vocoder_path.is_file():
                raise SherpaTTSError(
                    f"Vocoder not found: {vocoder_filename}\n"
                    f"Download (51 MB): https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/{vocoder_filename}\n"
                    f"Place in: {self._vocoder_dir} or {model_path.parent}"
                )
            self._vocoder_path = str(vocoder_path)

        # Load model in thread pool
        try:
            self._tts = await asyncio.to_thread(self._load_model)
        except Exception as exc:
            logger.exception("sherpa-onnx model loading failed")
            raise SherpaTTSError(
                f"sherpa-onnx initialization failed: {type(exc).__name__}: {exc}"
            ) from exc

        # Smoke test
        try:
            pcm, sr = await self.synthesize("你好")
            self._sample_rate = sr
            if not pcm or len(pcm) < 500:
                raise SherpaTTSError(
                    f"Smoke test produced too little output ({len(pcm)} bytes)"
                )
        except SherpaTTSError:
            raise
        except Exception as exc:
            logger.exception("sherpa-onnx smoke test failed")
            raise SherpaTTSError(
                f"Smoke test failed: {type(exc).__name__}: {exc}"
            ) from exc

        self._ready = True
        logger.info(
            "sherpa-onnx TTS ready: type=%s, sample_rate=%d Hz",
            self._model_type, self._sample_rate,
        )

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Synthesize text to PCM16 audio bytes.

        Returns (pcm16_bytes, sample_rate). Empty text returns empty bytes.
        """
        if not text or not text.strip():
            return b"", self._sample_rate or 44100

        if not self._tts:
            raise SherpaTTSError(
                "sherpa-onnx TTS not initialized. Call initialize() first."
            )

        logger.debug("sherpa-onnx synthesizing: %r", text[:80])

        try:
            audio = await asyncio.to_thread(
                self._tts.generate, text, sid=0, speed=self._speed,
            )
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

        md = self._model_dir

        if self._model_type == "vits":
            model_config = sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=str(Path(md) / "model.onnx"),
                    lexicon=str(Path(md) / "lexicon.txt"),
                    tokens=str(Path(md) / "tokens.txt"),
                    dict_dir=str(Path(md) / "dict"),
                ),
                provider="cpu",
                num_threads=self._num_threads,
            )
        else:  # matcha
            model_config = sherpa_onnx.OfflineTtsModelConfig(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=str(Path(md) / "model-steps-3.onnx"),
                    vocoder=self._vocoder_path,
                    lexicon=str(Path(md) / "lexicon.txt"),
                    tokens=str(Path(md) / "tokens.txt"),
                    dict_dir=str(Path(md) / "dict"),
                ),
                provider="cpu",
                num_threads=self._num_threads,
            )

        config = sherpa_onnx.OfflineTtsConfig(
            model=model_config,
            max_num_sentences=1,
        )
        return sherpa_onnx.OfflineTts(config)


# ---- Helpers ----

def _float32_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float32 audio samples in [-1, 1] to PCM16 bytes."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()
