"""Application configuration loaded from .env via Pydantic Settings."""

from functools import lru_cache
from typing import Literal

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

    # TTS
    tts_backend: Literal["browser", "piper"] = "browser"


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance (cached after first call)."""
    return Settings()
