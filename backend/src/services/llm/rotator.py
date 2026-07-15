"""Multi-provider LLM rotator.

Wraps a list of :class:`BaseLLMProvider` instances and automatically falls
back to the next provider when the current one raises an error (rate limit,
quota exhausted, service unavailable).

Each method (generate, generate_with_citations, generate_multimodal) follows
the same pattern: try providers in order, log the failure, advance to the
next, and only raise after all providers have been exhausted.
"""

import asyncio
from typing import Optional

from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider


class RotatingProvider(BaseLLMProvider):
    """Wraps multiple LLM providers and rotates through them transparently.

    Usage::

        rotator = RotatingProvider([gemini, openrouter, groq])
        result = await rotator.generate("Hello")  # tries Gemini first
    """

    def __init__(self, providers: list[BaseLLMProvider]):
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers = providers
        self._current_idx = 0
        self._lock = asyncio.Lock()

    # ── public API ────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        return await self._try_all(
            "generate",
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    async def generate_with_citations(
        self,
        prompt: str,
        context: list[dict],
        system_instruction: Optional[str] = None,
    ) -> tuple[str, list[dict]]:
        return await self._try_all(
            "generate_with_citations",
            prompt=prompt,
            context=context,
            system_instruction=system_instruction,
        )

    async def generate_multimodal(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        max_output_tokens: int = 4096,
    ) -> str:
        return await self._try_all(
            "generate_multimodal",
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            max_output_tokens=max_output_tokens,
        )

    # ── internal ──────────────────────────────────────────────────────

    async def _try_all(self, method: str, **kwargs):
        """Try each provider in order until one succeeds."""
        attempts = len(self.providers)

        async with self._lock:
            start_idx = self._current_idx

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            provider = self.providers[idx]
            name = getattr(provider, "name", type(provider).__name__)

            try:
                func = getattr(provider, method)
                result = await func(**kwargs)

                # Persist the successful provider index
                async with self._lock:
                    self._current_idx = idx

                return result

            except Exception as e:
                last_error = e
                err_msg = str(e)
                is_rate_limit = (
                    "429" in err_msg
                    or "quota" in err_msg.lower()
                    or "rate" in err_msg.lower()
                    or "resource" in err_msg.lower()
                    or "exhausted" in err_msg.lower()
                    or "limit" in err_msg.lower()
                )
                kind = "rate-limited/exhausted" if is_rate_limit else "failed"
                logger.warning(
                    f"Provider rotation: {name} {kind} for '{method}'. "
                    f"Error: {err_msg}. "
                    f"Trying next provider ({i + 1}/{attempts})..."
                )

        logger.error(
            f"All {attempts} provider(s) failed for '{method}'. "
            f"Last error: {last_error}"
        )
        raise last_error  # type: ignore[misc]
