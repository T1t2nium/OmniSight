"""Ollama HTTP API client with NDJSON streaming support."""

import json
import logging
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async HTTP client for Ollama's /api/chat endpoint.

    Uses httpx.AsyncClient for non-blocking I/O. Parses the NDJSON
    (newline-delimited JSON) streaming response and yields python dicts.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    async def chat(
        self,
        transcript: str,
        image_base64: str | None = None,
        history: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream a chat completion from Ollama.

        Args:
            transcript: The user's transcribed speech text.
            image_base64: Optional base64-encoded JPEG for vision models.
            history: Previous conversation messages for multi-turn context.

        Yields:
            dict with keys:
                delta: str          — incremental text content
                done: bool          — True on the final chunk
                total_duration: float  — total inference time in seconds (done only)

        Cancellation: the caller closes the stream or cancels the asyncio task.
        """
        messages = list(history or [])

        # Build the user message — with or without image
        if image_base64:
            messages.append({
                "role": "user",
                "content": transcript,
                "images": [image_base64],
            })
        else:
            messages.append({
                "role": "user",
                "content": transcript,
            })

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }

        async with self._client.stream(
            "POST", f"{self._base_url}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Ollama: unparseable NDJSON line: %s", line[:100])
                    continue

                yield {
                    "delta": chunk.get("message", {}).get("content", ""),
                    "done": chunk.get("done", False),
                    "total_duration": chunk.get("total_duration", 0) / 1e9,
                }

    async def check_health(self) -> bool:
        """Check that the Ollama server is running and the model is available."""
        try:
            response = await self._client.get(
                f"{self._base_url}/api/tags", timeout=5.0
            )
            if response.status_code != 200:
                return False
            models = response.json().get("models", [])
            available = any(
                m["name"].startswith(self._model.split(":")[0])
                for m in models
            )
            if not available:
                logger.warning(
                    "Ollama model '%s' not found. Available: %s",
                    self._model,
                    [m["name"] for m in models],
                )
            return available
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False

    async def close(self) -> None:
        """Clean shutdown of the underlying HTTP client."""
        await self._client.aclose()
