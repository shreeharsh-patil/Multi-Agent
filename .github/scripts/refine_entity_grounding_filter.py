from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Entity evidence must be filtered per search source, not as one aggregate.
# ---------------------------------------------------------------------------
qpath = Path('backend/src/api/routes/_chat_quality.py')
text = qpath.read_text(encoding='utf-8')

anchor = '''def _grounding_resolution_queries(request_text: str) -> list[str]:\n'''
if anchor not in text:
    raise SystemExit('resolution query anchor missing')

helper = '''def _filter_entity_evidence(request_text: str, evidence: str) -> str:\n    \"\"\"Keep only individual search source blocks that match the requested entity.\n\n    A search engine can return several unrelated expansions for the same acronym.\n    Matching the aggregate result string is not sufficient because one correct\n    source would otherwise admit every unrelated source into final synthesis.\n    \"\"\"\n    rendered = str(evidence or \"\").strip()\n    if not rendered or not _is_entity_lookup_request(request_text):\n        return rendered\n\n    blocks = [\n        block.strip()\n        for block in re.split(r\"(?=^###\\s+Source\\s+\\d+:)\", rendered, flags=re.I | re.M)\n        if block.strip()\n    ]\n    # If a provider changed away from the normal structured Source format, keep\n    # the payload only when it still passes the same entity+qualifier check.\n    if len(blocks) <= 1 and not re.search(r\"^###\\s+Source\\s+\\d+:\", rendered, re.I | re.M):\n        return rendered if _evidence_matches_entity(request_text, rendered) else \"\"\n\n    matched = [block for block in blocks if _evidence_matches_entity(request_text, block)]\n    return \"\\n\\n\".join(matched)\n\n\n'''
text = text.replace(anchor, helper + anchor, 1)

old = '''            rendered = str(result or \"\").strip()\n            if not rendered or rendered.lower().startswith(\"no live search results found\"):\n                continue\n            if entity_lookup and not _evidence_matches_entity(request_text, rendered):\n                continue\n            evidence_parts.append(f\"SEARCH QUERY: {query}\\n{rendered}\")\n'''
new = '''            rendered = str(result or \"\").strip()\n            if not rendered or rendered.lower().startswith(\"no live search results found\"):\n                continue\n            if entity_lookup:\n                rendered = _filter_entity_evidence(request_text, rendered)\n                if not rendered:\n                    continue\n            evidence_parts.append(f\"SEARCH QUERY: {query}\\n{rendered}\")\n'''
if old not in text:
    raise SystemExit('run_batch filter anchor missing')
text = text.replace(old, new, 1)
qpath.write_text(text, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Search ranking must never fail open and return sources it explicitly
#    rejected. If all primary results are rejected, try independent fallback
#    engines and rerank; if those are also irrelevant, return no evidence.
# ---------------------------------------------------------------------------
tools_path = Path('backend/src/adk/tools.py')
tools = tools_path.read_text(encoding='utf-8')

start_marker = '''    # SearXNG is a final fallback only.  The primary providers already ran in\n'''
end_marker = '''    formatted = []\n'''
start = tools.find(start_marker)
end = tools.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('web_search ranking section bounds missing')

replacement = '''    def _dedupe_search_results(items: List[Dict[str, str]]) -> List[Dict[str, str]]:\n        # Keep a larger discovery pool than the final answer limit so fallback\n        # providers are not pushed out by an early batch of irrelevant results.\n        discovery_limit = max(result_limit * 4, 24)\n        seen_urls: set[str] = set()\n        seen_titles: set[str] = set()\n        unique: List[Dict[str, str]] = []\n        for item in items:\n            title = str(item.get(\"title\", \"\")).strip()\n            url = str(item.get(\"url\", \"\")).strip()\n            snippet = str(item.get(\"snippet\", \"\")).strip()\n            if not title or not snippet:\n                continue\n            norm_url = url.split(\"#\")[0].rstrip(\"/\") if url else \"\"\n            norm_title = title.casefold()\n            if norm_url and norm_url in seen_urls:\n                continue\n            if norm_title in seen_titles:\n                continue\n            if norm_url:\n                seen_urls.add(norm_url)\n            seen_titles.add(norm_title)\n            unique.append(item)\n            if len(unique) >= discovery_limit:\n                break\n        return unique\n\n    def _rank_search_results(items: List[Dict[str, str]]) -> tuple[List[Dict[str, str]], bool]:\n        if not items:\n            return [], True\n        try:\n            from src.adk.search_ranker import SearchResultRanker\n\n            ranking = SearchResultRanker.rank_sources(\n                clean_query, items, max_selected=result_limit\n            )\n            by_url = {\n                str(item.get(\"url\", \"\")).split(\"#\")[0].rstrip(\"/\"): item\n                for item in items\n                if str(item.get(\"url\", \"\")).strip()\n            }\n            selected_urls = [\n                str(source.get(\"url\", \"\")).split(\"#\")[0].rstrip(\"/\")\n                for source in ranking.selected_sources\n                if str(source.get(\"url\", \"\")).strip()\n            ]\n            selected = [by_url[url] for url in selected_urls if url in by_url]\n            # A successful ranker decision that rejects everything is meaningful:\n            # never return the rejected inputs merely because selected == [].\n            return selected, True\n        except Exception as exc:\n            logger.warning(\"Search ranking failed for '%s': %s\", clean_query, exc)\n            return items[:result_limit], False\n\n    unique_results = _dedupe_search_results(raw_items)\n    ranked_results, ranking_succeeded = _rank_search_results(unique_results)\n\n    if ranking_succeeded and not ranked_results:\n        # Primary engines can occasionally return a full page of unrelated\n        # results.  Retry independent fallback paths only after relevance\n        # ranking proves the first pool unusable.\n        fallback_sets = await asyncio.gather(\n            _searxng_search_items(clean_query, max_items=min(result_limit, 8)),\n            _ddg_html_search(clean_query, max_items=min(result_limit, 8)),\n            return_exceptions=True,\n        )\n        fallback_items: List[Dict[str, str]] = []\n        for fallback in fallback_sets:\n            if isinstance(fallback, list):\n                fallback_items.extend(fallback)\n\n        # Wikipedia is useful for stable named entities, but its older helper\n        # returns formatted text rather than structured rows. Parse its URL/title\n        # blocks into the same ranking shape when available.\n        try:\n            wiki_text = await _wikipedia_search(clean_query)\n        except Exception:\n            wiki_text = None\n        if wiki_text:\n            current_title = \"Wikipedia Reference\"\n            current_url = \"\"\n            current_snippet: list[str] = []\n\n            def _flush_wiki() -> None:\n                nonlocal current_title, current_url, current_snippet\n                snippet = \" \\".join(current_snippet).strip()\n                if current_url and snippet:\n                    fallback_items.append({\n                        \"title\": current_title,\n                        \"url\": current_url,\n                        \"snippet\": snippet,\n                        \"source\": \"Wikipedia\",\n                    })\n                current_title = \"Wikipedia Reference\"\n                current_url = \"\"\n                current_snippet = []\n\n            for raw_line in str(wiki_text).splitlines():\n                line = raw_line.strip()\n                if line.startswith(\"### \"):\n                    _flush_wiki()\n                    current_title = re.sub(r\"^###\\s+(?:\\[[^]]+\\]\\s*)?\", \"\", line).strip() or current_title\n                elif line.startswith(\"URL: \"):\n                    current_url = line[5:].strip()\n                elif line:\n                    current_snippet.append(line)\n            _flush_wiki()\n\n        if fallback_items:\n            unique_results = _dedupe_search_results(raw_items + fallback_items)\n            ranked_results, ranking_succeeded = _rank_search_results(unique_results)\n\n    if ranking_succeeded:\n        unique_results = ranked_results\n    else:\n        unique_results = ranked_results[:result_limit]\n\n    if not unique_results:\n        output = f\"No live search results found for '{clean_query}'.\"\n        if len(_web_search_cache) >= _WEB_SEARCH_CACHE_MAX_ENTRIES:\n            oldest_key = min(_web_search_cache, key=lambda key: _web_search_cache[key][0])\n            _web_search_cache.pop(oldest_key, None)\n        _web_search_cache[cache_key] = (now, output)\n        logger.info(\"No relevant ranked search results for: '%s'\", clean_query)\n        return output\n\n'''
tools = tools[:start] + replacement + tools[end:]
tools_path.write_text(tools, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Permanent regression coverage.
# ---------------------------------------------------------------------------
tpath = Path('backend/tests/test_entity_grounding_resolution.py')
tests = tpath.read_text(encoding='utf-8')
addition = r'''

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
'''
if 'test_mixed_acronym_results_keep_only_pcce_goa_sources' not in tests:
    tests += addition
elif 'test_web_search_does_not_return_ranker_rejected_garbage' not in tests:
    tests += addition.split('async def test_grounded_rescue_filters_unrelated_sources_from_synthesis', 1)[1]
    raise SystemExit('unexpected partial test state; rerun from clean branch')
tpath.write_text(tests, encoding='utf-8')
