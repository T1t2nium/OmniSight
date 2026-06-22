"""Base AI client protocol — defines the contract all AI providers must fulfill.

All LLM integrations (Ollama, Bailian HTTP, Bailian WS, future providers)
implement this interface so ConversationOrchestrator remains provider-agnostic.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseAIClient(ABC):
    """Abstract base for all AI provider clients.

    Each provider must implement:
      - chat(): stream a chat completion (the core API)
      - check_health(): verify the provider is reachable and the model is available
      - close(): release underlying connections/resources

    Properties:
      - model: the model identifier string (e.g. "qwen3.5:2b", "qwen3.5-omni-plus-2026-03-15")
      - provider_name: human-readable provider name ("ollama" / "bailian" / "gemini")
    """

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model identifier used for API calls."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider name for logging and health checks."""
        ...

    @abstractmethod
    async def chat(
        self,
        transcript: str,
        image_base64: str | None = None,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[dict]:
        """Stream a chat completion from the AI provider.

        Args:
            transcript: The user's transcribed speech text.
            image_base64: Optional base64-encoded JPEG for vision models.
            history: Previous conversation messages for multi-turn context.
            system_prompt: Optional system prompt override. If None, the
                provider falls back to its default system prompt.

        Yields:
            dict with keys:
                delta: str          — incremental text content
                done: bool          — True on the final chunk
                total_duration: float  — total inference time in seconds (done only)
        """
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Check that the AI provider is reachable and the model is available.

        Returns:
            True if the provider is healthy and the model is ready for inference.
        """
        ...

    async def check_health_with_retry(
        self, retries: int = 3, delay: float = 2.0
    ) -> bool:
        """Repeatedly call check_health until success or retries exhausted.

        Subclasses may override for provider-specific retry logic.
        All subclasses share the same interface for use in main.py lifespan.
        """
        import asyncio
        import logging

        logger = logging.getLogger(__name__)
        for attempt in range(1, retries + 1):
            ok = await self.check_health()
            if ok:
                return True
            if attempt < retries:
                logger.info(
                    "%s health check attempt %d/%d failed — retrying in %.1fs",
                    self.provider_name,
                    attempt,
                    retries,
                    delay,
                )
                await asyncio.sleep(delay)
        logger.warning(
            "%s health check failed after %d attempts",
            self.provider_name,
            retries,
        )
        return False

    @abstractmethod
    async def close(self) -> None:
        """Clean shutdown of underlying connections and resources."""
        ...
