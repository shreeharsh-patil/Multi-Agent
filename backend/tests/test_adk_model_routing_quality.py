from unittest.mock import AsyncMock

import pytest

from src.services.llm.adk_model_rotator import AdkModelRotator


FULL_ROUTES = [
    ("gemini", "gemini-test", "gemini-key", None),
    ("groq", "groq-test", "groq-key", "https://groq.invalid/v1"),
    ("openrouter", "openrouter-test", "openrouter-key", "https://openrouter.invalid/v1"),
]

FAST_ROUTES = [
    ("groq", "groq-test", "groq-key", "https://groq.invalid/v1"),
    ("gemini", "gemini-test", "gemini-key", None),
]


def _configured_rotator(routes):
    rotator = AdkModelRotator()
    rotator.probe_credentials = AsyncMock(return_value=None)
    rotator._providers = lambda fast=False: list(routes)
    return rotator


@pytest.mark.asyncio
async def test_successful_full_route_stays_on_primary_provider():
    rotator = _configured_rotator(FULL_ROUTES)

    first = await rotator.next_route()
    second = await rotator.next_route()

    assert first.provider == "gemini"
    assert second.provider == "gemini"


@pytest.mark.asyncio
async def test_transient_failure_uses_fallback_then_restores_primary():
    rotator = _configured_rotator(FULL_ROUTES)

    primary = await rotator.next_route()
    await rotator.record_failure(primary, RuntimeError("503 provider unavailable"))

    fallback = await rotator.next_route()
    assert fallback.provider == "groq"

    await rotator.record_success(fallback)
    recovered = await rotator.next_route()
    assert recovered.provider == "gemini"


@pytest.mark.asyncio
async def test_permanent_failure_quarantines_route_without_skipping_next_provider():
    rotator = _configured_rotator(FULL_ROUTES)

    broken = await rotator.next_route()
    await rotator.record_failure(broken, RuntimeError("404 model_not_found"))

    fallback = await rotator.next_route()
    assert fallback.provider == "groq"


@pytest.mark.asyncio
async def test_fast_route_is_stable_until_a_real_failure():
    rotator = _configured_rotator(FAST_ROUTES)

    first = await rotator.next_fast_route()
    second = await rotator.next_fast_route()

    assert first.provider == "groq"
    assert second.provider == "groq"

    await rotator.record_failure(second, RuntimeError("503 temporarily unavailable"))
    fallback = await rotator.next_fast_route()
    assert fallback.provider == "gemini"


@pytest.mark.asyncio
async def test_reset_health_restores_primary_cursor():
    rotator = _configured_rotator(FULL_ROUTES)

    primary = await rotator.next_route()
    await rotator.record_failure(primary, RuntimeError("503 temporarily unavailable"))
    assert (await rotator.next_route()).provider == "groq"

    rotator.reset_health()
    rotator.probe_credentials = AsyncMock(return_value=None)
    assert (await rotator.next_route()).provider == "gemini"
