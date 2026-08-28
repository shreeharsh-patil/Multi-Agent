import uuid

import pytest

from src.adk import runner


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
