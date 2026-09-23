from pathlib import Path
import re


def replace_exact(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"missing expected block for {label}: {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


def replace_regex(path: str, pattern: str, replacement: str, label: str, flags: int = re.S) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"expected one match for {label}, got {count}: {path}")
    p.write_text(updated, encoding="utf-8")
    print(f"applied: {label}")


# ---------------------------------------------------------------------------
# Router: explicit image intents must never degrade into a prose answer, and
# external place/address questions must use the research/grounding runtime.
# ---------------------------------------------------------------------------
router_path = "backend/src/orchestrator/router.py"
router = Path(router_path).read_text(encoding="utf-8")
router = router.replace(
    r'''            (r"(?i)\b(generate|create|draw|make|design|render|paint|show|produce)\b.*\b(image|picture|photo|photograph|illustration|drawing|artwork|poster|logo|icon|graphic|banner|vector|avatar)\b", "image"),
            (r"(?i)\b(image|picture|photo|drawing|illustration)\b\s+(of|for|with|showing|featuring)\b", "image"),
            (r"(?i)\b(logo|icon|avatar)\b\s+(for|of|with|showing|featuring)\b", "image"),''',
    r'''            (r"(?i)\b(generate|create|draw|make|design|render|paint|show|produce|visualize|visualise|illustrate)\b.*\b(images?|pictures?|photos?|photographs?|illustrations?|drawings?|artworks?|posters?|logos?|icons?|graphics?|banners?|vectors?|avatars?)\b", "image"),
            (r"(?i)\b(images?|pictures?|photos?|drawings?|illustrations?)\b\s+(of|for|with|showing|featuring)\b", "image"),
            (r"(?i)\b(logos?|icons?|avatars?)\b\s+(for|of|with|showing|featuring)\b", "image"),
            # External entity/location facts must be verified on the web instead
            # of being answered from model memory. This catches queries such as
            # "Where is PCCE Goa?" without hard-coding any institution.
            (r"(?i)\b(where\s+is|where's|where\s+are|location\s+of|address\s+of|located\s+(?:in|at)|headquarters\s+of|campus\s+of|how\s+to\s+reach|directions?\s+to)\b", "research"),'''
)
if router == Path(router_path).read_text(encoding="utf-8"):
    raise RuntimeError("router image/location replacement did not apply")
Path(router_path).write_text(router, encoding="utf-8")
print("applied: image and external-location routing")


# ---------------------------------------------------------------------------
# Chat API: make research routing an explicit ADK grounding requirement, keep
# external questions off the compact no-tool path, and make image replies only
# contain the generated image rather than prompt-engineering prose.
# ---------------------------------------------------------------------------
chat_path = "backend/src/api/routes/chat.py"
replace_regex(
    chat_path,
    r'''def _adk_routing_preamble\(agent_id: str \| None, team_agents: list\[str\]\) -> str:\n.*?(?=\n\ndef _chat_log)''',
    '''def _adk_routing_preamble(agent_id: str | None, team_agents: list[str]) -> str:\n    """Give BossAgent a truthful routing requirement selected by the API."""\n    if team_agents:\n        return (\n            "SYSTEM ROUTING HINT: The request may use these specialists: "\n            f"{', '.join(team_agents)}. BossAgent must independently select the "\n            "smallest suitable ADK workflow. For any external, current, named-entity, "\n            "location, or address claim, use web grounding before answering.\\n\\n"\n        )\n    if agent_id == "research":\n        return (\n            "SYSTEM ROUTING REQUIREMENT: This request requires external factual verification. "\n            "Use the ADK Internet Intelligence / Google Search workflow before answering. "\n            "Search the user's exact entity or acronym together with all location qualifiers; "\n            "do not silently substitute a similarly named organisation, person, campus, or place. "\n            "Prefer official organisation domains, government sources, and other primary sources. "\n            "Return the verified answer with the tool-provided citations/URLs. If live search is "\n            "unavailable or the identity remains ambiguous, say that verification failed instead "\n            "of guessing.\\n\\n"\n        )\n    if agent_id and agent_id not in {"auto", "image"}:\n        return (\n            f"SYSTEM ROUTING HINT: The routing layer selected `{agent_id}`. BossAgent still "\n            "controls the ADK workflow and may delegate as needed. For unverified named entities, "\n            "locations, acronyms, or current facts, use the ADK web-grounding workflow and cite "\n            "the returned sources; never guess.\\n\\n"\n        )\n    return ""\n''',
    "research grounding preamble",
)

# Broaden the full-runtime guard with freshness and external-place intents.
replace_exact(
    chat_path,
    '''        r"(?ix)(?:"\n        r"\\b(?:research|latest|current|calculate|calendar|drive|file|pdf|web|"\n        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"\n        r"code|debug|python|javascript|typescript|medical|health|finance)\\b|"\n        r"\\bsearch\\s+(?:the\\s+)?(?:web|internet|google)\\b|"\n        r"\\bweb\\s+search\\b|\\blook\\s+up\\b|\\bfind\\s+online\\b"\n        r")",\n''',
    '''        r"(?ix)(?:"\n        r"\\b(?:research|latest|newest|recent|current|currently|calculate|calendar|drive|file|pdf|web|"\n        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"\n        r"code|debug|python|javascript|typescript|medical|health|finance|address|location|headquarters|campus)\\b|"\n        r"\\bwhere\\s+(?:is|are)\\b|\\bwhere's\\b|\\bhow\\s+to\\s+reach\\b|\\bdirections?\\s+to\\b|"\n        r"\\bsearch\\s+(?:the\\s+)?(?:web|internet|google)\\b|"\n        r"\\bweb\\s+search\\b|\\blook\\s+up\\b|\\bfind\\s+online\\b"\n        r")",\n''',
    "full runtime external fact guard",
)

replace_regex(
    chat_path,
    r'''async def _generate_image_message\(\n.*?(?=\n\ndef _friendly_chat_error)''',
    '''async def _generate_image_message(\n    prompt: str,\n    user_id: str,\n    workspace_id: str | None,\n    drive_access_token: str | None = None,\n    drive_refresh_token: str | None = None,\n) -> str:\n    image = await generate_and_store_image(\n        prompt=prompt,\n        user_id=user_id,\n        workspace_id=workspace_id,\n        drive_access_token=drive_access_token,\n        drive_refresh_token=drive_refresh_token,\n    )\n    # The visual is the user-facing result. Keep enhanced/revised prompts in\n    # provider metadata rather than turning an image request into prose.\n    return f"![Generated image]({image.download_url})"\n''',
    "image-only response body",
)

# Non-streaming endpoint currently builds the prompt before smart routing. Move
# the preamble application until after effective_agent_id is known.
replace_exact(
    chat_path,
    '''        augmented_message = history_prefix + memory_context + attachment_context + body.message\n        augmented_message = _adk_routing_preamble(body.agent_id, body.team_agents) + augmented_message\n\n        routed_agent_id = AgentRouter().route_smart(body.message, body.agent_id)\n''',
    '''        augmented_message = history_prefix + memory_context + attachment_context + body.message\n\n        routed_agent_id = AgentRouter().route_smart(body.message, body.agent_id)\n''',
    "defer nonstream routing hint",
)
replace_exact(
    chat_path,
    '''        effective_agent_id = routed_agent_id if routed_agent_id != "auto" else planned_agent_id\n        use_dynamic_orchestration = bool(automatic_mode and len((automatic_plan or {}).get("steps", [])) > 1)\n\n        google_access_token = http_request.headers.get("X-Google-Access-Token", "")\n''',
    '''        effective_agent_id = routed_agent_id if routed_agent_id != "auto" else planned_agent_id\n        use_dynamic_orchestration = bool(automatic_mode and len((automatic_plan or {}).get("steps", [])) > 1)\n        augmented_message = _adk_routing_preamble(effective_agent_id or body.agent_id, body.team_agents) + augmented_message\n\n        google_access_token = http_request.headers.get("X-Google-Access-Token", "")\n''',
    "apply resolved nonstream route hint",
)
replace_exact(
    chat_path,
    '''            augmented_message = history_prefix + memory_context + attachment_context + body.message\n            augmented_message = _adk_routing_preamble(body.agent_id, body.team_agents) + augmented_message\n''',
    '''            augmented_message = history_prefix + memory_context + attachment_context + body.message\n            augmented_message = _adk_routing_preamble(effective_agent_id or body.agent_id, body.team_agents) + augmented_message\n''',
    "apply resolved streaming route hint",
)


# ---------------------------------------------------------------------------
# Quality boundary: fast chat must still be Google ADK, and any request that
# requires external verification is not allowed to leak an uncited guess.
# ---------------------------------------------------------------------------
quality_path = "backend/src/api/routes/_chat_quality.py"
replace_exact(
    quality_path,
    '''- Preserve verified citations supplied by research tools. Never invent a URL,\n  citation, source, measurement, price, date, or tool result.\n- If evidence is incomplete, state the specific uncertainty briefly and give\n  the most useful answer supported by the available context.\n''',
    '''- Preserve verified citations supplied by research tools. Never invent a URL,\n  citation, source, measurement, price, date, or tool result.\n- For current facts, external facts, named organisations/people, addresses,\n  campuses, locations, or unfamiliar acronyms, use the ADK web-search/Internet\n  Intelligence workflow before asserting the answer. Search the exact entity\n  string and preserve qualifiers such as city/state/country. Never silently\n  answer about a similarly named entity. Prefer official/primary sources.\n- If evidence is incomplete, state the specific uncertainty briefly and give\n  the most useful answer supported by the available context.\n''',
    "quality external entity policy",
)

replace_exact(
    quality_path,
    '''_RELATIVE_EVENT_RE = re.compile(\n    r"(?ix)\\b(?:today|tomorrow|yesterday|tonight|right\\s+now)\\b.{0,45}\\b(?:"\n    r"weather|news|match|game|score|market|price|event|result|release|flight"\n    r")\\b"\n)\n''',
    '''_RELATIVE_EVENT_RE = re.compile(\n    r"(?ix)\\b(?:today|tomorrow|yesterday|tonight|right\\s+now)\\b.{0,45}\\b(?:"\n    r"weather|news|match|game|score|market|price|event|result|release|flight"\n    r")\\b"\n)\n_EXTERNAL_FACT_RE = re.compile(\n    r"(?ix)\\b(?:where\\s+(?:is|are)|where's|location\\s+of|address\\s+of|"\n    r"located\\s+(?:in|at)|headquarters\\s+of|campus\\s+of|how\\s+to\\s+reach|"\n    r"directions?\\s+to)\\b"\n)\n_RECENCY_RE = re.compile(\n    r"(?ix)\\b(?:newest|most\\s+recent|recent(?:ly)?|currently|as\\s+of\\s+(?:today|now|20\\d{2}))\\b"\n)\n_URL_RE = re.compile(r"https?://", re.I)\n''',
    "external fact and recency detectors",
)

replace_exact(
    quality_path,
    '''def _requires_live_verification(message: str) -> bool:\n    """Fail closed only when the latest request genuinely needs fresh evidence."""\n    request_text = _latest_request_view(message)\n    return bool(\n        _LIVE_OR_EXTERNAL_RE.search(request_text)\n        or _CURRENT_SUBJECT_RE.search(request_text)\n        or _RELATIVE_EVENT_RE.search(request_text)\n    )\n\n\ndef _internal_session_id(conversation_id: str) -> str:\n''',
    '''def _requires_live_verification(message: str) -> bool:\n    """Return True when the latest request needs external or fresh evidence."""\n    request_text = _latest_request_view(message)\n    return bool(\n        _LIVE_OR_EXTERNAL_RE.search(request_text)\n        or _CURRENT_SUBJECT_RE.search(request_text)\n        or _RELATIVE_EVENT_RE.search(request_text)\n        or _EXTERNAL_FACT_RE.search(request_text)\n        or _RECENCY_RE.search(request_text)\n    )\n\n\ndef _has_external_evidence(output: str, citations: Any) -> bool:\n    """Require a tool-derived citation or URL before exposing external facts."""\n    return bool(citations or _URL_RE.search(str(output or "")))\n\n\ndef _internal_session_id(conversation_id: str) -> str:\n''',
    "external verification helper",
)

replace_exact(
    quality_path,
    '''    return (\n        "I couldn't reliably verify the live/current information needed for this request because "\n        "the research provider is temporarily unavailable. Please retry."\n    )\n''',
    '''    return (\n        "I couldn't reliably verify the external/current information needed for this request. "\n        "The ADK web-grounding workflow did not return verifiable source evidence, so I won't guess. "\n        "Please retry."\n    )\n''',
    "grounding failure wording",
)

# Remove the speed optimization that bypassed ADK for fast streaming. The
# normal wrapper below already passes fast_path=True into the original ADK
# runner, preserving low-latency ADK SSE without bypassing the framework.
replace_regex(
    quality_path,
    r'''        if fast_path and not _requires_live_verification\(message\):\n.*?            return\n\n        if not adk_runner\.use_adk\(\):''',
    '''        if not adk_runner.use_adk():''',
    "remove direct-model fast bypass",
)

# Fail closed for external facts if an ADK result somehow arrives without any
# source evidence. This protects both non-streaming and streaming consumers.
replace_exact(
    quality_path,
    '''            if _is_adk_failure(output):\n                if _requires_live_verification(message):\n                    result["output"] = _grounding_unavailable_message()\n                    return result\n                result["output"] = await _direct_answer(message)\n                result.setdefault("agent_traces", []).append(\n                    {"agent_id": "direct", "event_type": "DirectFallback", "has_content": True}\n                )\n                result["events_count"] = int(result.get("events_count", 0) or 0) + 1\n                return result\n\n            traces = result.get("agent_traces") or []\n''',
    '''            if _is_adk_failure(output):\n                if _requires_live_verification(message):\n                    result["output"] = _grounding_unavailable_message()\n                    return result\n                result["output"] = await _direct_answer(message)\n                result.setdefault("agent_traces", []).append(\n                    {"agent_id": "direct", "event_type": "DirectFallback", "has_content": True}\n                )\n                result["events_count"] = int(result.get("events_count", 0) or 0) + 1\n                return result\n\n            if _requires_live_verification(message) and not _has_external_evidence(\n                output, result.get("citations")\n            ):\n                result["output"] = _grounding_unavailable_message()\n                result.setdefault("agent_traces", []).append(\n                    {"agent_id": "grounding_guard", "event_type": "MissingExternalEvidence", "has_content": False}\n                )\n                result["events_count"] = int(result.get("events_count", 0) or 0) + 1\n                return result\n\n            traces = result.get("agent_traces") or []\n''',
    "nonstream evidence guard",
)

replace_exact(
    quality_path,
    '''        # The underlying runner will not retry after *any* partial text because\n        # historically that partial was already user-visible. We hide specialist\n        # partials, so one outer retry remains safe when no Boss text was shown.\n        for quality_attempt in range(2):\n''',
    '''        # The underlying runner will not retry after *any* partial text because\n        # historically that partial was already user-visible. We hide specialist\n        # partials, so one outer retry remains safe when no Boss text was shown.\n        verification_required = _requires_live_verification(message)\n        for quality_attempt in range(2):\n''',
    "stream verification mode",
)

replace_exact(
    quality_path,
    '''                            if text:\n                                exposed_answer_text = True\n                                for piece in _stream_pieces(text):\n                                    boss_chunks.append(piece)\n                                    yield {"event": "chunk", "data": {"text": piece}}\n''',
    '''                            if text:\n                                exposed_answer_text = True\n                                for piece in _stream_pieces(text):\n                                    boss_chunks.append(piece)\n                                    # Buffer externally verifiable answers until the\n                                    # final event proves that search evidence exists.\n                                    if not verification_required:\n                                        yield {"event": "chunk", "data": {"text": piece}}\n''',
    "buffer external boss chunks",
)

replace_exact(
    quality_path,
    '''                boss_output = "".join(boss_chunks).strip()\n                completed_output = str((pending_completed or {}).get("output", "") or "").strip()\n                completed_citations = list((pending_completed or {}).get("citations", []) or [])\n\n                if boss_output:\n''',
    '''                boss_output = "".join(boss_chunks).strip()\n                completed_output = str((pending_completed or {}).get("output", "") or "").strip()\n                completed_citations = list((pending_completed or {}).get("citations", []) or [])\n\n                if verification_required:\n                    evidence_output = boss_output or completed_output\n                    if evidence_output and not _has_external_evidence(evidence_output, completed_citations):\n                        output = _grounding_unavailable_message()\n                        for piece in _stream_pieces(output):\n                            yield {"event": "chunk", "data": {"text": piece}}\n                        yield {"event": "error", "data": {"error": output, "conversation_id": conversation_id}}\n                        yield {\n                            "event": "completed",\n                            "data": {"output": output, "conversation_id": conversation_id, "citations": []},\n                        }\n                        return\n\n                if boss_output:\n                    if verification_required:\n                        for piece in boss_chunks:\n                            yield {"event": "chunk", "data": {"text": piece}}\n''',
    "stream evidence guard",
)


# ---------------------------------------------------------------------------
# Regression tests.
# ---------------------------------------------------------------------------
quality_test = "backend/tests/test_chat_quality_runtime.py"
replace_exact(
    quality_test,
    '''    assert quality._requires_live_verification("What is the latest AI news today?") is True\n    assert quality._requires_live_verification("Explain binary search with an example") is False\n''',
    '''    assert quality._requires_live_verification("What is the latest AI news today?") is True\n    assert quality._requires_live_verification("Where is PCCE Goa?") is True\n    assert quality._requires_live_verification("Explain binary search with an example") is False\n    assert quality._has_external_evidence("Verified: https://pccegoa.edu.in/contact-us/", []) is True\n    assert quality._has_external_evidence("Unverified memory answer", []) is False\n''',
    "quality external evidence tests",
)

replace_regex(
    quality_test,
    r'''def test_fast_path_streams_directly_without_waiting_for_adk\(\):\n.*\Z''',
    '''def test_fast_path_stays_inside_adk_and_streams_progressively():\n    result = _run_isolated(\n        r\'\'\'\nimport asyncio\nimport json\n\nimport src.adk.runner as runner\nimport src.services.llm as llm_module\n\nrunner.use_adk = lambda: True\ncalled = {"adk": 0, "direct": 0}\n\nasync def fake_adk_stream(message, user_id="default", conversation_id="default", workspace_id=None, fast_path=False, _failover_attempt=0):\n    called["adk"] += 1\n    yield {"event": "start", "data": {"conversation_id": conversation_id}}\n    yield {"event": "agent", "data": {"agent_id": "boss_agent"}}\n    yield {"event": "chunk", "data": {"text": "Fast "}}\n    yield {"event": "chunk", "data": {"text": "ADK "}}\n    yield {"event": "chunk", "data": {"text": "answer"}}\n    yield {"event": "completed", "data": {"output": "Fast ADK answer", "conversation_id": conversation_id, "citations": []}}\n\nasync def fake_direct_stream(*args, **kwargs):\n    called["direct"] += 1\n    raise RuntimeError("direct model path must not be used for healthy fast ADK")\n    yield "never"\n\nrunner.process_message_stream = fake_adk_stream\nllm_module.llm_service.generate_stream = fake_direct_stream\n\nimport src.api.routes\n\nasync def main():\n    events = []\n    async for event in runner.process_fast_message_stream(\n        "Explain this simply",\n        user_id="u1",\n        conversation_id="conversation-fast",\n    ):\n        events.append(event)\n    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]\n    completed = [e for e in events if e["event"] == "completed"][-1]\n    print(json.dumps({\n        "chunks": chunks,\n        "completed": completed["data"],\n        "adk_calls": called["adk"],\n        "direct_calls": called["direct"],\n    }))\n\nasyncio.run(main())\n\'\'\'\n    )\n\n    assert result["chunks"] == ["Fast ", "ADK ", "answer"]\n    assert result["completed"]["output"] == "Fast ADK answer"\n    assert result["adk_calls"] == 1\n    assert result["direct_calls"] == 0\n''',
    "ADK-first fast path test",
)

reliability_test = Path("backend/tests/test_adk_reliability_routing.py")
reliability_test.write_text('''from types import SimpleNamespace\n\nimport pytest\n\nfrom src.api.routes import chat as chat_module\nfrom src.api.routes.chat import ChatRequest, _adk_routing_preamble, _generate_image_message, _use_compact_adk_boss\nfrom src.orchestrator.dynamic import plan_dynamic\nfrom src.orchestrator.router import AgentRouter\n\n\ndef _is_fast(message: str) -> bool:\n    body = ChatRequest(message=message)\n    plan = plan_dynamic(message, has_attachments=False, has_workspace=False)\n    return _use_compact_adk_boss(body, plan, automatic_mode=True)\n\n\ndef test_pcce_location_question_requires_research_grounding():\n    assert AgentRouter().route_smart("Where is PCCE Goa?") == "research"\n    assert _is_fast("Where is PCCE Goa?") is False\n    hint = _adk_routing_preamble("research", [])\n    assert "Google Search" in hint\n    assert "exact entity or acronym" in hint\n    assert "official organisation domains" in hint\n\n\ndef test_plural_and_natural_image_requests_route_to_image_generation():\n    router = AgentRouter()\n    assert router.route_smart("Generate images of a futuristic Goa city") == "image"\n    assert router.route_smart("Create three pictures of a drone at sunset") == "image"\n    assert router.route_smart("Visualize an illustration of a robot classroom") == "image"\n\n\n@pytest.mark.asyncio\nasync def test_image_request_returns_visual_without_prompt_paragraph(monkeypatch):\n    async def fake_generate_and_store_image(**kwargs):\n        return SimpleNamespace(\n            download_url="/api/documents/generated-1/file",\n            revised_prompt="long internal enhanced prompt that should stay hidden",\n        )\n\n    monkeypatch.setattr(chat_module, "generate_and_store_image", fake_generate_and_store_image)\n    output = await _generate_image_message("Generate an image of a drone", "u1", None)\n    assert output == "![Generated image](/api/documents/generated-1/file)"\n    assert "Prompt used" not in output\n    assert "enhanced prompt" not in output\n''', encoding="utf-8")
print("created: ADK reliability routing tests")

print("ADK grounding and image routing repair complete")
