import pytest


@pytest.mark.asyncio
async def test_stream_recovery_uses_non_streaming_adk_path(monkeypatch):
    from src.api.routes import chat

    async def fake_process_message(**kwargs):
        assert kwargs["message"] == "augmented request"
        assert kwargs["user_id"] == "user-1"
        assert kwargs["conversation_id"] == "conv-1"
        return {
            "output": "Recovered answer",
            "citations": [{"file_name": "Source", "url": "https://example.com"}],
        }

    monkeypatch.setattr(chat, "process_message", fake_process_message)
    result = await chat._recover_stream_response(
        "augmented request", "user-1", "conv-1", None, "req-12345678"
    )

    assert result is not None
    assert result["output"] == "Recovered answer"


@pytest.mark.asyncio
async def test_stream_recovery_returns_none_when_fallback_fails(monkeypatch):
    from src.api.routes import chat

    async def failing_process_message(**kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(chat, "process_message", failing_process_message)
    result = await chat._recover_stream_response(
        "request", "user-1", "conv-1", None, "req-12345678"
    )

    assert result is None
