"""Connection state manager — tracks active WebSocket sessions with thread safety.

PR 5: Added background cleanup task for stale session removal.
"""

import time
import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Per-session metadata."""

    session_id: str
    connected_at: float = field(default_factory=time.time)
    frame_count: int = 0
    audio_chunk_count: int = 0
    audio_duration_ms: float = 0.0
    last_activity: float = field(default_factory=time.time)
    # PR 3: vision frame storage
    latest_frame: str | None = None  # base64 JPEG, overwritten each video_frame
    latest_frame_timestamp: float = 0.0
    # PR 3: AI pipeline state
    ai_status: str = "idle"  # idle | listening | thinking | speaking
    # PR 8: multi-turn conversation history
    history: list[dict] = field(default_factory=list)
    # PR 11: selected agent for this session
    selected_agent: str = "chat"


class ConnectionStateManager:
    """Thread-safe session tracking using asyncio.Lock.

    Tracks frame counts, audio statistics, and activity timestamps per session.
    All mutation methods are async to ensure lock acquisition is explicit.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._idle_timeout: float = 300.0  # default, overridden by config

    async def register(self, session_id: str) -> SessionState:
        """Create and store a new session. Returns the state object."""
        async with self._lock:
            state = SessionState(session_id=session_id)
            self._sessions[session_id] = state
            return state

    async def get(self, session_id: str) -> SessionState | None:
        """Retrieve session state, or None if not registered."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_activity(self, session_id: str) -> None:
        """Bump the last_activity timestamp."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].last_activity = time.time()

    async def increment_frames(self, session_id: str) -> int:
        """Increment frame counter and return the new total."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].frame_count += 1
                self._sessions[session_id].last_activity = time.time()
                return self._sessions[session_id].frame_count
            return 0

    async def add_audio_stats(self, session_id: str, duration_ms: float) -> float:
        """Increment audio stats and return accumulated total duration in ms."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].audio_chunk_count += 1
                self._sessions[session_id].audio_duration_ms += duration_ms
                self._sessions[session_id].last_activity = time.time()
                return self._sessions[session_id].audio_duration_ms
            return 0.0

    async def remove(self, session_id: str) -> None:
        """Delete a session (called on disconnect)."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def get_all_sessions(self) -> list[str]:
        """Return active session IDs (used for monitoring)."""
        async with self._lock:
            return list(self._sessions.keys())

    async def get_session_count(self) -> int:
        """Return number of active sessions."""
        async with self._lock:
            return len(self._sessions)

    # ---- PR 3: vision frame + AI status ----

    async def set_latest_frame(self, session_id: str, frame_b64: str) -> None:
        """Store the latest base64 JPEG frame for vision queries."""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state:
                state.latest_frame = frame_b64
                state.latest_frame_timestamp = time.time()

    async def get_latest_frame(self, session_id: str) -> tuple[str | None, float]:
        """Retrieve the latest frame (base64) and its timestamp."""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state:
                return state.latest_frame, state.latest_frame_timestamp
            return None, 0.0

    async def set_ai_status(self, session_id: str, status: str) -> None:
        """Update the AI processing status."""
        async with self._lock:
            state = self._sessions.get(session_id)
            if state:
                state.ai_status = status

    # ---- PR 5: stale session cleanup ----

    def set_idle_timeout(self, seconds: float) -> None:
        """Configure the idle timeout used by the cleanup task."""
        self._idle_timeout = seconds

    async def start_cleanup_task(self) -> None:
        """Begin a periodic background task that removes idle sessions."""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            "Session cleanup task started (idle_timeout=%.0fs, check every 30s)",
            self._idle_timeout,
        )

    async def stop_cleanup_task(self) -> None:
        """Cancel the background cleanup task (call at shutdown)."""
        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        self._cleanup_task = None
        logger.info("Session cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """Scan every 30s and remove sessions idle for > idle_timeout."""
        while True:
            await asyncio.sleep(30)
            now = time.time()
            stale: list[str] = []
            async with self._lock:
                for sid, state in self._sessions.items():
                    if now - state.last_activity > self._idle_timeout:
                        stale.append(sid)
                for sid in stale:
                    del self._sessions[sid]
            if stale:
                logger.info(
                    "Cleaned up %d stale session(s): %s",
                    len(stale),
                    ", ".join(sid[:8] for sid in stale),
                )
