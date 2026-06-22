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
    ai_provider: Literal["ollama", "bailian", "gemini"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"

    # Alibaba Cloud Bailian (百炼) — DashScope multimodal generation
    bailian_api_key: str = ""  # DashScope API key (sk-...)
    bailian_model: str = "qwen3.5-omni-plus-2026-03-15"

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
    tts_backend: Literal["browser", "piper", "sherpa"] = "sherpa"

    # Piper TTS (local ONNX-based TTS engine — fallback option)
    piper_executable: str = "piper"  # Path to piper executable (or "piper" if on PATH)
    piper_model: str = ""  # Path to .onnx voice model file
    piper_model_config: str = ""  # Path to .onnx.json config file (auto-derived if empty)
    piper_speaker: int | None = None  # Speaker ID for multi-speaker voices

    # sherpa-onnx TTS (local ONNX-based TTS engine — default, best Chinese quality)
    # Uses matcha-icefall-zh-baker model with built-in Chinese FST+lexicon text processing
    sherpa_model_dir: str = ""  # Path to extracted model archive directory
    sherpa_speed: float = 1.0  # Speech speed (0.5–2.0)
    sherpa_num_threads: int = 4  # ONNX Runtime CPU threads

    # ---- PR 5: Robustness settings ----

    # WebSocket heartbeat
    ws_ping_interval: int = 30     # seconds between server ping frames
    ws_ping_timeout: int = 10      # seconds to wait for pong before disconnect
    session_idle_timeout: int = 300  # 5 minutes idle → auto-session cleanup

    # Motion detection
    motion_detection_enabled: bool = True
    motion_threshold: float = 15.0  # mean pixel diff threshold (0-255)

    @field_validator("tts_backend", mode="before")
    @classmethod
    def _migrate_kokoro_to_sherpa(cls, v: object) -> str:
        """Transparently migrate 'kokoro' → 'sherpa' for existing .env files."""
        if v == "kokoro":
            return "sherpa"
        return str(v)

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
