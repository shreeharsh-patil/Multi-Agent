"""LLM provider factory - discovers all configured providers for auto-rotation.

Instead of picking a single provider, returns a RotatingProvider that wraps
all configured providers and falls back through them when one fails.
"""

from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_compat import OpenAICompatibleProvider

_LLMProvider: Optional[BaseLLMProvider] = None


def _build_providers() -> list[BaseLLMProvider]:
    """Build a list of all configured LLM providers, in priority order.

    AIand (Qwen) is the default provider and is tried first.
    Gemini is always included as the final fallback (if configured)
    because ADK orchestrator requires it for multi-agent orchestration.
    """
    providers: list[BaseLLMProvider] = []

    if settings.aiand_api_key:
        providers.append(OpenAICompatibleProvider(
            name="AIand",
            api_key=settings.aiand_api_key,
            model=settings.aiand_model,
            base_url=settings.aiand_base_url,
        ))

    if settings.openrouter_api_key:
        providers.append(OpenAICompatibleProvider(
            name="OpenRouter",
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
        ))

    if settings.groq_api_key:
        providers.append(OpenAICompatibleProvider(
            name="Groq",
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
        ))

    if settings.mistral_api_key:
        providers.append(OpenAICompatibleProvider(
            name="Mistral",
            api_key=settings.mistral_api_key,
            model=settings.mistral_model,
            base_url=settings.mistral_base_url,
        ))

    if settings.nararouter_api_key:
        providers.append(OpenAICompatibleProvider(
            name="NaraRouter",
            api_key=settings.nararouter_api_key,
            model=settings.nararouter_model,
            base_url=settings.nararouter_base_url,
        ))

    if settings.gemini_api_key:
        providers.append(GeminiProvider())

    logger.info(f"Auto-discovered {len(providers)} LLM provider(s): {[type(p).__name__ if hasattr(type(p), '__name__') else str(type(p)) for p in providers]}")
    return providers


def get_llm_provider() -> BaseLLMProvider:
    """Return a RotatingProvider that wraps all configured LLM providers.

    Each call to ``generate()`` starts with the preferred provider (AIand/Qwen)
    and falls back through OpenRouter → Groq → Mistral → NaraRouter → Gemini
    if the current provider's keys are exhausted or the service is unavailable.
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

    _LLMProvider = RotatingProvider(providers)
    logger.info(
        f"LLM service ready with {len(providers)} provider(s) — "
        f"auto-rotation enabled"
    )
    return _LLMProvider
