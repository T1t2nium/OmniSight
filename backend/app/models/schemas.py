"""WebSocket message Pydantic models — shared contract between frontend and backend."""

import time
from typing import Literal, Optional
from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    """Envelope for all WebSocket messages. type determines payload structure."""

    type: str
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    payload: dict = Field(default_factory=dict)


# ---- Client → Server Payloads ----


class AudioChunkPayload(BaseModel):
    """Payload for audio_chunk messages. data is base64-encoded WAV (PCM16)."""

    data: str
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: float = 0.0


class VideoFramePayload(BaseModel):
    """Payload for video_frame messages. data is base64-encoded JPEG."""

    data: str
    width: int = 0
    height: int = 0


class VADEventPayload(BaseModel):
    """Payload for vad_event messages."""

    event: Literal["speech_start", "speech_end"]


# ---- Server → Client Payloads ----


class ServerStatusPayload(BaseModel):
    """Sent when a session is registered or the connection state changes."""

    status: Literal["connected", "disconnected"]
    message: str = ""


class EchoPayload(BaseModel):
    """Echo statistics returned to client for pipeline verification."""

    received_type: str
    duration_ms: Optional[float] = None
    frame_count: Optional[int] = None
    total_audio_ms: Optional[float] = None
    total_frames: Optional[int] = None


class ErrorPayload(BaseModel):
    """Server error notification."""

    message: str


# ---- PR 3: AI Pipeline Payloads (Server → Client) ----


class TranscriptPayload(BaseModel):
    """Sent when user speech has been transcribed by faster-whisper."""

    text: str
    language: str = ""
    duration_ms: float = 0.0


class LLMResponsePayload(BaseModel):
    """Streaming AI response chunk. delta is incremental text content."""

    delta: str
    done: bool = False
    total_duration: float = 0.0  # seconds, only meaningful when done=True


class AIStatusPayload(BaseModel):
    """AI pipeline status for frontend visual feedback."""

    status: Literal["listening", "thinking", "speaking", "idle"] = "idle"
