"""Bailian OmniRealtime WebSocket client for full-duplex audio conversation.

Connects to the DashScope realtime WebSocket endpoint (wss://dashscope.aliyuncs.com)
and streams PCM16 audio bidirectionally. The API handles VAD, ASR, LLM, and TTS
internally, so this client replaces the entire transcription → LLM → TTS pipeline.

API reference:
  https://www.alibabacloud.com/help/en/model-studio/realtime
"""

import asyncio
import json
import logging
import time
import uuid
from types import TracebackType
from typing import Any, AsyncIterator, Self

import websockets
from websockets import ClientConnection
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedOK,
    ConnectionClosedError,
)

logger = logging.getLogger(__name__)

# DashScope realtime WebSocket endpoint
BAILIAN_REALTIME_BASE = "wss://dashscope.aliyuncs.com"
BAILIAN_REALTIME_PATH = "/api-ws/v1/realtime"

# Audio format constants
INPUT_SAMPLE_RATE = 16000   # 16 kHz PCM16 mono input
OUTPUT_SAMPLE_RATE = 24000  # 24 kHz PCM16 mono output


class BailianWSClient:
    """Manages a WebSocket connection to Bailian OmniRealtime API.

    NOT a BaseAIClient — the realtime protocol (audio in → audio out + events)
    is fundamentally different from the chat protocol (text in → delta text out).

    Usage::

        client = BailianWSClient(api_key)
        await client.connect(instructions="You are a helpful assistant...")
        await client.send_audio(base64_pcm16_chunk)
        async for event in client.receive():
            handle_event(event)
        await client.close()
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-omni-plus-realtime",
    ) -> None:
        if not api_key:
            raise ValueError("Bailian API key must not be empty")
        self._api_key = api_key
        self._model = model
        self._ws: ClientConnection | None = None
        self._connected = False
        self._receive_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._receiver_task: asyncio.Task | None = None
        self._session_id: str | None = None

    # ---- Properties ----

    @property
    def is_connected(self) -> bool:
        """True while the underlying WebSocket is open."""
        return self._connected and self._ws is not None

    @property
    def session_id(self) -> str | None:
        """Bailian session id assigned after `session.created` is received."""
        return self._session_id

    # ---- Core API ----

    async def connect(
        self,
        instructions: str,
        voice: str = "Cherry",
        turn_detection_type: str = "server_vad",
        vad_threshold: float = 0.5,
        silence_duration_ms: int = 800,
    ) -> None:
        """Connect to Bailian Realtime WS and configure the session.

        Args:
            instructions: System instructions (persona + context + rules).
            voice: TTS voice name (e.g. Cherry, Ethan, Tina). 55 voices available.
            turn_detection_type: ``"server_vad"`` (auto) or ``None`` for manual mode.
            vad_threshold: VAD sensitivity (0.0–1.0).
            silence_duration_ms: Silence before auto-commit (ms).
        """
        url = f"{BAILIAN_REALTIME_BASE}{BAILIAN_REALTIME_PATH}?model={self._model}"

        logger.info("Connecting to Bailian Realtime: %s", url)

        # Connect with auth header. The websockets library 14.x uses
        # additional_headers via the `extra_headers` kwarg.
        self._ws = await websockets.connect(
            url,
            additional_headers={"Authorization": f"Bearer {self._api_key}"},
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
        )
        self._connected = True

        # Start the background receiver
        self._receiver_task = asyncio.create_task(self._receiver_loop())

        # Configure session via session.update
        turn_detection: dict | None = None
        if turn_detection_type:
            turn_detection = {
                "type": turn_detection_type,
                "threshold": vad_threshold,
                "silence_duration_ms": silence_duration_ms,
            }

        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": voice,
                "input_audio_format": "pcm",
                "output_audio_format": "pcm",
                "instructions": instructions,
                "turn_detection": turn_detection,
            },
        })

        # Wait for session.created (confirms config accepted)
        try:
            event = await asyncio.wait_for(self._wait_for_event("session.created"), timeout=10)
            self._session_id = event.get("session", {}).get("id")
            logger.info(
                "Bailian Realtime session created: %s (model=%s, voice=%s)",
                self._session_id, self._model, voice,
            )
        except asyncio.TimeoutError:
            logger.error("Timed out waiting for session.created from Bailian Realtime")
            await self.close()
            raise

    async def send_audio(self, pcm16_base64: str) -> None:
        """Send an audio chunk to the input buffer.

        Args:
            pcm16_base64: Base64-encoded 16-bit, 16kHz, mono PCM audio.
        """
        if not self.is_connected:
            logger.warning("Cannot send audio — not connected")
            return
        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "input_audio_buffer.append",
            "audio": pcm16_base64,
        })

    async def send_image(self, jpeg_base64: str) -> None:
        """Send an image frame for vision context.

        Args:
            jpeg_base64: Base64-encoded JPEG image (max 500KB, 1080p).
        """
        if not self.is_connected:
            logger.warning("Cannot send image — not connected")
            return
        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "input_image_buffer.append",
            "image": jpeg_base64,
        })

    async def commit_audio(self) -> None:
        """Commit the audio buffer (manual turn-detection mode only)."""
        if not self.is_connected:
            return
        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "input_audio_buffer.commit",
        })

    async def clear_audio(self) -> None:
        """Clear the audio buffer (e.g. on interrupt)."""
        if not self.is_connected:
            return
        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "input_audio_buffer.clear",
        })

    async def cancel_response(self) -> None:
        """Cancel the current AI response (barge-in / interrupt)."""
        if not self.is_connected:
            return
        await self._send_event({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "response.cancel",
        })
        logger.info("Bailian Realtime: sent response.cancel (barge-in)")

    async def receive(self) -> AsyncIterator[dict]:
        """Yield events from the Bailian Realtime WebSocket.

        Events include:
          - ``input_audio_buffer.speech_started`` / ``speech_stopped``
          - ``conversation.item.input_audio_transcription.completed``
          - ``response.audio_transcript.delta`` / ``.done``
          - ``response.audio.delta`` / ``.done``
          - ``response.text.delta`` / ``.done``
          - ``response.done`` (with ``usage`` token stats)
          - ``session.created`` / ``session.updated``
          - ``error``
        """
        while self._connected:
            try:
                event = await asyncio.wait_for(self._receive_queue.get(), timeout=1.0)
                yield event
            except asyncio.TimeoutError:
                # No event yet; loop and wait
                if not self._connected:
                    return
                continue

    async def close(self) -> None:
        """Clean shutdown of the WebSocket connection."""
        self._connected = False

        # Stop receiver
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
            self._receiver_task = None

        # Close WebSocket
        if self._ws is not None:
            try:
                await self._ws.close()
            except (ConnectionClosed, Exception):
                pass
            self._ws = None

        logger.info("Bailian Realtime client closed (session=%s)", self._session_id)

    # ---- Internal helpers ----

    async def _send_event(self, event: dict) -> None:
        """Serialize and send a JSON event over the WebSocket."""
        if self._ws is None:
            return
        raw = json.dumps(event, ensure_ascii=False)
        try:
            await self._ws.send(raw)
        except ConnectionClosed as exc:
            logger.warning("Failed to send event %s: %s", event.get("type"), exc)
            self._connected = False

    async def _receiver_loop(self) -> None:
        """Background task: read raw messages from WS and push to queue."""
        while self._connected and self._ws is not None:
            try:
                raw = await self._ws.recv()
            except ConnectionClosedOK:
                logger.debug("Bailian Realtime WS closed normally")
                self._connected = False
                break
            except ConnectionClosedError as exc:
                logger.warning("Bailian Realtime WS closed with error: %s", exc)
                self._connected = False
                break
            except Exception:
                logger.exception("Unexpected error in Bailian receiver loop")
                self._connected = False
                break

            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Bailian Realtime: unparseable message: %s", raw[:200])
                continue

            self._receive_queue.put_nowait(event)

    async def _wait_for_event(self, event_type: str) -> dict:
        """Read events from the queue until we see the target type."""
        while self._connected:
            try:
                event = await asyncio.wait_for(self._receive_queue.get(), timeout=0.5)
                if event.get("type") == event_type:
                    return event
            except asyncio.TimeoutError:
                continue
        raise ConnectionError("WebSocket disconnected while waiting for event")

    # ---- Context manager support ----

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
