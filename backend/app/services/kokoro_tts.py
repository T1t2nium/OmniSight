"""Kokoro 82M TTS service — local ONNX-based text-to-speech.

Uses kokoro-onnx (https://github.com/thewh1teagle/kokoro-onnx) for direct
Python API calls. This avoids the subprocess overhead of Piper and delivers
significantly better Chinese voice quality with 100+ voice options.

Sentence streaming: the orchestrator detects sentence boundaries in the
LLM output, calls synthesize() per sentence, and sends each PCM16 chunk
to the frontend for playback via Web Audio API.

Model: Kokoro 82M (Apache 2.0 license, commercial-friendly).
Default Chinese voice: zf_xiaobei (v1.0) or zf_001 (v1.1-zh).
"""

import asyncio
import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Kokoro v1.0 Chinese voices (8 total, 4F + 4M)
KOKORO_CHINESE_VOICES_V1 = [
    "zf_xiaobei",    # female
    "zf_xiaoni",     # female
    "zf_xiaoxiao",   # female
    "zf_xiaoyi",     # female
    "zm_yunjian",    # male
    "zm_yunxi",      # male
    "zm_yunxia",     # male
    "zm_yunyang",    # male
]

# Kokoro v1.1-zh adds 100+ numeric voices (zf_001-zf_099, zm_001-zm_100)

# Recommended default Chinese voices
DEFAULT_CHINESE_VOICE = "zf_xiaobei"   # v1.0 default (always available)
DEFAULT_CHINESE_VOICE_V11 = "zf_001"   # v1.1-zh default (higher quality if available)

# espeak-ng language codes used by kokoro-onnx for G2P
LANG_MAP = {
    "zh": "zh",        # Mandarin Chinese
    "en": "en-us",     # American English
    "auto": "zh",      # default to Chinese
}


class KokoroTTSError(Exception):
    """Raised when Kokoro TTS synthesis or initialization fails."""


class KokoroTTS:
    """Async wrapper around Kokoro 82M ONNX TTS engine.

    Uses kokoro-onnx for direct Python API calls (no subprocess needed).
    The ONNX model is loaded in a thread pool during initialize() to avoid
    blocking the event loop. Synthesis runs in a thread pool for the same
    reason.

    Usage:
        tts = KokoroTTS(
            model_path="kokoro-v1.0.int8.onnx",
            voices_path="voices-v1.0.bin",
            voice="zf_xiaobei",
            lang="zh",
        )
        await tts.initialize()
        pcm_bytes, sample_rate = await tts.synthesize("你好世界")
    """

    def __init__(
        self,
        model_path: str = "",
        voices_path: str = "",
        voice: str = DEFAULT_CHINESE_VOICE,
        speed: float = 1.0,
        lang: str = "zh",
    ) -> None:
        """
        Args:
            model_path: Path to kokoro .onnx model file.
            voices_path: Path to voices-v1.0.bin embeddings file.
            voice: Voice identifier (e.g. "zf_xiaobei", "zf_001").
            speed: Speech speed (0.5–2.0, default 1.0).
            lang: espeak-ng language code for G2P (e.g. "zh", "en-us").
        """
        self._model_path = model_path
        self._voices_path = voices_path
        self._voice = voice
        self._speed = speed
        self._lang = LANG_MAP.get(lang, lang)
        self._kokoro = None  # loaded in initialize()
        self._ready = False

    # ---- public API ----

    @property
    def ready(self) -> bool:
        """True if the Kokoro model is loaded and ready for synthesis."""
        return self._ready

    @property
    def sample_rate(self) -> int:
        """Native sample rate of Kokoro output (always 24000 Hz)."""
        return 24000

    @property
    def voices(self) -> list[str]:
        """List of available voice names (empty before initialize())."""
        if self._kokoro is None:
            return []
        return self._kokoro.get_voices()

    async def initialize(self) -> None:
        """Load the Kokoro ONNX model and validate voice availability.

        The model is loaded in a thread pool because ONNX Runtime's
        InferenceSession creation is synchronous and can take 1–3 seconds.

        Raises KokoroTTSError if model/voices files are missing or invalid.
        """
        # Validate file existence before loading
        if not self._model_path:
            raise KokoroTTSError(
                "Kokoro model path not configured. "
                "Set KOKORO_MODEL_PATH in .env to a .onnx model file.\n"
                "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases"
            )
        if not os.path.isfile(self._model_path):
            raise KokoroTTSError(
                f"Kokoro model not found: {self._model_path}"
            )
        if not self._voices_path:
            raise KokoroTTSError(
                "Kokoro voices path not configured. "
                "Set KOKORO_VOICES_PATH in .env to voices-v1.0.bin."
            )
        if not os.path.isfile(self._voices_path):
            raise KokoroTTSError(
                f"Kokoro voices file not found: {self._voices_path}"
            )

        # Load model in thread pool (synchronous ONNX session creation)
        try:
            self._kokoro = await asyncio.to_thread(self._load_model)
        except FileNotFoundError as exc:
            raise KokoroTTSError(
                f"Kokoro model file not found: {exc}"
            ) from exc
        except OSError as exc:
            raise KokoroTTSError(
                f"Failed to load Kokoro ONNX model (OS error): {exc}\n"
                "The model file may be corrupt or incompatible. "
                "Try re-downloading from GitHub releases."
            ) from exc
        except Exception as exc:
            logger.exception("Kokoro model loading failed")
            raise KokoroTTSError(
                f"Kokoro initialization failed: {type(exc).__name__}: {exc}"
            ) from exc

        # Validate the requested voice exists
        available = self._kokoro.get_voices()
        if self._voice not in available:
            # Try to find a suitable Chinese voice
            fallback = _find_chinese_voice(available)
            if fallback:
                logger.warning(
                    "Voice '%s' not found — falling back to '%s'",
                    self._voice, fallback,
                )
                self._voice = fallback
            else:
                raise KokoroTTSError(
                    f"Voice '{self._voice}' not found in {len(available)} available voices."
                )

        # Smoke test: synthesize a single character
        try:
            pcm, _ = await self.synthesize("好")
            if not pcm or len(pcm) < 100:
                raise KokoroTTSError(
                    "Kokoro smoke test produced no output — model may be broken."
                )
        except KokoroTTSError:
            raise
        except Exception as exc:
            logger.exception("Kokoro smoke test failed")
            raise KokoroTTSError(
                f"Kokoro smoke test failed: {type(exc).__name__}: {exc}"
            ) from exc

        self._ready = True
        logger.info(
            "Kokoro TTS ready: model=%s, voice=%s, voices_available=%d",
            Path(self._model_path).name,
            self._voice,
            len(available),
        )

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Synthesize text to PCM16 audio bytes.

        Args:
            text: The text to speak. Empty/silent strings return empty audio.

        Returns:
            (pcm16_bytes, sample_rate) — raw 16-bit mono PCM at 24000 Hz.
        """
        if not text or not text.strip():
            return b"", self.sample_rate

        if not self._kokoro:
            raise KokoroTTSError("Kokoro TTS not initialized. Call initialize() first.")

        logger.debug("Kokoro synthesizing: %r", text[:80])

        try:
            samples, sr = await asyncio.to_thread(
                self._kokoro.create,
                text,
                self._voice,
                self._speed,
                self._lang,
            )
            # Convert float32 [-1, 1] → PCM16 int16 bytes
            pcm_bytes = _float32_to_pcm16(samples)
            return pcm_bytes, sr

        except asyncio.CancelledError:
            logger.debug("Kokoro synthesis cancelled")
            raise
        except AssertionError as exc:
            # kokoro-onnx raises AssertionError for invalid inputs
            raise KokoroTTSError(
                f"Kokoro synthesis assertion failed: {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("Kokoro synthesis failed")
            raise KokoroTTSError(
                f"Kokoro synthesis failed: {type(exc).__name__}: {exc}"
            ) from exc

    def _load_model(self):
        """Load ONNX model synchronously (called in thread pool)."""
        from kokoro_onnx import Kokoro
        return Kokoro(self._model_path, self._voices_path)


# ---- Helpers ----

def _float32_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float32 audio samples in [-1, 1] to PCM16 bytes.

    Clips values outside [-1, 1] to prevent overflow.
    """
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()


def _find_chinese_voice(available: list[str]) -> str | None:
    """Find the first available Chinese voice from the available list.

    Checks known v1.0 Chinese voices first, then any voice starting with 'zf_' or 'zm_'.
    """
    # Try v1.0 Chinese voices first
    for voice in KOKORO_CHINESE_VOICES_V1:
        if voice in available:
            return voice
    # Try any Chinese female/male voice
    for voice in available:
        if voice.startswith("zf_") or voice.startswith("zm_"):
            return voice
    return None
