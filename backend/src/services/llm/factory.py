"""LLM provider factory - selects provider based on config."""

from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_compat import OpenAICompatibleProvider

_LLMProvider: Optional[BaseLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    global _LLMProvider
    if _LLMProvider is not None:
        return _LLMProvider

    provider_name = settings.llm_provider.lower()

    if provider_name == "gemini":
        _LLMProvider = GeminiProvider()
    elif provider_name == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        _LLMProvider = OpenAICompatibleProvider(
            name="OpenRouter",
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
        )
    elif provider_name == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")
        _LLMProvider = OpenAICompatibleProvider(
            name="Groq",
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
        )
    elif provider_name == "nararouter":
        if not settings.nararouter_api_key:
            raise ValueError("NARAROUTER_API_KEY not configured")
        _LLMProvider = OpenAICompatibleProvider(
            name="NaraRouter",
            api_key=settings.nararouter_api_key,
            model=settings.nararouter_model,
            base_url=settings.nararouter_base_url,
        )
    elif provider_name == "mistral":
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY not configured")
        _LLMProvider = OpenAICompatibleProvider(
            name="Mistral",
            api_key=settings.mistral_api_key,
            model=settings.mistral_model,
            base_url=settings.mistral_base_url,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: gemini, openrouter, groq, nararouter, mistral")

    logger.info(f"LLM provider selected: {provider_name}")
    return _LLMProvider
