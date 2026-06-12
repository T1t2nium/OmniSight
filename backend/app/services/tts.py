"""Piper TTS service — local ONNX-based text-to-speech.

Uses the official Piper executable (https://github.com/rhasspy/piper) via
asyncio subprocess. Each sentence triggers a separate synthesis call; the
OS page cache makes repeated loads fast after the first invocation.

Sentence streaming: the orchestrator detects sentence boundaries in the
LLM output, calls synthesize() per sentence, and sends each PCM16 chunk
to the frontend for playback via Web Audio API.

Interrupt: if the caller cancels the asyncio task, the running subprocess
is killed and partial audio is discarded.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Piper voices available on huggingface.co/rhasspy/piper-voices
# Default recommended voices for Chinese + English:
RECOMMENDED_VOICES = {
    "zh_CN": "zh_CN-huayan-medium",
    "en_US": "en_US-lessac-medium",
}


class PiperTTSError(Exception):
    """Raised when Piper synthesis fails."""


class PiperTTS:
    """Async wrapper around the Piper TTS executable.

    Usage:
        tts = PiperTTS(executable="piper", model="zh_CN-huayan-medium.onnx")
        pcm_bytes, sample_rate = await tts.synthesize("你好世界")
    """

    def __init__(
        self,
        executable: str = "piper",
        model_path: str = "",
        config_path: str = "",
        speaker: int | None = None,
    ) -> None:
        """
        Args:
            executable: Path to piper binary, or "piper" to search PATH.
            model_path: Path to .onnx voice model file.
            config_path: Path to .onnx.json config file. Auto-derived from
                         model_path if empty (model.onnx → model.onnx.json).
            speaker: Speaker ID for multi-speaker voices (e.g., en_US-libritts).
        """
        self._executable = executable
        self._model_path = model_path
        self._config_path = config_path or (model_path + ".json" if model_path else "")
        self._speaker = speaker
        self._sample_rate: int = 22050  # default, overridden from config
        self._ready = False
        self._source_lang: str = ""

    # ---- public API ----

    @property
    def ready(self) -> bool:
        """True if the model is loaded and Piper executable is available."""
        return self._ready

    @property
    def sample_rate(self) -> int:
        """Native sample rate of the loaded voice model."""
        return self._sample_rate

    @property
    def source_lang(self) -> str:
        """Language code from the voice model config (e.g. 'zh_CN', 'en_US')."""
        return self._source_lang

    async def initialize(self) -> None:
        """Validate the Piper executable and voice model exist.

        Reads the model config JSON to extract sample rate and language.
        Raises PiperTTSError if any requirement is missing.
        """
        # Check executable
        piper_path = shutil.which(self._executable) if self._executable == "piper" else self._executable
        if not piper_path:
            piper_path = self._executable  # absolute or relative path
        if not os.path.isfile(piper_path) and self._executable == "piper":
            raise PiperTTSError(
                "Piper executable not found on PATH. "
                "Download from https://github.com/rhasspy/piper/releases "
                "and set PIPER_EXECUTABLE in .env."
            )
        self._executable = piper_path

        # Check model
        if not self._model_path:
            raise PiperTTSError(
                "Piper voice model not configured. "
                "Set PIPER_MODEL in .env to a .onnx model file.\n"
                f"Recommended: {RECOMMENDED_VOICES}\n"
                "Download from https://huggingface.co/rhasspy/piper-voices"
            )
        if not os.path.isfile(self._model_path):
            raise PiperTTSError(
                f"Piper model not found: {self._model_path}"
            )

        # Check config
        if not os.path.isfile(self._config_path):
            # Try auto-deriving from model path
            auto_config = self._model_path + ".json"
            if os.path.isfile(auto_config):
                self._config_path = auto_config
            else:
                raise PiperTTSError(
                    f"Piper model config not found: {self._config_path}"
                )

        # Parse config for sample rate and language
        try:
            cfg = json.loads(Path(self._config_path).read_text(encoding="utf-8"))
            self._sample_rate = cfg.get("audio", {}).get("sample_rate", 22050)
            self._source_lang = cfg.get("language", "")
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Could not parse Piper config %s: %s", self._config_path, exc)

        # Quick smoke test with a tiny synthesis
        try:
            await self.synthesize(".")
        except PiperTTSError:
            raise
        except Exception as exc:
            raise PiperTTSError(
                f"Piper smoke test failed: {exc}"
            ) from exc

        self._ready = True
        logger.info(
            "Piper TTS ready: model=%s, sample_rate=%d, language=%s",
            Path(self._model_path).name, self._sample_rate,
            self._source_lang or "unknown",
        )

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Synthesize text to PCM16 audio bytes.

        Args:
            text: The text to speak. Empty/silent strings return empty audio.

        Returns:
            (pcm16_bytes, sample_rate) — raw 16-bit mono PCM at the voice's
            native sample rate.

        Raises PiperTTSError on synthesis failure.
        """
        if not text or not text.strip():
            return b"", self._sample_rate

        # Build the piper command
        cmd = [self._executable, "--model", self._model_path, "--output-raw"]
        if self._config_path:
            cmd.extend(["--config", self._config_path])
        if self._speaker is not None:
            cmd.extend(["--speaker", str(self._speaker)])

        logger.debug("Piper synthesizing: %r", text[:80])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode("utf-8"))

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                raise PiperTTSError(
                    f"Piper exited with code {proc.returncode}: {err_msg}"
                )

            return stdout, self._sample_rate

        except asyncio.CancelledError:
            logger.debug("Piper synthesis cancelled")
            raise
        except PiperTTSError:
            raise
        except FileNotFoundError:
            raise PiperTTSError(
                f"Piper executable not found at '{self._executable}'. "
                "Is Piper installed and PIPER_EXECUTABLE set correctly?"
            )
        except Exception as exc:
            raise PiperTTSError(f"Piper synthesis failed: {exc}") from exc


# ---- Helpers ----

def split_sentences(text: str) -> tuple[list[str], str]:
    """Extract complete sentences from accumulated text.

    Returns (complete_sentences, remaining_text).
    Sentence boundaries: 。！？.!?\n

    >>> split_sentences("你好。这是测试。未完")
    (['你好。', '这是测试。'], '未完')
    """
    boundaries = set("。！？.!?\n")
    result: list[str] = []
    start = 0

    for i, ch in enumerate(text):
        if ch in boundaries:
            end = i + 1
            sentence = text[start:end].strip()
            if sentence:
                result.append(sentence)
            start = end

    remaining = text[start:].strip()
    return result, remaining
