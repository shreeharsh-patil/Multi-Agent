"""Multi-provider LLM rotator with rate-limit awareness.

Wraps a list of :class:`BaseLLMProvider` instances and automatically falls
back to the next provider when the current one raises an error (rate limit,
quota exhausted, service unavailable). On 429 (rate-limit) errors, applies
exponential backoff before retrying the next provider to avoid hammering
free-tier API endpoints.

Each method (generate, generate_with_citations, generate_multimodal) follows
the same pattern: try providers in order, log the failure, advance to the
next, and only raise after all providers have been exhausted.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Optional

from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider


class TokenBucket:
    """Simple in-memory token bucket rate limiter.

    Limits to ``capacity`` requests per ``window_seconds`` sliding window.
    Used to stay within free-tier limits without hard-cutting requests.
    """

    def __init__(self, capacity: int, window_seconds: float = 60.0):
        self.capacity = capacity
        self.window = window_seconds
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Wait for a token and return the wait time in seconds.

        If a token is immediately available, returns 0.
        Otherwise sleeps until one becomes available.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * (self.capacity / self.window))
            self._last_refill = now

            if self._tokens >= 1:
                self._tokens -= 1
                return 0.0

            # Time until next token — don't zero _tokens or the
            # partial token fraction is lost. The next caller's
            # refill will correctly add elapsed refill to the
            # remaining partial.
            wait = (1 - self._tokens) * (self.window / self.capacity)

        await asyncio.sleep(wait)
        return wait


class EmptyProviderResponse(RuntimeError):
    """Raised when a provider completes without returning usable text."""


class RotatingProvider(BaseLLMProvider):
    """Wraps multiple LLM providers and rotates through them transparently.

    Respects free-tier rate limits by applying exponential backoff on 429
    errors and using a token-bucket limiter to smooth out request bursts.

    Usage::

        rotator = RotatingProvider([gemini, openrouter, groq])
        result = await rotator.generate("Hello")  # tries Gemini first
    """

    def __init__(
        self,
        providers: list[BaseLLMProvider],
        rate_limit_rpm: int = 60,
    ):
        """
        Args:
            providers: Ordered list of providers to rotate through.
            rate_limit_rpm: Target max requests per minute across all
                providers. Defaults to 60 to stay safely within most
                free-tier limits. Burst capacity is double the RPM so
                short bursts don't artificially delay users.
        """
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers = providers
        self._current_idx = 0
        self._lock = asyncio.Lock()
        # Burst capacity = 2x RPM so the first N requests are never delayed
        self._limiter = TokenBucket(capacity=rate_limit_rpm * 2, window_seconds=60.0)

    # ── internal ──────────────────────────────────────────────────────

    async def _try_all(self, method: str, **kwargs):
        """Try each provider in order until one succeeds.

        Applies exponential backoff (1s, 2s, 4s) on 429/rate-limit errors
        and uses a token-bucket rate limiter to stay within free-tier limits.
        """
        attempts = len(self.providers)

        async with self._lock:
            start_idx = self._current_idx

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            provider = self.providers[idx]
            name = getattr(provider, "name", type(provider).__name__)

            for retry in range(3):
                try:
                    func = getattr(provider, method)
                    result = await func(**kwargs)
                    if isinstance(result, str) and not result.strip():
                        raise EmptyProviderResponse(f"{name} returned an empty response")

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
                        f"Provider rotation: {name} {kind} for '{method}' retry {retry + 1}/3. Error: {err_msg}."
                    )
                    if retry < 2:
                        await asyncio.sleep(0.5 * (2 ** retry))
                        continue
                    break

        logger.error(
            f"All {attempts} provider(s) failed for '{method}'. "
            f"Last error: {last_error}"
        )
        raise last_error  # type: ignore[misc]

    async def _try_all_stream(self, method: str, **kwargs) -> AsyncGenerator[str, None]:
        """Try each provider in order until one succeeds, yielding chunks instantly."""
        attempts = len(self.providers)

        async with self._lock:
            start_idx = self._current_idx

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            provider = self.providers[idx]
            name = getattr(provider, "name", type(provider).__name__)

            for retry in range(3):
                emitted = False
                try:
                    func = getattr(provider, method)
                    gen = func(**kwargs)

                    async with self._lock:
                        self._current_idx = idx

                    async for chunk in gen:
                        if chunk:
                            emitted = True
                            yield chunk

                    if not emitted:
                        raise EmptyProviderResponse(f"{name} returned an empty stream")
                    return

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
                        f"Provider rotation: {name} {kind} for '{method}' retry {retry + 1}/3. Error: {err_msg}."
                    )
                    if retry < 2:
                        await asyncio.sleep(0.5 * (2 ** retry))
                        continue
                    break

        logger.error(
            f"All {attempts} provider(s) failed for '{method}'. "
            f"Last error: {last_error}"
        )
        raise last_error  # type: ignore[misc]

    # ── public generation ──────────────────────────────────────────────

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

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._try_all_stream(
            "generate_stream",
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ):
            yield chunk
