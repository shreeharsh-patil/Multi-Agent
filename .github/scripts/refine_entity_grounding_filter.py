from pathlib import Path

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

# Extend permanent regression tests.
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
'''
if 'test_mixed_acronym_results_keep_only_pcce_goa_sources' not in tests:
    tests += addition
tpath.write_text(tests, encoding='utf-8')
