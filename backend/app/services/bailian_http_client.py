"""Alibaba Cloud Bailian (百炼) HTTP client for multimodal generation.

Calls the DashScope multimodal-generation endpoint with SSE streaming.
Implements BaseAIClient so it is a drop-in replacement for OllamaClient.

API reference:
  https://help.aliyun.com/zh/model-studio/multimodal-generation
"""

import asyncio
import json
import logging
import time
from typing import AsyncIterator

import httpx

from app.services.base_ai_client import BaseAIClient

logger = logging.getLogger(__name__)

# DashScope multimodal-generation endpoint
BAILIAN_API_BASE = "https://dashscope.aliyuncs.com"
BAILIAN_API_PATH = "/api/v1/services/aigc/multimodal-generation/generation"


class BailianHTTPClient(BaseAIClient):
    """Async HTTP client for Alibaba Cloud Bailian multimodal generation.

    Uses httpx.AsyncClient for non-blocking I/O. Parses SSE
    (Server-Sent Events) streaming response and yields python dicts
    in the same format as OllamaClient so ConversationOrchestrator
    needs zero changes.
    """

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("Bailian API key must not be empty")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    # ---- BaseAIClient interface properties ----

    @property
    def model(self) -> str:
        """Return the model identifier (e.g. 'qwen3.5-omni-plus-2026-03-15')."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return a human-readable provider name for logging."""
        return "bailian"

    # ---- Core API ----

    async def chat(
        self,
        transcript: str,
        image_base64: str | None = None,
        history: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream a chat completion from Bailian DashScope.

        Maps the Ollama-compatible interface to DashScope's multimodal
        generation API format.

        Args:
            transcript: The user's transcribed speech text.
            image_base64: Optional base64-encoded JPEG for vision.
            history: Previous conversation messages for multi-turn context.

        Yields:
            dict with keys:
                delta: str          — incremental text content
                done: bool          — True on the final chunk
                total_duration: float  — total inference time in seconds (done only)
        """
        from app.services.prompts import SYSTEM_PROMPT

        # Build DashScope-format messages
        messages: list[dict] = []

        # System prompt
        messages.append({
            "role": "system",
            "content": [{"text": SYSTEM_PROMPT}],
        })

        # History (keep last 4 exchanges = 8 messages)
        if history:
            for h in history[-8:]:
                role = h.get("role", "user")
                content_blocks: list[dict] = [{"text": h.get("content", "")}]
                messages.append({
                    "role": role,
                    "content": content_blocks,
                })

        # Current user message — with or without image
        user_content: list[dict] = [{"text": transcript}]
        if image_base64:
            # DashScope accepts base64 with data URI prefix or plain base64
            image_uri = image_base64
            if not image_uri.startswith("data:"):
                image_uri = f"data:image/jpeg;base64,{image_base64}"
            user_content.append({"image": image_uri})

        messages.append({
            "role": "user",
            "content": user_content,
        })

        payload = {
            "model": self._model,
            "input": {
                "messages": messages,
            },
            "parameters": {
                "incremental_output": True,
                "result_format": "message",
                # Text-only output for chat mode (no audio generation)
                "modalities": ["text"],
            },
        }

        t_start = time.perf_counter()

        try:
            async with self._client.stream(
                "POST",
                f"{BAILIAN_API_BASE}{BAILIAN_API_PATH}",
                json=payload,
            ) as response:
                # Bailian returns 200 on success, 4xx/5xx on error
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error(
                        "Bailian API error %d: %s",
                        response.status_code,
                        body[:500],
                    )
                    # Yield error as a response so the frontend sees it
                    yield {
                        "delta": f"[Bailian API error {response.status_code}]",
                        "done": True,
                        "total_duration": time.perf_counter() - t_start,
                    }
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # SSE format: "data: <json>"
                    if not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if not data_str:
                        continue

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Bailian: unparseable SSE line: %s", line[:100]
                        )
                        continue

                    # Extract incremental text from the DashScope response
                    output = data.get("output", {})
                    choices = output.get("choices", [])
                    if not choices:
                        continue

                    choice = choices[0]
                    finish_reason = choice.get("finish_reason", "")
                    message = choice.get("message", {})
                    content_blocks = message.get("content", [])

                    delta_text = ""
                    for block in content_blocks:
                        if "text" in block:
                            delta_text += block["text"]

                    is_done = finish_reason == "stop" or finish_reason == "length"
                    total_duration = time.perf_counter() - t_start if is_done else 0.0

                    yield {
                        "delta": delta_text,
                        "done": is_done,
                        "total_duration": total_duration,
                    }

                    if is_done:
                        # Log usage info if available
                        usage = data.get("usage", {})
                        if usage:
                            logger.info(
                                "Bailian response done — tokens: in=%d out=%d, %.1fs",
                                usage.get("input_tokens", 0),
                                usage.get("output_tokens", 0),
                                total_duration,
                            )
                        return

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.error("Bailian API request failed: %s", exc)
            yield {
                "delta": f"[Bailian API connection error: {exc}]",
                "done": True,
                "total_duration": time.perf_counter() - t_start,
            }
        except httpx.HTTPStatusError as exc:
            logger.error("Bailian API HTTP error: %s", exc)
            yield {
                "delta": f"[Bailian API HTTP error: {exc.response.status_code}]",
                "done": True,
                "total_duration": time.perf_counter() - t_start,
            }

    # ---- Health check ----

    async def check_health(self) -> bool:
        """Check that the Bailian API key is valid by making a minimal request.

        Sends a trivial chat request (no streaming) to verify connectivity
        and authentication.
        """
        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": "ping"}],
                    }
                ],
            },
            "parameters": {
                "incremental_output": False,
                "result_format": "message",
                "modalities": ["text"],
            },
        }

        try:
            response = await self._client.post(
                f"{BAILIAN_API_BASE}{BAILIAN_API_PATH}",
                json=payload,
                timeout=10.0,
            )
            if response.status_code == 200:
                logger.info("Bailian model '%s' is available", self._model)
                return True
            elif response.status_code == 401 or response.status_code == 403:
                logger.warning(
                    "Bailian API key is invalid or expired (HTTP %d)",
                    response.status_code,
                )
                return False
            else:
                body = response.text[:200]
                logger.warning(
                    "Bailian health check failed (HTTP %d): %s",
                    response.status_code,
                    body,
                )
                return False
        except Exception as exc:
            logger.warning("Bailian health check failed: %s", exc)
            return False

    async def check_health_with_retry(
        self, retries: int = 3, delay: float = 2.0
    ) -> bool:
        """Repeatedly call check_health until success or retries exhausted.

        Override to add provider name to log messages.
        """
        for attempt in range(1, retries + 1):
            ok = await self.check_health()
            if ok:
                return True
            if attempt < retries:
                logger.info(
                    "Bailian health check attempt %d/%d failed — retrying in %.1fs",
                    attempt, retries, delay,
                )
                await asyncio.sleep(delay)
        logger.warning(
            "Bailian health check failed after %d attempts", retries
        )
        return False

    # ---- Cleanup ----

    async def close(self) -> None:
        """Clean shutdown of the underlying HTTP client."""
        await self._client.aclose()
