"""Shared pytest fixtures for backend tests.

These provide configuration, test data, and WebSocket helpers so
individual test files don't need to duplicate setup logic.
"""

from __future__ import annotations

import json
import struct
import uuid

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app
from app.models.state import ConnectionStateManager
from app.services.audio import AudioBufferManager
from app.services.base_ai_client import BaseAIClient


# ---- Mock AI Client (shared across integration tests) ----


class MockAIClient(BaseAIClient):
    """Returns a controlled response for integration tests.

    Set ``_response`` to the JSON string you want the client to yield
    as a single ``delta`` chunk with ``done=True``.
    """

    def __init__(self, response_text: str = "", model: str = "mock"):
        self._response = response_text
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mock"

    async def chat(self, transcript, image_base64=None, history=None,
                   system_prompt=None):
        yield {"delta": self._response, "done": True, "total_duration": 0.1}

    async def check_health(self) -> bool:
        return True

    async def close(self) -> None:
        pass


def mock_report_json() -> str:
    """Return a valid interview report JSON string for MockAIClient."""
    return json.dumps({
        "scores": {
            "technical": 80,
            "experience": 75,
            "communication": 85,
            "role_fit": 70,
            "stress": 65,
        },
        "overall_score": 75,
        "strengths": ["Python经验丰富", "沟通表达清晰"],
        "weaknesses": ["缺少FastAPI经验", "压力测试表现一般"],
        "summary": "候选人技术基础扎实，沟通能力好，但部分核心技能有缺口。",
        "recommendation": "推荐",
    })


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return a test Settings instance (uses .env by default)."""
    return Settings()


@pytest.fixture
def sample_pcm16() -> bytes:
    """1 second of silent 16kHz PCM16 (mono, little-endian int16)."""
    samples = [0] * 16000  # 1 second at 16kHz
    return struct.pack(f"<{len(samples)}h", *samples)


@pytest.fixture
def silent_wav_ieee_float() -> bytes:
    """Generate a 60ms IEEE_FLOAT WAV (matching vad-web's encoder output).

    Format tag 3 = IEEE_FLOAT, 32-bit, mono, 16kHz — exactly what the
    browser-side Silero VAD sends via encodeWAV().
    """
    sample_rate = 16000
    num_samples = 960  # 60ms
    data_size = num_samples * 4  # 32-bit float = 4 bytes

    header = struct.pack(
        "<4sI4s"      # RIFF chunk
        "4sIHHIIHH"   # fmt chunk
        "4sI",        # data chunk header
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16,              # chunk size
        3,                        # format = IEEE_FLOAT
        1,                        # channels = mono
        sample_rate,
        sample_rate * 4,          # byte rate
        4,                        # block align
        32,                       # bits per sample
        b"data", data_size,
    )
    # Silent float samples (zeros)
    samples = np.zeros(num_samples, dtype=np.float32).tobytes()
    return header + samples


@pytest.fixture
def new_session_id() -> str:
    """Generate a unique session ID independent of crypto.randomUUID()."""
    return f"test-{uuid.uuid4().hex[:12]}"


@pytest.fixture
async def ws_client():
    """Provide an httpx async client wired to the FastAPI app via ASGI transport.

    Usage in test:
        async with ws_client() as (client, transport):
            async with client.ws_connect("/ws") as ws:
                ...
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
