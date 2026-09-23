import pytest

from src.api.routes import chat as chat_route


@pytest.mark.asyncio
async def test_last_resort_plain_provider_recovery(monkeypatch):
    async def fake_generate(**kwargs):
        return "Recovered answer"

    from src.services.llm import llm_service
    monkeypatch.setattr(llm_service, "generate", fake_generate)
    result = await chat_route._last_resort_chat_recovery(
        "Explain recursion simply", "req-test-plain", require_grounding=False
    )
    assert result["output"] == "Recovered answer"
    assert result["citations"] == []
    assert result["recovery_stage"] == "provider"


@pytest.mark.asyncio
async def test_last_resort_grounded_recovery_uses_web_evidence(monkeypatch):
    async def fake_search(*args, **kwargs):
        return "### Source 1: Official PCCE\nURL: https://example.edu/pcce\nPadre Conceicao College of Engineering, Verna, Goa"

    async def fake_generate(**kwargs):
        assert "LIVE WEB SEARCH EVIDENCE" in kwargs["prompt"]
        return "PCCE is in Verna, Goa."

    from src.adk import tools as adk_tools
    from src.adk import runner as adk_runner
    from src.services.llm import llm_service
    monkeypatch.setattr(adk_tools, "web_search", fake_search)
    monkeypatch.setattr(adk_runner, "_citations_from_search_text", lambda text: [{"file_name": "Official PCCE", "url": "https://example.edu/pcce"}])
    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = await chat_route._last_resort_chat_recovery(
        "Where is Pcce goa?", "req-test-grounded", require_grounding=True
    )
    assert result["output"] == "PCCE is in Verna, Goa."
    assert result["citations"][0]["url"] == "https://example.edu/pcce"
    assert result["recovery_stage"] == "grounded_provider"


@pytest.mark.asyncio
async def test_last_resort_grounded_recovery_fails_closed_without_sources(monkeypatch):
    async def fake_search(*args, **kwargs):
        return "No live search results found."

    from src.adk import tools as adk_tools
    from src.adk import runner as adk_runner
    monkeypatch.setattr(adk_tools, "web_search", fake_search)
    monkeypatch.setattr(adk_runner, "_citations_from_search_text", lambda text: [])

    result = await chat_route._last_resort_chat_recovery(
        "Where is UnknownXYZ?", "req-test-nosource", require_grounding=True
    )
    assert result is None


def test_last_resort_grounding_detection_covers_location_and_current_queries():
    assert chat_route._LAST_RESORT_GROUNDING_RE.search("Where is Pcce goa?")
    assert chat_route._LAST_RESORT_GROUNDING_RE.search("latest OpenAI news")
    assert not chat_route._LAST_RESORT_GROUNDING_RE.search("Explain recursion simply")
