from pathlib import Path

path = Path('backend/src/api/routes/chat.py')
text = path.read_text(encoding='utf-8')

anchor = '''async def _recover_stream_response(
    message: str,
    user_id: str,
    conversation_id: str,
    workspace_id: str | None,
    request_id: str,
) -> dict | None:
'''
if anchor not in text:
    raise RuntimeError('recovery helper anchor missing')

insert_before = '''class AttachmentInfo(BaseModel):
'''
helper = r'''_LAST_RESORT_GROUNDING_RE = re.compile(
    r"(?ix)\b(?:latest|current|currently|today|news|weather|price|rate|"
    r"where\s+(?:is|are)|where's|location|address|headquarters|campus|"
    r"search\s+(?:the\s+)?(?:web|internet|google)|look\s+up|find\s+online|"
    r"verify\s+online|recent|newest|most\s+recent)\b"
)


async def _last_resort_chat_recovery(
    message: str,
    request_id: str,
    require_grounding: bool,
) -> dict | None:
    """Recover after both streaming ADK and non-streaming ADK have failed.

    ADK remains the primary and secondary runtime. This final stage only keeps a
    transient ADK/provider failure from becoming an empty generic retry. Fresh or
    external questions are never answered from model memory here: they first run
    the existing web-search tool and synthesize only from returned evidence.
    """
    from src.services.llm import llm_service

    try:
        if require_grounding:
            from src.adk.tools import web_search
            from src.adk.runner import _citations_from_search_text

            evidence = await web_search(message, for_research=True, max_items=8)
            citations = _citations_from_search_text(evidence)
            if not citations:
                return None
            prompt = (
                "USER REQUEST:\n" + message[:8000] +
                "\n\nLIVE WEB SEARCH EVIDENCE:\n" + evidence[:18000]
            )
            output = await llm_service.generate(
                prompt=prompt,
                system_instruction=(
                    "Answer the user using only the supplied live web evidence for factual claims. "
                    "Do not guess or use model memory to fill gaps. Preserve entity/location qualifiers, "
                    "prefer primary sources, and keep useful source links/citations."
                ),
                temperature=0.15,
                max_output_tokens=4096,
            )
            answer = str(output or '').strip()
            if not answer:
                return None
            return {"output": answer, "citations": citations, "recovery_stage": "grounded_provider"}

        output = await llm_service.generate(
            prompt=message[:24000],
            system_instruction=(
                "You are the final user-facing assistant. Answer the latest request directly and naturally. "
                "Do not mention internal agents or hidden routing. Do not invent current facts or claim web access."
            ),
            temperature=0.35,
            max_output_tokens=4096,
        )
        answer = str(output or '').strip()
        if not answer:
            return None
        return {"output": answer, "citations": [], "recovery_stage": "provider"}
    except Exception as fallback_error:
        logger.warning(
            "chat_last_resort_recovery_failed",
            extra={"request_id": request_id, "error": str(fallback_error)[:500]},
        )
        return None


'''
if insert_before not in text:
    raise RuntimeError('AttachmentInfo anchor missing')
text = text.replace(insert_before, helper + insert_before, 1)

old = '''            # If answer text already escaped before the exception, never replay
            # the model and risk mixing two generations. Persist the partial and
            # let the client preserve a non-empty completed payload.
            if accumulated_output:
'''
new = '''            # If both ADK streaming and non-streaming ADK recovery failed before
            # any text reached the user, use one final independent provider path.
            # External/current queries remain evidence-grounded and never fall
            # back to unsupported model memory.
            if not accumulated_output and routed_agent_id != "image":
                require_grounding = bool(
                    effective_agent_id == "research"
                    or _LAST_RESORT_GROUNDING_RE.search(body.message)
                )
                fallback = await _last_resort_chat_recovery(
                    body.message,
                    request_id,
                    require_grounding=require_grounding,
                )
                if fallback:
                    recovered_output = str(fallback.get("output", "") or "").strip()
                    recovered_citations = list(fallback.get("citations", []) or [])
                    accumulated_output = recovered_output
                    yield f"event: agent\\ndata: {json.dumps({'agent_id': 'last_resort_recovery'})}\\n\\n"
                    async for word in _word_chunks(recovered_output):
                        yield f"event: chunk\\ndata: {json.dumps({'text': word}, ensure_ascii=False)}\\n\\n"
                    attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                    await _save_messages(
                        conv_id=conv_id,
                        user_id=user_id,
                        user_message=body.message,
                        agent_message=recovered_output,
                        agent_id=effective_agent_id or body.agent_id,
                        is_new=is_new,
                        attachments=attachments_data,
                        workspace_id=body.workspace_id,
                        citations=recovered_citations,
                        request_id=request_id,
                    )
                    yield f"event: complete\\ndata: {json.dumps({'output': recovered_output, 'conversation_id': conv_id, 'citations': recovered_citations, 'recovered': True, 'recovery_stage': fallback.get('recovery_stage')}, ensure_ascii=False)}\\n\\n"
                    return

            # If answer text already escaped before the exception, never replay
            # the model and risk mixing two generations. Persist the partial and
            # let the client preserve a non-empty completed payload.
            if accumulated_output:
'''
if old not in text:
    raise RuntimeError('stream exception fallback anchor missing')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')

# Add focused regression tests.
test_path = Path('backend/tests/test_chat_last_resort_recovery.py')
test_path.write_text(r'''import pytest

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
''', encoding='utf-8')
print('chat last-resort recovery patch applied')
