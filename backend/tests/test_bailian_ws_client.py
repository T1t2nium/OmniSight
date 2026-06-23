"""Unit tests for BailianWSClient — realtime WebSocket client.

Tests cover constructor validation, properties, and the interface
contract without requiring a live Bailian Realtime connection.
"""

from __future__ import annotations

import pytest

from app.services.bailian_ws_client import BailianWSClient


class TestBailianWSClientInit:
    """Constructor and property tests."""

    def test_init_with_valid_key(self):
        """Constructor accepts a non-empty API key."""
        client = BailianWSClient(api_key="sk-test-key")
        assert client is not None
        assert client.is_connected is False
        assert client.session_id is None

    def test_init_with_empty_key_raises(self):
        """Constructor raises ValueError if API key is empty."""
        with pytest.raises(ValueError, match="must not be empty"):
            BailianWSClient(api_key="")

    def test_init_with_default_model(self):
        """Default model is qwen3.5-omni-plus-realtime."""
        client = BailianWSClient(api_key="sk-test")
        assert client._model == "qwen3.5-omni-plus-realtime"

    def test_init_with_custom_model(self):
        """Custom model name is stored."""
        client = BailianWSClient(api_key="sk-test", model="custom-model")
        assert client._model == "custom-model"

    def test_is_connected_false_before_connect(self):
        """is_connected is False before connect() is called."""
        client = BailianWSClient(api_key="sk-test")
        assert client.is_connected is False

    def test_close_before_connect_is_noop(self):
        """Closing before connecting is safe (no-op)."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            await client.close()  # Should not raise

        asyncio.run(_run())


class TestBailianWSClientAudio:
    """send_audio / send_image tests when not connected."""

    def test_send_audio_when_not_connected(self):
        """send_audio logs a warning but does not raise when not connected."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            # Should not raise — just logs warning
            await client.send_audio("dGVzdA==")

        asyncio.run(_run())

    def test_send_image_when_not_connected(self):
        """send_image logs a warning but does not raise when not connected."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            await client.send_image("dGVzdA==")

        asyncio.run(_run())

    def test_cancel_response_when_not_connected(self):
        """cancel_response does not raise when not connected."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            await client.cancel_response()

        asyncio.run(_run())

    def test_commit_audio_when_not_connected(self):
        """commit_audio does not raise when not connected."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            await client.commit_audio()

        asyncio.run(_run())

    def test_clear_audio_when_not_connected(self):
        """clear_audio does not raise when not connected."""
        import asyncio

        async def _run():
            client = BailianWSClient(api_key="sk-test")
            await client.clear_audio()

        asyncio.run(_run())
