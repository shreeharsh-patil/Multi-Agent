import uuid
from types import SimpleNamespace

import pytest
from google.adk.tools import google_search

from src.adk import runner
from src.adk.tools import web_search_tool
from src.config import Settings
from src.services.llm.adk_model_rotator import AdkModelRoute, AdkModelRotator


@pytest.mark.asyncio
async def test_get_or_create_session_awaits_adk_session_service():
    session_id = f"test-{uuid.uuid4()}"
    session = await runner.get_or_create_session("test-user", session_id)

    assert session.id == session_id
    persisted = await runner.SESSION_SERVICE.get_session(
        app_name=runner.APP_NAME,
        user_id="test-user",
        session_id=session_id,
    )
    assert persisted is not None


def test_adk_rejects_non_ai_studio_credentials(monkeypatch):
    monkeypatch.setattr(runner.settings, "adk_enabled", True)
    monkeypatch.setattr(runner.settings, "gemini_api_key", "not-a-google-ai-studio-key")
    for name in (
        "groq_api_key", "openrouter_api_key", "mistral_api_key",
        "aiand_api_key", "nararouter_api_key", "kimi_api_key",
    ):
        monkeypatch.setattr(runner.settings, name, "")

    assert runner.use_adk() is False
    assert runner.get_adk_status()["status"] == "invalid_key_format"


def test_adk_accepts_plausible_ai_studio_credentials(monkeypatch):
    monkeypatch.setattr(runner.settings, "adk_enabled", True)
    monkeypatch.setattr(runner.settings, "gemini_api_key", "AIza" + "a" * 35)

    assert runner.use_adk() is True
    status = runner.get_adk_status()
    assert status["enabled"] is True
    assert status["status"] == "configured"
    assert status["model"] == runner.settings.gemini_model
    assert status["adk_specialists"] >= 100


def test_non_gemini_adk_fallback_replaces_native_google_search():
    """A dead Gemini route must not prevent ADK workers from answering."""
    primary_model = object()
    agent = SimpleNamespace(
        name="google_search_general",
        model=None,
        tools=[google_search],
        sub_agents=[],
    )

    runner._apply_adk_models(agent, primary_model, grounding_model=None)

    assert agent.model is primary_model
    assert agent.tools == [web_search_tool]
    assert runner._uses_native_google_search(agent) is False


def test_adk_remains_enabled_with_only_litellm_fallback(monkeypatch):
    monkeypatch.setattr(runner.settings, "adk_enabled", True)
    monkeypatch.setattr(runner.settings, "gemini_api_key", "")
    monkeypatch.setattr(runner.settings, "groq_api_key", "gsk_configured")

    assert runner.use_adk() is True
    assert runner.get_adk_status()["status"] == "configured_fallback"


def test_retired_render_gemini_model_is_migrated():
    configured = Settings(
        _env_file=None,
        debug=True,
        secret_key="diagnostic-secret-key",
        gemini_model="gemini-2.0-flash",
    )

    assert configured.gemini_model == "gemini-3.7-flash"


def test_fast_adk_boss_has_no_specialist_tree():
    route = AdkModelRoute(
        provider="gemini",
        model="gemini-3.7-flash",
        api_key="AQ." + "a" * 40,
    )

    agent = runner.get_fast_boss_agent(route)

    assert agent.name == "boss_agent"
    assert list(agent.sub_agents) == []


def test_stale_provider_models_are_migrated():
    configured = Settings(
        _env_file=None,
        debug=True,
        secret_key="diagnostic-secret-key",
        openrouter_model="google/gemini-2.0-flash-exp:free",
        groq_model="openai/gpt-oss-20b",
        aiand_model="qwen/qwen-2.5-72b-instruct",
    )

    assert configured.openrouter_model == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert configured.groq_model == "qwen/qwen3.6-27b"
    assert configured.aiand_model == "qwen/qwen3.6-27b"


@pytest.mark.asyncio
async def test_fast_rotator_prefers_groq_and_quarantines_timeout(monkeypatch):
    rotator = AdkModelRotator()
    rotator._credentials_probed = True
    monkeypatch.setattr(runner.settings, "groq_api_key", "gsk_working")
    monkeypatch.setattr(runner.settings, "gemini_api_key", "AQ." + "a" * 40)
    for name in ("openrouter_api_key", "mistral_api_key", "aiand_api_key", "nararouter_api_key", "kimi_api_key"):
        monkeypatch.setattr(runner.settings, name, "")

    first = await rotator.next_fast_route()
    assert first.provider == "groq"

    await rotator.record_failure(first, TimeoutError())
    health = rotator.health_summary()
    assert health["groq"]["status"] == "unavailable"
    assert health["groq"]["ready_keys"] == 0
    second = await rotator.next_fast_route()
    assert second.provider == "gemini"


def test_fast_groq_boss_hides_reasoning():
    route = AdkModelRoute(
        provider="groq",
        model="qwen/qwen3.6-27b",
        api_key="gsk_diagnostic",
        api_base="https://api.groq.com/openai/v1",
    )

    agent = runner.get_fast_boss_agent(route)

    assert agent.model._additional_args["reasoning_format"] == "hidden"


def test_generation_probe_requires_nonempty_assistant_content():
    assert AdkModelRotator._has_generated_content(
        "gemini",
        {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
    ) is True
    assert AdkModelRotator._has_generated_content(
        "gemini",
        {"candidates": [{"content": {"parts": []}}]},
    ) is False
    assert AdkModelRotator._has_generated_content(
        "groq",
        {"choices": [{"message": {"content": "OK"}}]},
    ) is True
    assert AdkModelRotator._has_generated_content(
        "openrouter",
        {"choices": [{"message": {"content": ""}}]},
    ) is False


def test_generation_probe_failure_categories_are_secret_free():
    assert AdkModelRotator._failure_category(401) == "authentication"
    assert AdkModelRotator._failure_category(402) == "credits"
    assert AdkModelRotator._failure_category(404) == "model_or_endpoint"
    assert AdkModelRotator._failure_category(429) == "rate_limited"
    assert AdkModelRotator._failure_category(503) == "provider_unavailable"
    assert AdkModelRotator._failure_category(422) == "request_or_model"
    assert AdkModelRotator._failure_category(empty=True) == "empty_response"
    assert AdkModelRotator._failure_category() == "timeout_or_network"
