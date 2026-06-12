"""Connection state manager — tracks active WebSocket sessions with thread safety."""

import time
import asyncio
from dataclasses import dataclass, field


@dataclass
class SessionState:
    """Per-session metadata."""

    session_id: str
    connected_at: float = field(default_factory=time.time)
    frame_count: int = 0
    audio_chunk_count: int = 0
    audio_duration_ms: float = 0.0
    last_activity: float = field(default_factory=time.time)


class ConnectionStateManager:
    """Thread-safe session tracking using asyncio.Lock.

    Tracks frame counts, audio statistics, and activity timestamps per session.
    All mutation methods are async to ensure lock acquisition is explicit.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

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
