"""WebSocket /ws endpoint — media streaming + AI pipeline trigger.

Receives audio_chunk, video_frame, and vad_event messages from the browser.
On speech_end, triggers the full AI pipeline (transcriber → Ollama → response).

PR 3 additions:
- Video frames are stored in SessionState.latest_frame (for vision queries).
- vad_event(speech_end) launches AI pipeline as a background task.
- New server→client message types: transcript, llm_response, ai_status.
- Background tasks are tracked per-session and cancelled on disconnect.
"""

import asyncio
import json
import base64
import logging
from typing import Callable, Awaitable
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import (
    WSMessage,
    ServerStatusPayload,
    EchoPayload,
    ErrorPayload,
    AIStatusPayload,
    InterruptPayload,
)
from app.models.state import ConnectionStateManager
from app.services.audio import AudioBufferManager
from app.services.conversation import ConversationOrchestrator
from app.services.frame_manager import FrameMotionDetector
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared service instances
state_manager = ConnectionStateManager()
audio_manager = AudioBufferManager()
motion_detector = FrameMotionDetector()  # PR 5

# Map of session_id → running AI task (for cancellation on disconnect or new utterance)
_running_tasks: dict[str, asyncio.Task] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept a WebSocket connection and dispatch messages by type."""
    await websocket.accept()
    session_id: str | None = None
    heartbeat_task: asyncio.Task | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_session = data.get("session_id")
            if not msg_session:
                await _send_error(websocket, session_id, "Missing session_id")
                continue

            if session_id is None:
                session_id = msg_session
                await state_manager.register(session_id)
                await _send_status(
                    websocket, session_id, "connected",
                    f"Session {session_id} registered",
                )
                logger.info("Session registered: %s", session_id)
                # PR 5: Start heartbeat for this session
                heartbeat_task = asyncio.create_task(
                    _heartbeat_loop(websocket, session_id)
                )
            elif msg_session != session_id:
                continue

            await state_manager.update_activity(session_id)

            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            # PR 5: wrap each handler in try/except to prevent
            # a single bad message from breaking the entire session
            try:
                if msg_type == "audio_chunk":
                    await _handle_audio_chunk(websocket, session_id, payload)
                elif msg_type == "video_frame":
                    await _handle_video_frame(websocket, session_id, payload)
                elif msg_type == "vad_event":
                    await _handle_vad_event(websocket, session_id, payload)
                else:
                    await _send_error(websocket, session_id,
                                      f"Unknown message type: {msg_type}")
            except Exception:
                logger.exception(
                    "Handler error for msg_type=%s session=%s",
                    msg_type, session_id,
                )
                await _send_error(
                    websocket, session_id,
                    f"Internal error processing {msg_type}",
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", session_id)
    except Exception:
        logger.exception("WS error for session %s", session_id)
    finally:
        # Cancel heartbeat
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        if session_id:
            # Cancel any running AI pipeline
            task = _running_tasks.pop(session_id, None)
            if task and not task.done():
                task.cancel()
                logger.info("Cancelled AI pipeline for %s", session_id)
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

        # vad-web encodes WAV as IEEE_FLOAT (format=3), not PCM16 as
        # documented. Parse manually — stdlib wave can't read float WAV.
        pcm_data = _parse_wav_to_pcm16(raw_wav)
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
    """Store the latest JPEG frame for vision queries, with motion detection.

    PR 5: unchanged frames (below motion threshold) are still counted but
    not stored as latest_frame — they don't trigger a new vision query.
    """
    b64_data = payload.get("data", "")
    motion_skipped = False

    if b64_data:
        settings = get_settings()
        if settings.motion_detection_enabled:
            if not motion_detector.is_significant_change(b64_data):
                motion_skipped = True
                b64_data = ""  # Don't update latest_frame
        if b64_data:
            await state_manager.set_latest_frame(session_id, b64_data)

    frame_count = await state_manager.increment_frames(session_id)
    session_state = await state_manager.get(session_id)

    echo = EchoPayload(
        received_type="video_frame",
        total_frames=frame_count,
        total_audio_ms=session_state.audio_duration_ms if session_state else 0,
    )
    echo_dict = echo.model_dump()
    if motion_skipped:
        echo_dict["motion_skipped"] = True
    await _send_message(ws, session_id, "echo", echo_dict)


async def _handle_vad_event(
    ws: WebSocket, session_id: str, payload: dict
) -> None:
    """Handle VAD events. On speech_end, launch the AI pipeline.

    PR 4: speech_start during active AI pipeline cancels it (barge-in).
    """
    event = payload.get("event", "unknown")
    logger.info("VAD %s [%s]", event, session_id)

    if event == "speech_start":
        # Clear any residual audio from previous VAD cycle
        audio_manager.clear(session_id)
        # PR 5: reset motion detector for new utterance
        motion_detector.reset()

        # Barge-in: cancel running AI pipeline + notify frontend to stop audio
        existing = _running_tasks.get(session_id)
        if existing and not existing.done():
            existing.cancel()
            logger.info("Interrupted AI pipeline for %s (barge-in)", session_id)
            p = InterruptPayload(reason="user_interrupt")
            await _send_message(ws, session_id, "interrupt", p.model_dump())

    if event == "speech_end":
        await _start_ai_pipeline(ws, session_id)

    echo = EchoPayload(received_type=f"vad_event:{event}")
    await _send_message(ws, session_id, "echo", echo.model_dump())


# ---- AI Pipeline ----


async def _start_ai_pipeline(ws: WebSocket, session_id: str) -> None:
    """Retrieve audio + frame, then launch transcribe → Ollama in background."""
    # Cancel any previous task for this session
    existing = _running_tasks.get(session_id)
    if existing and not existing.done():
        existing.cancel()
        logger.info("Cancelled previous AI pipeline for %s", session_id)

    # Flush audio buffer
    pcm_bytes, duration_ms = audio_manager.flush(session_id)
    if not pcm_bytes or len(pcm_bytes) < 320:
        logger.info(
            "Skipping AI pipeline for %s — audio too short (%d bytes, %.0f ms)",
            session_id, len(pcm_bytes), duration_ms,
        )
        return

    # Get latest frame (only if vision is enabled in config)
    settings = ws.app.state.settings
    latest_frame = None
    if settings.vision_enabled:
        latest_frame, _ = await state_manager.get_latest_frame(session_id)

    # Get orchestrator from app state
    orchestrator: ConversationOrchestrator = ws.app.state.orchestrator

    # Build send callbacks that close over the WebSocket
    async def send_msg(msg_type: str, payload: dict) -> None:
        await _send_message(ws, session_id, msg_type, payload)

    async def send_status(status: str) -> None:
        p = AIStatusPayload(status=status)
        await _send_message(ws, session_id, "ai_status", p.model_dump())

    # PR 8: load existing conversation history from session state
    session = await state_manager.get(session_id)
    history: list[dict] = session.history.copy() if session and session.history else []

    task = asyncio.create_task(
        orchestrator.process_utterance(
            pcm_bytes=pcm_bytes,
            sample_rate=16000,
            latest_frame_b64=latest_frame,
            history=history,
            send_fn=send_msg,
            status_fn=send_status,
        )
    )
    _running_tasks[session_id] = task

    # PR 8: save updated history back to session state when pipeline completes
    async def _save_history(t: asyncio.Task) -> None:
        try:
            updated = t.result()
            if updated:
                s = await state_manager.get(session_id)
                if s:
                    s.history = updated
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    def _cleanup(t: asyncio.Task) -> None:
        if _running_tasks.get(session_id) is t:
            _running_tasks.pop(session_id, None)

    task.add_done_callback(
        lambda t: (_cleanup(t), asyncio.create_task(_save_history(t)))
    )


# ---- WAV Parser ----


def _parse_wav_to_pcm16(raw: bytes) -> bytes:
    """Parse a WAV file and return PCM16 bytes regardless of source format.

    vad-web's encodeWAV() outputs IEEE_FLOAT (format tag 3) WAV, not PCM16
    as documented. We manually parse the WAV header and convert to PCM16.
    """
    import struct
    import numpy as np

    if len(raw) < 44:
        raise ValueError(f"WAV too short: {len(raw)} bytes")

    # RIFF header validation
    riff, wave = struct.unpack_from("<4s4s", raw, 8)
    if riff[:4] != b"RIFF" or wave != b"WAVE":
        # retry: riff tag might be at offset 0
        riff = raw[:4]
        if riff != b"RIFF":
            raise ValueError("Not a valid RIFF WAV")

    # Scan chunks for fmt and data
    fmt_tag = 0
    bits_per_sample = 0
    data_offset = 0
    data_size = 0

    pos = 12  # After "RIFF....WAVE"
    while pos < len(raw) - 8:
        chunk_id, chunk_size = struct.unpack_from("<4sI", raw, pos)
        pos += 8
        if chunk_id == b"fmt ":
            fmt_tag = struct.unpack_from("<H", raw, pos)[0]
            bits_per_sample = struct.unpack_from("<H", raw, pos + 14)[0]
        elif chunk_id == b"data":
            data_offset = pos
            data_size = chunk_size
            break
        pos += chunk_size

    if not data_offset:
        raise ValueError("No data chunk in WAV")

    samples_raw = raw[data_offset : data_offset + data_size]

    if fmt_tag == 3:  # IEEE_FLOAT (32-bit)
        arr = np.frombuffer(samples_raw, dtype=np.float32).copy()
        arr = np.clip(arr, -1.0, 1.0)
        pcm = (arr * 32767.0).astype(np.int16)
        return pcm.tobytes()

    elif fmt_tag == 1:  # PCM
        return samples_raw

    else:
        raise ValueError(f"Unsupported WAV format: {fmt_tag}")


# ---- Debug ----


def _dump_raw_wav(raw_wav: bytes) -> None:
    """Save the received WAV (with original header, before stripping) to disk.

    Comparing this with the frontend's browser-side playback tells us
    whether the base64 round-trip preserves the audio correctly.
    """
    import time
    from pathlib import Path

    debug_dir = Path("debug_audio")
    debug_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = debug_dir / f"received_{timestamp}.wav"
    path.write_bytes(raw_wav)
    logger.info("Debug received WAV saved: %s (%.1f KB)", path, len(raw_wav) / 1024)


# ---- Heartbeat ----


async def _heartbeat_loop(ws: WebSocket, session_id: str) -> None:
    """Send WebSocket protocol-level ping frames every N seconds.

    If no pong is received within the timeout window the connection is
    considered dead and is closed.
    """
    settings = get_settings()
    interval = settings.ws_ping_interval
    timeout = settings.ws_ping_timeout

    while True:
        await asyncio.sleep(interval)
        try:
            pong_waiter = await ws.ping()
            await asyncio.wait_for(pong_waiter, timeout=timeout)
            logger.debug("Heartbeat OK for %s", session_id)
        except asyncio.TimeoutError:
            logger.warning(
                "Heartbeat timeout for %s — closing connection", session_id
            )
            await ws.close(code=1000)
            return
        except Exception:
            # Connection already gone — exit silently
            return


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
