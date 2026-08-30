"""Provider/key rotation for ADK model instances.

Native Google Search grounding remains on Gemini.  Other ADK agents can use
the official ADK LiteLLM connector against the configured OpenAI-compatible
providers without falling out of the ADK runtime.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.config import settings, split_gemini_api_keys


@dataclass(frozen=True)
class AdkModelRoute:
    provider: str
    model: str
    api_key: str
    api_base: str | None = None


class AdkModelRotator:
    def __init__(self) -> None:
        self._route_index = 0
        self._key_indices: dict[str, int] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _keys(value: str) -> list[str]:
        return split_gemini_api_keys(value) if ("AIza" in (value or "") or "AQ." in (value or "")) else [key.strip() for key in (value or "").split(",") if key.strip()]

    async def next_route(self) -> AdkModelRoute:
        """Select a provider and one of its API keys round-robin."""
        providers = [
            ("groq", settings.groq_model, settings.groq_api_key, "https://api.groq.com/openai/v1"),
            ("openrouter", settings.openrouter_model, settings.openrouter_api_key, settings.openrouter_base_url),
            ("mistral", settings.mistral_model, settings.mistral_api_key, settings.mistral_base_url),
            ("openai", settings.aiand_model, settings.aiand_api_key, settings.aiand_base_url),
            ("openai", settings.nararouter_model, settings.nararouter_api_key, settings.nararouter_base_url),
            ("openai", settings.kimi_model, settings.kimi_api_key, settings.kimi_base_url),
            ("gemini", settings.gemini_model, settings.gemini_api_key, None),
        ]
        enabled = [(provider, model, self._keys(keys), base) for provider, model, keys, base in providers if self._keys(keys)]
        if not enabled:
            raise ValueError("No ADK model provider is configured.")

        async with self._lock:
            provider, model, keys, base = enabled[self._route_index % len(enabled)]
            self._route_index = (self._route_index + 1) % len(enabled)
            identity = f"{provider}:{base or 'google'}"
            key_index = self._key_indices.get(identity, 0)
            key = keys[key_index % len(keys)]
            self._key_indices[identity] = (key_index + 1) % len(keys)
            return AdkModelRoute(provider=provider, model=model, api_key=key, api_base=base)


adk_model_rotator = AdkModelRotator()
