import pytest

from src.adk import tools
from src.api.routes import _chat_quality as quality


@pytest.mark.asyncio
async def test_web_search_uses_bing_when_other_engines_are_empty(monkeypatch):
    async def empty(*args, **kwargs):
        return []

    async def bing(*args, **kwargs):
        return [{
            "title": "Official Example",
            "url": "https://example.org/location",
            "snippet": "Example is located in Goa.",
            "source": "Bing Web",
        }]

    async def no_wiki(*args, **kwargs):
        return None

    tools._web_search_cache.clear()
    monkeypatch.setattr(tools, "_duckduckgo_search", empty)
    monkeypatch.setattr(tools, "_jina_search_items", empty)
    monkeypatch.setattr(tools, "_bing_html_search", bing)
    monkeypatch.setattr(tools, "_searxng_search_items", empty)
    monkeypatch.setattr(tools, "_wikipedia_search", no_wiki)

    result = await tools.web_search("Example Goa", for_research=True, max_items=8)
    assert "https://example.org/location" in result
    assert "Official Example" in result


@pytest.mark.asyncio
async def test_grounded_rescue_accepts_tool_url_when_primary_parser_misses(monkeypatch):
    async def fake_search(*args, **kwargs):
        return "### [Official] PCCE\nhttps://pccegoa.edu.in/contact-us/\nVerna Goa 403722"

    async def fake_generate(**kwargs):
        return "PCCE is in Verna, Goa."

    from src.adk import runner
    from src.services.llm import llm_service
    monkeypatch.setattr(tools, "web_search", fake_search)
    monkeypatch.setattr(runner, "_citations_from_search_text", lambda text: [])
    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = await quality._grounded_rescue("Where is PCCE Goa?")
    assert result is not None
    assert result["citations"]
    assert result["citations"][0]["url"] == "https://pccegoa.edu.in/contact-us/"
