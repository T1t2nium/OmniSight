"""Application configuration loaded from .env via Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration values come from .env with sensible defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI provider
    ai_provider: Literal["ollama", "gemini"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"

    # Gemini (optional — future use)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-live-preview"

    # Speech recognition
    whisper_model: str = "base"
    whisper_language: str | None = None  # None = auto-detect

    # Server
    ws_host: str = "0.0.0.0"
    ws_port: int = 8000

    # Video
    max_fps: int = 4
    jpeg_quality: int = 70
    frame_max_width: int = 640
    frame_max_height: int = 480

    # Vision
    vision_enabled: bool = True  # Set to False for text-only mode (faster on CPU)

    # TTS
    tts_backend: Literal["browser", "piper", "kokoro"] = "kokoro"

    # Piper TTS (local ONNX-based TTS engine — fallback option)
    piper_executable: str = "piper"  # Path to piper executable (or "piper" if on PATH)
    piper_model: str = ""  # Path to .onnx voice model file
    piper_model_config: str = ""  # Path to .onnx.json config file (auto-derived if empty)
    piper_speaker: int | None = None  # Speaker ID for multi-speaker voices

    # Kokoro 82M TTS (local ONNX-based TTS engine — default, best quality)
    kokoro_model_path: str = ""  # Path to .onnx model file
    kokoro_voices_path: str = ""  # Path to voices-v1.0.bin embeddings
    kokoro_voice: str = "zf_xiaobei"  # Default Chinese voice
    kokoro_speed: float = 1.0  # Speech speed (0.5–2.0)
    kokoro_lang: str = "zh"  # espeak-ng language code for G2P

    # ---- PR 5: Robustness settings ----

    # WebSocket heartbeat
    ws_ping_interval: int = 30     # seconds between server ping frames
    ws_ping_timeout: int = 10      # seconds to wait for pong before disconnect
    session_idle_timeout: int = 300  # 5 minutes idle → auto-session cleanup

    # Motion detection
    motion_detection_enabled: bool = True
    motion_threshold: float = 15.0  # mean pixel diff threshold (0-255)

    @field_validator("piper_speaker", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> int | None:
        """Coerce empty-string env var to None for optional int fields."""
        if v is None or v == "" or v == "None":
            return None
        return int(v)


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance (cached after first call)."""
    return Settings()
