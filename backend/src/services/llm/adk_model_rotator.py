"""Provider/key rotation for ADK model instances.

Native Google Search grounding remains on Gemini. Other ADK agents can use
the official ADK LiteLLM connector against configured OpenAI-compatible
providers without falling out of the ADK runtime.

Routing is deliberately *preference based*, not round-robin. A healthy primary
route is reused across requests for consistent answer quality. The fallback
cursor advances only after a real runtime failure and resets after a successful
response. This prevents adjacent chat turns from silently switching models.
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
        # These are failover cursors, not round-robin request cursors. They
        # remain at the preferred route until record_failure() advances them.
        self._route_index = 0
        self._fast_route_index = 0
        self._key_indices: dict[str, int] = {}
        self._blocked_keys: set[str] = set()
        self._blocked_reasons: dict[str, str] = {}
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
        """Select the currently preferred healthy route.

        The cursor is intentionally not advanced here. Merely receiving a new
        user request is not a reason to change models. ``record_failure`` moves
        the cursor to a fallback; ``record_success`` moves it back to the best
        healthy route for the next request.
        """
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
            # A provider can disappear after credential quarantine. Clamp the
            # failover cursor so we never skip the new first healthy provider.
            if index >= len(enabled):
                index = 0
                if fast:
                    self._fast_route_index = 0
                else:
                    self._route_index = 0
            provider, model, keys, base = enabled[index]
            identity = f"{provider}:{base or 'google'}"
            key_index = self._key_indices.get(identity, 0)
            key = keys[key_index % len(keys)]
            # Rotate keys within a provider for quota distribution, while
            # keeping the provider/model itself stable for answer consistency.
            self._key_indices[identity] = (key_index + 1) % len(keys)
            return AdkModelRoute(provider=provider, model=model, api_key=key, api_base=base)

    async def next_route(self) -> AdkModelRoute:
        """Select the best healthy route for full ADK orchestration."""
        return await self._select_route()

    async def next_fast_route(self) -> AdkModelRoute:
        """Select the best healthy low-latency route, preferring Groq."""
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

    @staticmethod
    def _failure_category(status_code: int | None = None, *, empty: bool = False) -> str:
        if empty:
            return "empty_response"
        if status_code in {401, 403}:
            return "authentication"
        if status_code == 402:
            return "credits"
        if status_code == 404:
            return "model_or_endpoint"
        if status_code == 429:
            return "rate_limited"
        if status_code is not None and status_code >= 500:
            return "provider_unavailable"
        if status_code in {400, 405, 409, 422}:
            return "request_or_model"
        if status_code is not None:
            return "provider_error"
        return "timeout_or_network"

    @staticmethod
    def _has_generated_content(provider: str, payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        if provider == "gemini":
            candidates = payload.get("candidates") or []
            return any(
                isinstance(part, dict) and bool(str(part.get("text") or "").strip())
                for candidate in candidates if isinstance(candidate, dict)
                for part in ((candidate.get("content") or {}).get("parts") or [])
                if isinstance(candidate.get("content"), dict)
            )
        choices = payload.get("choices") or []
        return any(
            isinstance(choice, dict)
            and isinstance(choice.get("message"), dict)
            and bool(str(choice["message"].get("content") or "").strip())
            for choice in choices
        )

    async def probe_credentials(self) -> None:
        """Admit only credentials that complete a real minimal generation.

        Model-list checks produced false positives: a key could list a model but
        still fail chat because of quota, endpoint, timeout, or empty-output
        errors. Every configured key is tested concurrently against the same
        generation endpoint the ADK adapter ultimately uses.
        """
        if self._credentials_probed:
            return
        async with self._probe_lock:
            if self._credentials_probed:
                return
            providers = self._providers()

            async def probe_one(provider: str, model: str, key: str, base: str | None) -> None:
                identity = self._key_identity(provider, model, base, key)
                try:
                    if provider == "gemini":
                        url = (
                            "https://generativelanguage.googleapis.com/v1beta/"
                            f"models/{model}:generateContent"
                        )
                        headers = {"x-goog-api-key": key}
                        body = {
                            "contents": [{"role": "user", "parts": [{"text": "Reply only OK"}]}],
                            "generationConfig": {"maxOutputTokens": 64, "temperature": 0},
                        }
                    else:
                        url = f"{(base or '').rstrip('/')}/chat/completions"
                        headers = {"Authorization": f"Bearer {key}"}
                        body = {
                            "model": model,
                            "messages": [{"role": "user", "content": "Reply only OK"}],
                            # Reasoning models can consume a small token budget
                            # before producing assistant-visible content.
                            "max_tokens": 128 if provider == "groq" else 32,
                            "temperature": 0,
                            "stream": False,
                        }
                        if provider == "groq":
                            body["reasoning_format"] = "hidden"
                    response = await client.post(url, headers=headers, json=body)
                    category = None
                    if response.status_code < 200 or response.status_code >= 300:
                        category = self._failure_category(response.status_code)
                    else:
                        try:
                            generated = self._has_generated_content(provider, response.json())
                        except ValueError:
                            generated = False
                        if not generated:
                            category = self._failure_category(empty=True)
                    if category:
                        self._blocked_keys.add(identity)
                        self._blocked_reasons[identity] = category
                    else:
                        self._blocked_keys.discard(identity)
                        self._blocked_reasons.pop(identity, None)
                except (httpx.HTTPError, asyncio.TimeoutError):
                    self._blocked_keys.add(identity)
                    self._blocked_reasons[identity] = self._failure_category()

            probes = [
                probe_one(provider, model, key, base)
                for provider, model, raw_keys, base in providers
                for key in self._keys(raw_keys, provider)
            ]
            probe_seconds = max(3, settings.adk_provider_probe_timeout_seconds)
            timeout = httpx.Timeout(float(probe_seconds), connect=min(5.0, float(probe_seconds)))
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                await asyncio.gather(*probes)
            self._credentials_probed = True

    @staticmethod
    def _key_identity(provider: str, model: str, api_base: str | None, api_key: str) -> str:
        """Secret-free route identity used only for in-memory health tracking."""
        fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"{provider}:{model}:{api_base or ''}:{fingerprint}"

    async def record_failure(self, route: AdkModelRoute, error: Exception) -> None:
        """Advance failover after a runtime failure and quarantine bad routes.

        Permanent failures remove the broken credential/model and restart from
        the first remaining healthy provider. Transient failures advance one
        provider for the current retry chain without permanently degrading the
        preferred model for future successful requests.
        """
        message = f"{type(error).__name__}: {error}".lower()
        permanent_markers = (
            "401", "unauthenticated", "invalid api key", "invalid authentication",
            "404", "model_not_found", "model not found", "decommissioned",
            "no endpoints found", "not supported", "402", "insufficient credits",
            "timeouterror", "timed out",
        )
        permanent = any(marker in message for marker in permanent_markers)

        async with self._lock:
            if permanent:
                identity = self._key_identity(route.provider, route.model, route.api_base, route.api_key)
                self._blocked_keys.add(identity)
                self._blocked_reasons[identity] = "runtime_failure"
                self._route_index = 0
                self._fast_route_index = 0
            else:
                # Move to the next healthy provider only because a real call
                # failed. Both cursors advance so either retry mode can escape
                # a temporarily unhealthy provider.
                self._route_index += 1
                self._fast_route_index += 1

    async def record_success(self, route: AdkModelRoute) -> None:
        """Mark a route healthy and restore primary preference for new turns."""
        async with self._lock:
            identity = self._key_identity(route.provider, route.model, route.api_base, route.api_key)
            self._blocked_keys.discard(identity)
            self._blocked_reasons.pop(identity, None)
            self._route_index = 0
            self._fast_route_index = 0

    def health_summary(self) -> dict[str, dict[str, object]]:
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
            route_identities = [self._key_identity(provider, model, base, key) for key in keys]
            failure_categories: dict[str, int] = {}
            for identity in route_identities:
                reason = self._blocked_reasons.get(identity)
                if reason:
                    failure_categories[reason] = failure_categories.get(reason, 0) + 1
            summary[label] = {
                "status": "ready" if ready else ("unavailable" if keys else "not_configured"),
                "configured_keys": len(keys),
                "ready_keys": ready,
                "validation": "generation" if self._credentials_probed else "pending",
                "failures": failure_categories,
            }
        return summary

    def reset_health(self) -> None:
        """Clear in-memory quarantine after configuration or deployment changes."""
        self._blocked_keys.clear()
        self._blocked_reasons.clear()
        self._route_index = 0
        self._fast_route_index = 0
        self._credentials_probed = False


adk_model_rotator = AdkModelRotator()
