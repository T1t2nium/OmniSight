"""Per-session PCM16 audio buffer management."""

from collections import defaultdict


class AudioBufferManager:
    """Accumulates raw PCM16 audio chunks per session.

    Each audio_chunk message carries a base64-encoded WAV whose 44-byte header
    has already been stripped by the WS handler, leaving pure PCM16 samples.
    """

    def __init__(self) -> None:
        self._buffers: dict[str, list[bytes]] = defaultdict(list)
        self._durations: dict[str, float] = defaultdict(float)

    def add_audio(self, session_id: str, pcm_data: bytes, duration_ms: float) -> None:
        """Append a PCM16 chunk and accumulate total milliseconds."""
        self._buffers[session_id].append(pcm_data)
        self._durations[session_id] += duration_ms

    def get_audio(self, session_id: str) -> tuple[bytes, float]:
        """Return concatenated PCM16 bytes and total duration in ms."""
        if session_id not in self._buffers:
            return b"", 0.0
        concatenated = b"".join(self._buffers[session_id])
        return concatenated, self._durations[session_id]

    def clear(self, session_id: str) -> None:
        """Remove all buffered audio for a session."""
        self._buffers.pop(session_id, None)
        self._durations.pop(session_id, None)

    def flush(self, session_id: str) -> tuple[bytes, float]:
        """Get accumulated audio AND clear the buffer — atomic convenience."""
        pcm, duration = self.get_audio(session_id)
        self.clear(session_id)
        return pcm, duration

    def clear_all(self) -> None:
        """Remove all sessions (used at shutdown)."""
        self._buffers.clear()
        self._durations.clear()
