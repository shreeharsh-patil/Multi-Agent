"""LLM provider factory - discovers all configured providers for auto-rotation.

Instead of picking a single provider, returns a RotatingProvider that wraps
all configured providers and falls back through them when one fails.

On first load, kicks off a background warmup of the AIand (Qwen) provider
so its free-tier cold start (~30-60s) doesn't delay the first real request.
"""

import asyncio
from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_compat import OpenAICompatibleProvider

_LLMProvider: Optional[BaseLLMProvider] = None
_aiand_warmup_done: asyncio.Event | None = None


def _build_providers() -> list[BaseLLMProvider]:
    """Build a list of all configured LLM providers, in priority order.

    Groq is first because it's proven fast (1-2s replies) and has a generous
    free tier (14,400 req/day with llama-3.1-8b-instant).
    AIand (Qwen) is second as a free fallback with warmup handling.
    Gemini is the final fallback for ADK multi-agent orchestration.
    """
    providers: list[BaseLLMProvider] = []

    if settings.groq_api_key:
        providers.append(OpenAICompatibleProvider(
            name="Groq",
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
            timeout_seconds=10,
        ))

    if settings.aiand_api_key:
        providers.append(OpenAICompatibleProvider(
            name="AIand",
            api_key=settings.aiand_api_key,
            model=settings.aiand_model,
            base_url=settings.aiand_base_url,
            timeout_seconds=60,  # Cold start on free tier can take ~30-60s
        ))

    if settings.openrouter_api_key:
        providers.append(OpenAICompatibleProvider(
            name="OpenRouter",
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            timeout_seconds=10,
        ))

    if settings.mistral_api_key:
        providers.append(OpenAICompatibleProvider(
            name="Mistral",
            api_key=settings.mistral_api_key,
            model=settings.mistral_model,
            base_url=settings.mistral_base_url,
            timeout_seconds=10,
        ))

    if settings.nararouter_api_key:
        providers.append(OpenAICompatibleProvider(
            name="NaraRouter",
            api_key=settings.nararouter_api_key,
            model=settings.nararouter_model,
            base_url=settings.nararouter_base_url,
            timeout_seconds=10,
        ))

    if settings.kimi_api_key:
        providers.append(OpenAICompatibleProvider(
            name="Kimi",
            api_key=settings.kimi_api_key,
            model=settings.kimi_model,
            base_url=settings.kimi_base_url,
            timeout_seconds=20,
        ))

    if settings.gemini_api_key:
        providers.append(GeminiProvider())

    logger.info(f"Auto-discovered {len(providers)} LLM provider(s): {[type(p).__name__ if hasattr(type(p), '__name__') else str(type(p)) for p in providers]}")
    return providers


async def _warmup_aiand(providers: list[BaseLLMProvider]) -> None:
    """Fire a tiny warmup request to AIand in the background.

    The free-tier model unloads after inactivity and takes ~30-60s
    to cold-start. This keeps it warm after the first real use or
    primes it for a fast first reply.

    Sets ``_aiand_warmup_done`` so that ``wait_for_aiand_warmup()``
    can await completion before routing real requests to AIand.
    """
    global _aiand_warmup_done
    try:
        for p in providers:
            name = getattr(p, "name", "")
            if name == "AIand":
                logger.info("Warming up AIand (Qwen) in background...")
                try:
                    await asyncio.wait_for(
                        p.generate(prompt="Hello"),
                        timeout=70.0,
                    )
                    logger.info("AIand (Qwen) warmup complete")
                except asyncio.TimeoutError:
                    logger.warning("AIand warmup timed out (cold start slow) — will warm on first real request")
                except Exception as e:
                    logger.warning(f"AIand warmup failed: {e}")
                return
    finally:
        # Signal completion in all exit paths so wait_for_aiand_warmup()
        # never hangs, even if AIand is not configured at all.
        if _aiand_warmup_done is not None:
            _aiand_warmup_done.set()


def get_llm_provider() -> BaseLLMProvider:
    """Return a RotatingProvider that wraps all configured LLM providers.

    Each call to ``generate()`` starts with Groq (fastest) and falls back
    through AIand → OpenRouter → Mistral → NaraRouter → Gemini if the
    current provider's keys are exhausted or the service is unavailable.

    On first initialization, kicks off a background warmup of AIand so its
    free-tier cold start doesn't affect the user experience.
    """
    global _LLMProvider
    if _LLMProvider is not None:
        return _LLMProvider

    from src.services.llm.rotator import RotatingProvider
    providers = _build_providers()

    if not providers:
        raise ValueError(
            "No LLM providers configured. Set at least one of: "
            "GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, "
            "MISTRAL_API_KEY, NARAROUTER_API_KEY, AIAND_API_KEY in your .env file."
        )

    _LLMProvider = RotatingProvider(providers, rate_limit_rpm=60)
    logger.info(
        f"LLM service ready with {len(providers)} provider(s) — "
        f"auto-rotation enabled, rate-limited to ~30 RPM (free-tier safe)"
    )

    # Fire-and-forget AIand warmup so its cold start doesn't
    # affect the first real user request. Only create the event
    # when AIand is actually in the provider chain.
    if any(getattr(p, "name", "") == "AIand" for p in providers):
        global _aiand_warmup_done
        _aiand_warmup_done = asyncio.Event()
        asyncio.create_task(_warmup_aiand(providers))

    return _LLMProvider


async def wait_for_aiand_warmup():
    """Await AIand warmup completion.

    Call this before routing a real request to AIand so the
    free-tier cold start doesn't delay the user.
    """
    if _aiand_warmup_done is not None:
        await _aiand_warmup_done.wait()
