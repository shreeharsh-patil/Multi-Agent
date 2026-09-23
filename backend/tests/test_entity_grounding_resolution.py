import pytest

from src.adk import tools
from src.api.routes import _chat_quality as quality


def test_pcc_goa_evidence_relevance_rejects_wrong_entity():
    request = "Where is PCCE Goa?"
    wrong = "### Source 1: Pacific Coast Convention Expo\nURL: https://example.com/pcc\nCalifornia event venue"
    right = (
        "### Source 1: Padre Conceicao College of Engineering\n"
        "URL: https://pccegoa.edu.in/contact-us/\n"
        "PCCE is located at Verna, Goa 403722."
    )
    assert not quality._evidence_matches_entity(request, wrong)
    assert quality._evidence_matches_entity(request, right)


def test_pcc_goa_second_stage_queries_preserve_acronym_and_goa():
    queries = quality._grounding_resolution_queries("Where is PCCE Goa?")
    joined = "\n".join(queries)
    assert '"PCCE" Goa full form' in joined
    assert '"PCCE" Goa official site' in joined
    assert '"PCCE" Goa address' in joined


def test_long_entity_name_is_not_misread_as_acronym():
    acronym, qualifiers, useful = quality._entity_terms(
        "Where is Padre Conceicao College of Engineering Goa?"
    )
    assert acronym is None
    assert "Padre" in useful
    assert "Conceicao" in useful


@pytest.mark.asyncio
async def test_grounded_rescue_retries_targeted_entity_queries(monkeypatch):
    calls = []

    async def fake_search(query, **kwargs):
        calls.append(query)
        if "full form" in query.lower():
            return (
                "### Source 1: Padre Conceicao College of Engineering (Official)\n"
                "URL: https://pccegoa.edu.in/contact-us/\n"
                "Padre Conceicao College of Engineering (PCCE), Agnel Technical "
                "Education Complex, Verna Goa, 403722."
            )
        return (
            "### Source 1: Unrelated PCCE\n"
            "URL: https://example.com/unrelated\n"
            "An unrelated acronym result in California."
        )

    async def fake_generate(**kwargs):
        return "PCCE is in Verna, Goa, at the Agnel Technical Education Complex."

    monkeypatch.setattr(tools, "web_search", fake_search)
    from src.services.llm import llm_service
    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = await quality._grounded_rescue("Where is PCCE Goa?")
    assert result is not None
    assert "Verna, Goa" in result["output"]
    assert result["citations"][0]["url"].startswith("https://pccegoa.edu.in")
    assert any("full form" in q.lower() for q in calls)


@pytest.mark.asyncio
async def test_firecrawl_search_parser_accepts_current_web_envelope(monkeypatch):
    monkeypatch.setattr(tools.firecrawl_rotator, "get_keys", lambda: ["fc-test"])

    async def fake_execute(method, endpoint, **kwargs):
        assert method == "POST"
        assert endpoint == "/search"
        assert kwargs["json"]["query"] == "PCCE Goa"
        return {
            "data": {
                "web": [
                    {
                        "title": "Padre Conceicao College of Engineering",
                        "url": "https://pccegoa.edu.in/",
                        "description": "PCCE is an engineering college in Verna, Goa.",
                    }
                ]
            }
        }

    monkeypatch.setattr(tools.firecrawl_rotator, "execute_request", fake_execute)
    results = await tools._firecrawl_search_items("PCCE Goa", 5)
    assert results == [
        {
            "title": "Padre Conceicao College of Engineering",
            "url": "https://pccegoa.edu.in/",
            "snippet": "PCCE is an engineering college in Verna, Goa.",
            "source": "Firecrawl Search",
        }
    ]


@pytest.mark.asyncio
async def test_research_web_search_includes_firecrawl_provider(monkeypatch):
    async def empty(*args, **kwargs):
        return []

    async def firecrawl(*args, **kwargs):
        return [{
            "title": "PCCE Official",
            "url": "https://pccegoa.edu.in/",
            "snippet": "PCCE is in Verna, Goa.",
            "source": "Firecrawl Search",
        }]

    monkeypatch.setattr(tools.firecrawl_rotator, "get_keys", lambda: ["fc-test"])
    monkeypatch.setattr(tools, "_firecrawl_search_items", firecrawl)
    monkeypatch.setattr(tools, "_duckduckgo_search", empty)
    monkeypatch.setattr(tools, "_jina_search_items", empty)
    monkeypatch.setattr(tools, "_bing_html_search", empty)
    monkeypatch.setattr(tools, "_searxng_search_items", empty)
    monkeypatch.setattr(tools, "_wikipedia_search", empty)
    tools._web_search_cache.clear()

    output = await tools.web_search("PCCE Goa", for_research=True, max_items=8)
    assert "https://pccegoa.edu.in" in output
    assert "PCCE Official" in output


def test_mixed_acronym_results_keep_only_pcce_goa_sources():
    mixed = (
        "### Source 1: GitHub PCCE Save Editor (DuckDuckGo Web)\n"
        "URL: https://github.com/example/PCCE\n"
        "A save editor for a game.\n\n"
        "### Source 2: Padre Conceicao College of Engineering (DuckDuckGo Web)\n"
        "URL: https://pccegoa.edu.in/\n"
        "Padre Conceicao College of Engineering (PCCE) is in Verna, Goa, India.\n\n"
        "### Source 3: PCCE Conference (DuckDuckGo Web)\n"
        "URL: https://example.cn/pcce\n"
        "An engineering conference in Guangzhou, China."
    )
    filtered = quality._filter_entity_evidence("Where is PCCE Goa?", mixed)
    assert "https://pccegoa.edu.in/" in filtered
    assert "github.com/example/PCCE" not in filtered
    assert "example.cn/pcce" not in filtered


@pytest.mark.asyncio
async def test_grounded_rescue_filters_unrelated_sources_from_synthesis(monkeypatch):
    mixed = (
        "### Source 1: GitHub PCCE Save Editor\n"
        "URL: https://github.com/example/PCCE\n"
        "A save editor for a game.\n\n"
        "### Source 2: Padre Conceicao College of Engineering\n"
        "URL: https://pccegoa.edu.in/\n"
        "Padre Conceicao College of Engineering (PCCE) is in Verna, Goa, India."
    )

    async def fake_search(*args, **kwargs):
        return mixed

    captured = {}

    async def fake_generate(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return "PCCE is in Verna, Goa."

    monkeypatch.setattr(tools, "web_search", fake_search)
    from src.services.llm import llm_service
    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = await quality._grounded_rescue("Where is PCCE Goa?")
    assert result is not None
    assert "https://pccegoa.edu.in/" in captured["prompt"]
    assert "github.com/example/PCCE" not in captured["prompt"]
    assert all("github.com/example/PCCE" not in c["url"] for c in result["citations"])


@pytest.mark.asyncio
async def test_web_search_does_not_return_ranker_rejected_garbage(monkeypatch):
    irrelevant = [
        {
            "title": f"Seattle travel result {i}",
            "url": f"https://travel.example/{i}",
            "snippet": "A Seattle travel itinerary with no requested institution.",
            "source": "Primary",
        }
        for i in range(8)
    ]

    async def primary(*args, **kwargs):
        return list(irrelevant)

    async def empty(*args, **kwargs):
        return []

    async def relevant_fallback(*args, **kwargs):
        return [{
            "title": "PCCE | Padre Conceicao College of Engineering",
            "url": "https://pccegoa.edu.in/",
            "snippet": "PCCE is an engineering college in Verna, Goa, India.",
            "source": "SearXNG",
        }]

    monkeypatch.setattr(tools, "_duckduckgo_search", primary)
    monkeypatch.setattr(tools, "_jina_search_items", empty)
    monkeypatch.setattr(tools, "_bing_html_search", empty)
    monkeypatch.setattr(tools, "_searxng_search_items", relevant_fallback)
    monkeypatch.setattr(tools, "_ddg_html_search", empty)
    monkeypatch.setattr(tools, "_wikipedia_search", empty)
    monkeypatch.setattr(tools.firecrawl_rotator, "get_keys", lambda: [])
    tools._web_search_cache.clear()

    output = await tools.web_search("PCCE Goa", for_research=True, max_items=8)
    assert "https://pccegoa.edu.in/" in output
    assert "Seattle travel" not in output


@pytest.mark.asyncio
async def test_web_search_returns_no_evidence_when_every_result_is_rejected(monkeypatch):
    async def irrelevant(*args, **kwargs):
        return [{
            "title": "Seattle itinerary",
            "url": "https://travel.example/seattle",
            "snippet": "Things to do in Seattle.",
            "source": "Web",
        }]

    async def empty(*args, **kwargs):
        return []

    monkeypatch.setattr(tools, "_duckduckgo_search", irrelevant)
    monkeypatch.setattr(tools, "_jina_search_items", empty)
    monkeypatch.setattr(tools, "_bing_html_search", empty)
    monkeypatch.setattr(tools, "_searxng_search_items", empty)
    monkeypatch.setattr(tools, "_ddg_html_search", empty)
    monkeypatch.setattr(tools, "_wikipedia_search", empty)
    monkeypatch.setattr(tools.firecrawl_rotator, "get_keys", lambda: [])
    tools._web_search_cache.clear()

    output = await tools.web_search("PCCE Goa", for_research=True, max_items=8)
    assert output.startswith("No live search results found")
    assert "Seattle itinerary" not in output
