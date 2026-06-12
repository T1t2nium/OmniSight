"""WebSocket /ws endpoint — core media streaming handler.

Receives audio_chunk, video_frame, and vad_event messages from the browser.
Echoes statistics back so the frontend can verify the pipeline is working.
"""

import json
import base64
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import (
    WSMessage,
    ServerStatusPayload,
    EchoPayload,
    ErrorPayload,
)
from app.models.state import ConnectionStateManager
from app.services.audio import AudioBufferManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared service instances — lives for the application lifetime
state_manager = ConnectionStateManager()
audio_manager = AudioBufferManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept a WebSocket connection and dispatch messages by type."""
    await websocket.accept()
    session_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            # Extract session_id (client sends it with every message)
            msg_session = data.get("session_id")
            if not msg_session:
                await _send_error(websocket, session_id, "Missing session_id")
                continue

            if session_id is None:
                # First message — register the session
                session_id = msg_session
                await state_manager.register(session_id)
                await _send_status(websocket, session_id, "connected",
                                   f"Session {session_id} registered")
                logger.info("Session registered: %s", session_id)
            elif msg_session != session_id:
                # Safety: ignore messages that don't match the registered session
                continue

            await state_manager.update_activity(session_id)

            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "audio_chunk":
                await _handle_audio_chunk(websocket, session_id, payload)
            elif msg_type == "video_frame":
                await _handle_video_frame(websocket, session_id, payload)
            elif msg_type == "vad_event":
                await _handle_vad_event(websocket, session_id, payload)
            else:
                await _send_error(websocket, session_id,
                                  f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", session_id)
    except Exception:
        logger.exception("WS error for session %s", session_id)
    finally:
        if session_id:
            await state_manager.remove(session_id)
            audio_manager.clear(session_id)
            logger.info("Session cleaned up: %s", session_id)


# ---- Message Handlers ----


async def _handle_audio_chunk(
    ws: WebSocket, session_id: str, payload: dict
) -> None:
    """Decode base64 WAV, strip header, store PCM16, echo stats."""
    b64_data = payload.get("data", "")
    duration_ms = payload.get("duration_ms", 0)

    if not b64_data:
        return

    try:
        raw_wav = base64.b64decode(b64_data)
        # Strip 44-byte WAV header to get pure PCM16 samples
        pcm_data = raw_wav[44:] if len(raw_wav) > 44 else raw_wav
    except Exception:
        logger.exception("Failed to decode audio chunk for %s", session_id)
        return

    audio_manager.add_audio(session_id, pcm_data, duration_ms)
    total_audio_ms = await state_manager.add_audio_stats(session_id, duration_ms)
    session_state = await state_manager.get(session_id)

    echo = EchoPayload(
        received_type="audio_chunk",
        duration_ms=duration_ms,
        total_audio_ms=total_audio_ms,
        total_frames=session_state.frame_count if session_state else 0,
    )
    await _send_message(ws, session_id, "echo", echo.model_dump())


async def _handle_video_frame(
    ws: WebSocket, session_id: str, payload: dict
) -> None:
    """Count the frame and echo statistics back."""
    frame_count = await state_manager.increment_frames(session_id)
    session_state = await state_manager.get(session_id)

    echo = EchoPayload(
        received_type="video_frame",
        total_frames=frame_count,
        total_audio_ms=session_state.audio_duration_ms if session_state else 0,
    )
    await _send_message(ws, session_id, "echo", echo.model_dump())


async def _handle_vad_event(
    ws: WebSocket, session_id: str, payload: dict
) -> None:
    """Log VAD events and echo them back."""
    event = payload.get("event", "unknown")
    logger.info("VAD %s [%s]", event, session_id)

    echo = EchoPayload(received_type=f"vad_event:{event}")
    await _send_message(ws, session_id, "echo", echo.model_dump())


# ---- Helpers ----


async def _send_message(
    ws: WebSocket, session_id: str, msg_type: str, payload: dict
) -> None:
    """Serialize and send a WSMessage envelope as JSON."""
    msg = WSMessage(type=msg_type, session_id=session_id, payload=payload)
    await ws.send_text(msg.model_dump_json())


async def _send_status(
    ws: WebSocket, session_id: str, status: str, message: str = ""
) -> None:
    """Send a server_status message."""
    p = ServerStatusPayload(status=status, message=message)
    await _send_message(ws, session_id, "server_status", p.model_dump())


async def _send_error(
    ws: WebSocket, session_id: str | None, message: str
) -> None:
    """Send an error message."""
    p = ErrorPayload(message=message)
    await _send_message(ws, session_id or "unknown", "error", p.model_dump())
