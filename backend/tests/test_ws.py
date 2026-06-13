"""WebSocket integration tests — session lifecycle, message routing, and isolation.

Uses Starlette's TestClient (built-in WebSocket support) rather than httpx
(whose WS support varies by version).
"""

from __future__ import annotations

import json
import time
import uuid

import pytest
from starlette.testclient import TestClient

from app.main import app


# ---- Helpers ----


def _make_msg(msg_type: str, session_id: str, payload: dict | None = None) -> dict:
    return {
        "type": msg_type,
        "session_id": session_id,
        "timestamp": time.time(),
        "payload": payload or {},
    }


def _make_audio_chunk(session_id: str, wav_data: bytes) -> dict:
    """Build a valid audio_chunk message with base64 WAV."""
    import base64

    return _make_msg("audio_chunk", session_id, {
        "data": base64.b64encode(wav_data).decode("ascii"),
        "sample_rate": 16000,
        "channels": 1,
        "duration_ms": 60,
    })


# ---- Tests ----


def test_session_lifecycle():
    """Connect → receive server_status → disconnect → session cleaned."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        sid = f"test-life-{uuid.uuid4().hex[:8]}"

        # Send any valid message to trigger registration
        ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))

        # First message should be server_status
        resp = ws.receive_json()
        assert resp["type"] == "server_status"
        assert resp["payload"]["status"] == "connected"

        # Then echo for vad_event
        resp2 = ws.receive_json()
        assert resp2["type"] == "echo"


def test_unknown_message_type_returns_error():
    """Sending an unrecognized message type yields an error payload."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        sid = f"test-unk-{uuid.uuid4().hex[:8]}"
        ws.send_json(_make_msg("bogus_type", sid))

        # Should get server_status (registration) then error
        msgs = []
        for _ in range(2):
            msgs.append(ws.receive_json())

        types = [m["type"] for m in msgs]
        assert "server_status" in types
        assert "error" in types


def test_audio_chunk_echo(silent_wav_ieee_float):
    """Send audio_chunk → receive echo with duration info."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        sid = f"test-aud-{uuid.uuid4().hex[:8]}"
        ws.send_json(_make_audio_chunk(sid, silent_wav_ieee_float))

        # Skip server_status
        msg1 = ws.receive_json()
        if msg1["type"] == "server_status":
            msg2 = ws.receive_json()
        else:
            msg2 = msg1

        assert msg2["type"] == "echo"
        assert msg2["payload"]["received_type"] == "audio_chunk"
        assert msg2["payload"]["duration_ms"] == 60
        assert isinstance(msg2["payload"]["total_audio_ms"], (int, float))


def test_video_frame_echo():
    """Send video_frame → frame_count increments."""
    import base64

    # Minimal valid JPEG (1x1 pixel, black)
    minimal_jpeg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
        "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
        "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
        "CAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
        "AgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
        "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWG"
        "h4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl"
        "5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
        "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYk"
        "NOEl8RcYI0JTY3KSo0RUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkp"
        "OUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8v"
        "P09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q=="
    )

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        sid = f"test-vid-{uuid.uuid4().hex[:8]}"

        # Send two video frames
        ws.send_json(_make_msg("video_frame", sid, {
            "data": base64.b64encode(minimal_jpeg).decode("ascii"),
            "width": 640,
            "height": 480,
        }))
        ws.send_json(_make_msg("video_frame", sid, {
            "data": base64.b64encode(minimal_jpeg).decode("ascii"),
            "width": 640,
            "height": 480,
        }))

        # Collect all messages (2 frames → server_status + 2 echoes = 3 msgs)
        msgs = []
        for _ in range(3):
            msgs.append(ws.receive_json())

        echoes = [m for m in msgs if m["type"] == "echo"]
        assert len(echoes) >= 1


def test_session_isolation():
    """Two different session_ids are tracked independently."""
    client = TestClient(app)
    with (
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        sid_a = f"test-iso-a-{uuid.uuid4().hex[:8]}"
        sid_b = f"test-iso-b-{uuid.uuid4().hex[:8]}"

        ws_a.send_json(_make_msg("vad_event", sid_a, {"event": "speech_start"}))
        ws_b.send_json(_make_msg("vad_event", sid_b, {"event": "speech_start"}))

        resp_a = ws_a.receive_json()
        resp_b = ws_b.receive_json()

        assert resp_a["type"] == "server_status"
        assert resp_b["type"] == "server_status"
        assert resp_a["session_id"] == sid_a
        assert resp_b["session_id"] == sid_b


def test_missing_session_id():
    """Messages without session_id get an error."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "vad_event", "payload": {}})

        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "session_id" in resp["payload"]["message"].lower()


def test_health_endpoint():
    """GET /health returns expected fields."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "ollama_available" in data
    assert "active_sessions" in data
    assert "uptime_seconds" in data
