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


# ---- PR 4: TTS Audio + Interrupt Payloads (Server → Client) ----

class TTSAudioPayload(BaseModel):
    """PCM16 audio chunk produced by Piper TTS for a single sentence."""

    data: str  # base64 PCM16 audio
    sample_rate: int = 22050
    channels: int = 1
    text: str = ""  # The sentence being spoken (for UI display)


class InterruptPayload(BaseModel):
    """Sent by server to confirm AI generation has been interrupted."""

    reason: str = "user_interrupt"


# ---- PR 11: Agent Payloads (Server → Client & Client → Server) ----


class AgentInfo(BaseModel):
    """Lightweight agent metadata sent to frontend."""

    agent_id: str
    name: str
    description: str
    ui_config: dict = Field(default_factory=dict)


class AgentListPayload(BaseModel):
    """Sent by server on session start — list of available agents."""

    agents: list[AgentInfo]


class AgentSelectPayload(BaseModel):
    """Sent by client to switch the active agent for this session."""

    agent_id: str


# ---- PR 13: Document Upload & Question Bank Payloads ----


class DocumentUploadPayload(BaseModel):
    """Sent by client when uploading a JD or resume document."""

    doc_type: Literal["jd", "resume"]
    filename: str
    data: str  # base64-encoded file bytes


class DocumentParsedPayload(BaseModel):
    """Sent by server after document parsing and entity extraction."""

    doc_type: Literal["jd", "resume"]
    filename: str = ""
    jd_entities: Optional[dict] = None
    resume_entities: Optional[dict] = None
    match_result: Optional[dict] = None


class QuestionBankPayload(BaseModel):
    """Sent by server with AI-generated interview question bank."""

    categories: list[dict]
    total_questions: int
    generated_at: str = ""


# ---- PR 14: Interview During ----

class InterviewStartedPayload(BaseModel):
    """Sent by server when real-time interview has started."""

    phase: str = "icebreaker"


class InterviewStoppedPayload(BaseModel):
    """Sent by server when interview has ended, with full transcript."""

    transcript: list[dict] = Field(default_factory=list)
    message: str = ""


# ---- PR 15: Interview Report Payload ----

class InterviewReportPayload(BaseModel):
    """Sent by server with AI-generated post-interview analysis."""

    scores: dict = Field(default_factory=dict)  # {technical, experience, communication, role_fit, stress}
    overall_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    summary: str = ""
    recommendation: str = ""
    generated_at: str = ""
