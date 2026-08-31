import uuid
from types import SimpleNamespace

import pytest
from google.adk.tools import google_search

from src.adk import runner
from src.adk.tools import web_search_tool


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
