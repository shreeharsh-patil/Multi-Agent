"""Provider/key rotation for ADK model instances.

Native Google Search grounding remains on Gemini.  Other ADK agents can use
the official ADK LiteLLM connector against the configured OpenAI-compatible
providers without falling out of the ADK runtime.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass

import httpx

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
        self._fast_route_index = 0
        self._key_indices: dict[str, int] = {}
        self._blocked_keys: set[str] = set()
        self._lock = asyncio.Lock()
        self._probe_lock = asyncio.Lock()
        self._credentials_probed = False

    @staticmethod
    def _keys(value: str, provider: str) -> list[str]:
        """Split comma-separated and accidentally concatenated provider keys."""
        raw = value or ""
        if provider == "gemini":
            return split_gemini_api_keys(raw)

        # Common provider prefixes are safe boundaries: the prefix cannot
        # occur inside a token before the next token begins. This supports the
        # no-comma format used in the environment without logging credentials.
        boundaries = {
            "groq": r"gsk_",
            "openrouter": r"sk-or-v1-",
        }
        boundary = boundaries.get(provider)
        if boundary and re.search(boundary, raw):
            if provider in {"groq", "openrouter"}:
                return [key for key in re.split(f"(?={boundary})", raw) if key]
        return [key.strip() for key in raw.split(",") if key.strip()]

    @staticmethod
    def _providers(fast: bool = False) -> list[tuple[str, str, str, str | None]]:
        providers = [
            # Gemini runs the ADK control plane and native Google Search. Try
            # it first; external providers remain ADK worker fallbacks.
            ("gemini", settings.gemini_model, settings.gemini_api_key, None),
            ("groq", settings.groq_model, settings.groq_api_key, "https://api.groq.com/openai/v1"),
            ("openrouter", settings.openrouter_model, settings.openrouter_api_key, settings.openrouter_base_url),
            ("mistral", settings.mistral_model, settings.mistral_api_key, settings.mistral_base_url),
            ("openai", settings.aiand_model, settings.aiand_api_key, settings.aiand_base_url),
            ("openai", settings.nararouter_model, settings.nararouter_api_key, settings.nararouter_base_url),
            ("openai", settings.kimi_model, settings.kimi_api_key, settings.kimi_base_url),
        ]
        if fast:
            priority = {"groq": 0, "gemini": 1, "openrouter": 2}
            providers.sort(key=lambda item: priority.get(item[0], 3))
        return providers

    async def _select_route(self, *, fast: bool = False) -> AdkModelRoute:
        await self.probe_credentials()
        providers = self._providers(fast=fast)
        enabled = [
            (provider, model, healthy_keys, base)
            for provider, model, keys, base in providers
            if (
                healthy_keys := [
                    key for key in self._keys(keys, provider)
                    if self._key_identity(provider, model, base, key) not in self._blocked_keys
                ]
            )
        ]
        if not enabled:
            raise ValueError("No ADK model provider is configured.")

        async with self._lock:
            index = self._fast_route_index if fast else self._route_index
            provider, model, keys, base = enabled[index % len(enabled)]
            if fast:
                self._fast_route_index = (index + 1) % len(enabled)
            else:
                self._route_index = (index + 1) % len(enabled)
            identity = f"{provider}:{base or 'google'}"
            key_index = self._key_indices.get(identity, 0)
            key = keys[key_index % len(keys)]
            self._key_indices[identity] = (key_index + 1) % len(keys)
            return AdkModelRoute(provider=provider, model=model, api_key=key, api_base=base)

    async def next_route(self) -> AdkModelRoute:
        """Select a Gemini-first route for full ADK orchestration."""
        return await self._select_route()

    async def next_fast_route(self) -> AdkModelRoute:
        """Select a low-latency ADK route, preferring a healthy Groq key."""
        return await self._select_route(fast=True)

    async def next_gemini_route(self) -> AdkModelRoute:
        """Select a healthy Gemini key for ADK control and Google grounding."""
        await self.probe_credentials()
        provider = "gemini"
        model = settings.gemini_model
        keys = [
            key for key in self._keys(settings.gemini_api_key, provider)
            if self._key_identity(provider, model, None, key) not in self._blocked_keys
        ]
        if not keys:
            raise ValueError("No healthy Gemini API key is configured for ADK Google Search grounding.")

        async with self._lock:
            identity = "gemini:google:grounding"
            key_index = self._key_indices.get(identity, 0)
            key = keys[key_index % len(keys)]
            self._key_indices[identity] = (key_index + 1) % len(keys)
            return AdkModelRoute(provider=provider, model=model, api_key=key)

    async def probe_credentials(self) -> None:
        """Quarantine explicitly rejected credentials once per process.

        Serverless cold starts previously spent most of the chat timeout
        constructing agent trees and attempting keys that were already invalid.
        These lightweight model-list requests reject bad authentication before
        a Runner is built. Network errors and rate limits remain retryable.
        """
        if self._credentials_probed:
            return
        async with self._probe_lock:
            if self._credentials_probed:
                return
            providers = self._providers()

            async def probe(provider: str, model: str, raw_keys: str, base: str | None) -> None:
                for key in self._keys(raw_keys, provider):
                    try:
                        if provider == "gemini":
                            url = "https://generativelanguage.googleapis.com/v1beta/models"
                            headers = {"x-goog-api-key": key}
                        else:
                            url = f"{(base or '').rstrip('/')}/models"
                            headers = {"Authorization": f"Bearer {key}"}
                        response = await client.get(url, headers=headers)
                        rejected = response.status_code in {401, 402, 403, 404}
                        if response.status_code == 200:
                            payload = response.json()
                            items = payload.get("models") or payload.get("data") or []
                            available_models = {
                                str(item.get("id") or item.get("name") or "").removeprefix("models/")
                                for item in items
                                if isinstance(item, dict)
                            }
                            if available_models and model not in available_models:
                                rejected = True
                        if rejected:
                            self._blocked_keys.add(self._key_identity(provider, model, base, key))
                    except (httpx.HTTPError, ValueError):
                        # A probe is an optimization, never a reason to disable
                        # an otherwise retryable provider route.
                        continue

            timeout = httpx.Timeout(6.0, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                await asyncio.gather(*(probe(*provider) for provider in providers))
            self._credentials_probed = True

    @staticmethod
    def _key_identity(provider: str, model: str, api_base: str | None, api_key: str) -> str:
        """Secret-free route identity used only for in-memory health tracking."""
        fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"{provider}:{model}:{api_base or ''}:{fingerprint}"

    async def record_failure(self, route: AdkModelRoute, error: Exception) -> None:
        """Quarantine credentials/models that cannot recover by retrying."""
        message = f"{type(error).__name__}: {error}".lower()
        permanent_markers = (
            "401", "unauthenticated", "invalid api key", "invalid authentication",
            "404", "model_not_found", "model not found", "decommissioned",
            "no endpoints found", "not supported", "402", "insufficient credits",
            "timeouterror", "timed out",
        )
        if not any(marker in message for marker in permanent_markers):
            return
        async with self._lock:
            self._blocked_keys.add(self._key_identity(route.provider, route.model, route.api_base, route.api_key))

    async def record_success(self, route: AdkModelRoute) -> None:
        async with self._lock:
            self._blocked_keys.discard(self._key_identity(route.provider, route.model, route.api_base, route.api_key))

    def health_summary(self) -> dict[str, dict[str, int | str]]:
        """Return secret-free configured and currently usable route counts."""
        summary: dict[str, dict[str, int | str]] = {}
        for provider, model, raw_keys, base in self._providers():
            if provider == "openai":
                if base == settings.aiand_base_url:
                    label = "aiand"
                elif base == settings.nararouter_base_url:
                    label = "nararouter"
                elif base == settings.kimi_base_url:
                    label = "kimi"
                else:
                    label = "openai_compatible"
            else:
                label = provider
            keys = self._keys(raw_keys, provider)
            ready = sum(
                self._key_identity(provider, model, base, key) not in self._blocked_keys
                for key in keys
            )
            summary[label] = {
                "status": "ready" if ready else ("unavailable" if keys else "not_configured"),
                "configured_keys": len(keys),
                "ready_keys": ready,
            }
        return summary

    def reset_health(self) -> None:
        """Clear in-memory quarantine after configuration or deployment changes."""
        self._blocked_keys.clear()
        self._credentials_probed = False


adk_model_rotator = AdkModelRotator()
