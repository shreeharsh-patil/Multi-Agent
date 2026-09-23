from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"missing expected block for {label}: {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


replace_once(
    "backend/src/api/routes/chat.py",
    '''def _use_compact_adk_boss(body: "ChatRequest", dynamic_plan: dict | None, automatic_mode: bool) -> bool:
    """Use the low-latency ADK Boss when no tools or delegation are needed."""
    simple_greeting = bool(re.fullmatch(
        r"(?i)\s*(?:hi|hello|hey|hiya|howdy|good\s+(?:morning|afternoon|evening)|namaste)[!?.\s]*",
        body.message,
    ))
    direct_boss_mode = body.agent_id in (None, "auto", "boss_agent") and not body.team_agents
    return bool(
        direct_boss_mode
        and not body.attachments
        and not body.workspace_id
        and (
            simple_greeting
            or (
                automatic_mode
                and not body.conversation_id
                and len((dynamic_plan or {}).get("steps", [])) <= 1
                and not re.search(r"(?i)\b(research|latest|current|search|calculate|calendar|drive|file|pdf|web)\b", body.message)
            )
        )
    )
''',
    '''def _use_compact_adk_boss(body: "ChatRequest", dynamic_plan: dict | None, automatic_mode: bool) -> bool:
    """Use the low-latency direct stream for ordinary conversational turns."""
    simple_greeting = bool(re.fullmatch(
        r"(?i)\s*(?:hi|hello|hey|hiya|howdy|good\s+(?:morning|afternoon|evening)|namaste)[!?.\s]*",
        body.message,
    ))
    direct_boss_mode = body.agent_id in (None, "auto", "boss_agent") and not body.team_agents
    steps = (dynamic_plan or {}).get("steps", [])
    planned_agent = steps[0].get("agent_id") if steps else None
    general_turn = planned_agent in (None, "knowledge")
    needs_full_runtime = bool(re.search(
        r"(?i)\b(?:research|latest|current|search|calculate|calendar|drive|file|pdf|web|"
        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"
        r"code|debug|python|javascript|typescript|medical|health|finance)\b",
        body.message,
    ))
    return bool(
        direct_boss_mode
        and not body.attachments
        and not body.workspace_id
        and (
            simple_greeting
            or (
                automatic_mode
                and len(steps) <= 1
                and general_turn
                and not needs_full_runtime
            )
        )
    )
''',
    "broaden safe fast-stream routing",
)

replace_once(
    "backend/src/api/routes/chat.py",
    '''            if fast_path:
                memory_context, attachment_context, history_snippet = "", "", ""
            else:
''',
    '''            if fast_path:
                memory_context, attachment_context = "", ""
                history_snippet = ""
                if body.conversation_id:
                    try:
                        async with asyncio.timeout(min(settings.chat_context_timeout_seconds, 1.5)):
                            history_snippet = await _build_full_conversation_history(
                                body.conversation_id, max_messages=12, max_chars=12_000
                            )
                    except TimeoutError:
                        history_snippet = ""
            else:
''',
    "retain bounded history on fast follow-ups",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''async def _direct_answer(message: str) -> str:
''',
    '''def _stream_pieces(text: str) -> list[str]:
    """Split text into display-friendly word/token pieces without changing it."""
    return re.findall(r"\S+\s*|\s+", str(text or ""))


async def _direct_answer(message: str) -> str:
''',
    "add stream piece helper",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''async def _synthesize_draft(message: str, draft: str) -> str:
    """Convert an internal specialist final into one clean user-facing answer."""
    from src.services.llm import llm_service

    prompt = (
        "USER REQUEST AND CONTEXT:\n"
        f"{_compact_prompt(message, 18_000)}\n\n"
        "INTERNAL DRAFT TO SYNTHESIZE:\n"
        f"{_compact_prompt(draft, 14_000)}"
    )
    try:
        result = await llm_service.generate(
            prompt=prompt,
            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=4096,
        )
        return result.strip() or draft.strip()
    except Exception:
        # A valid specialist answer is better than replacing useful work with a
        # second-provider failure. The stream boundary still hides raw partials.
        return draft.strip()


def _grounding_unavailable_message() -> str:
''',
    '''async def _synthesize_draft(message: str, draft: str) -> str:
    """Convert an internal specialist final into one clean user-facing answer."""
    from src.services.llm import llm_service

    prompt = (
        "USER REQUEST AND CONTEXT:\n"
        f"{_compact_prompt(message, 18_000)}\n\n"
        "INTERNAL DRAFT TO SYNTHESIZE:\n"
        f"{_compact_prompt(draft, 14_000)}"
    )
    try:
        result = await llm_service.generate(
            prompt=prompt,
            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=4096,
        )
        return result.strip() or draft.strip()
    except Exception:
        # A valid specialist answer is better than replacing useful work with a
        # second-provider failure. The stream boundary still hides raw partials.
        return draft.strip()


async def _synthesize_draft_stream(message: str, draft: str) -> AsyncIterator[str]:
    """Stream final synthesis so complex answers do not appear all at once."""
    from src.services.llm import llm_service

    prompt = (
        "USER REQUEST AND CONTEXT:\n"
        f"{_compact_prompt(message, 18_000)}\n\n"
        "INTERNAL DRAFT TO SYNTHESIZE:\n"
        f"{_compact_prompt(draft, 14_000)}"
    )
    emitted = False
    try:
        async for chunk in llm_service.generate_stream(
            prompt=prompt,
            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=4096,
        ):
            if chunk:
                emitted = True
                yield str(chunk)
        if emitted:
            return
    except Exception:
        if emitted:
            return

    fallback = await _synthesize_draft(message, draft)
    if fallback:
        yield fallback


def _grounding_unavailable_message() -> str:
''',
    "add streaming final synthesis",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''    ):
        if not adk_runner.use_adk():
            yield {"event": "start", "data": {"conversation_id": conversation_id}}
''',
    '''    ):
        if fast_path and not _requires_live_verification(message):
            yield {"event": "start", "data": {"conversation_id": conversation_id}}
            yield {"event": "agent", "data": {"agent_id": "direct"}}
            direct_chunks: list[str] = []
            try:
                async for chunk in _direct_stream(message):
                    for piece in _stream_pieces(chunk):
                        direct_chunks.append(piece)
                        yield {"event": "chunk", "data": {"text": piece}}
                output = "".join(direct_chunks).strip()
                if not output:
                    raise RuntimeError("Direct fast stream returned an empty response")
                yield {
                    "event": "completed",
                    "data": {"output": output, "conversation_id": conversation_id, "citations": []},
                }
            except Exception:
                output = "".join(direct_chunks).strip()
                if not output:
                    output = "Unable to generate a response right now. Please retry."
                    for piece in _stream_pieces(output):
                        yield {"event": "chunk", "data": {"text": piece}}
                yield {
                    "event": "error",
                    "data": {"error": "The response stream was interrupted. Please retry.", "conversation_id": conversation_id},
                }
                yield {
                    "event": "completed",
                    "data": {"output": output, "conversation_id": conversation_id, "citations": []},
                }
            return

        if not adk_runner.use_adk():
            yield {"event": "start", "data": {"conversation_id": conversation_id}}
''',
    "add true direct fast stream",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                async for chunk in _direct_stream(message):
                    chunks.append(chunk)
                    yield {"event": "chunk", "data": {"text": chunk}}
''',
    '''                async for chunk in _direct_stream(message):
                    for piece in _stream_pieces(chunk):
                        chunks.append(piece)
                        yield {"event": "chunk", "data": {"text": piece}}
''',
    "rechunk non-ADK direct stream",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                            if text:
                                boss_chunks.append(text)
                                exposed_answer_text = True
                                yield {"event": "chunk", "data": {"text": text}}
''',
    '''                            if text:
                                exposed_answer_text = True
                                for piece in _stream_pieces(text):
                                    boss_chunks.append(piece)
                                    yield {"event": "chunk", "data": {"text": piece}}
''',
    "rechunk boss partials",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                if completed_output and not _is_adk_failure(completed_output):
                    if _is_user_facing(current_agent):
                        final_output = completed_output
                    else:
                        final_output = await _synthesize_draft(message, completed_output)
                        yield {"event": "agent", "data": {"agent_id": "final_synthesizer"}}
                    yield {"event": "chunk", "data": {"text": final_output}}
                    yield {
                        "event": "completed",
                        "data": {
                            "output": final_output,
                            "conversation_id": conversation_id,
                            "citations": completed_citations,
                        },
                    }
                    return
''',
    '''                if completed_output and not _is_adk_failure(completed_output):
                    final_chunks: list[str] = []
                    if _is_user_facing(current_agent):
                        for piece in _stream_pieces(completed_output):
                            final_chunks.append(piece)
                            yield {"event": "chunk", "data": {"text": piece}}
                    else:
                        yield {"event": "agent", "data": {"agent_id": "final_synthesizer"}}
                        async for chunk in _synthesize_draft_stream(message, completed_output):
                            for piece in _stream_pieces(chunk):
                                final_chunks.append(piece)
                                yield {"event": "chunk", "data": {"text": piece}}
                    final_output = "".join(final_chunks).strip() or completed_output
                    yield {
                        "event": "completed",
                        "data": {
                            "output": final_output,
                            "conversation_id": conversation_id,
                            "citations": completed_citations,
                        },
                    }
                    return
''',
    "stream aggregated and synthesized finals",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                fallback_failed = False
                if _requires_live_verification(message):
                    output = _grounding_unavailable_message()
                    fallback_failed = True
                else:
                    try:
                        output = await _direct_answer(message)
                    except Exception:
                        fallback_failed = True
                        output = str((pending_error or {}).get("error", "") or "").strip()
                        if not output:
                            output = "Unable to generate a response right now. Please retry."

                if not exposed_answer_text:
                    yield {"event": "chunk", "data": {"text": output}}
                if fallback_failed:
''',
    '''                fallback_failed = False
                fallback_chunks: list[str] = []
                if _requires_live_verification(message):
                    output = _grounding_unavailable_message()
                    fallback_failed = True
                    if not exposed_answer_text:
                        for piece in _stream_pieces(output):
                            fallback_chunks.append(piece)
                            yield {"event": "chunk", "data": {"text": piece}}
                else:
                    try:
                        async for chunk in _direct_stream(message):
                            for piece in _stream_pieces(chunk):
                                fallback_chunks.append(piece)
                                if not exposed_answer_text:
                                    yield {"event": "chunk", "data": {"text": piece}}
                        output = "".join(fallback_chunks).strip()
                        if not output:
                            raise RuntimeError("Direct fallback returned an empty response")
                    except Exception:
                        fallback_failed = True
                        output = "".join(fallback_chunks).strip()
                        if not output:
                            output = str((pending_error or {}).get("error", "") or "").strip()
                        if not output:
                            output = "Unable to generate a response right now. Please retry."
                        if not fallback_chunks and not exposed_answer_text:
                            for piece in _stream_pieces(output):
                                yield {"event": "chunk", "data": {"text": piece}}

                if fallback_failed:
''',
    "stream fallback response progressively",
)

replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''    assert result["chunks"] == ["Clean final answer"]
''',
    '''    assert result["chunks"] == ["Clean ", "final ", "answer"]
''',
    "update boss chunk expectation",
)

replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''async def fake_generate(*args, **kwargs):
    return "Polished user-facing answer"

llm_module.llm_service.generate = fake_generate
''',
    '''async def fake_generate(*args, **kwargs):
    return "Polished user-facing answer"

async def fake_generate_stream(*args, **kwargs):
    yield "Polished "
    yield "user-facing "
    yield "answer"

llm_module.llm_service.generate = fake_generate
llm_module.llm_service.generate_stream = fake_generate_stream
''',
    "mock streaming synthesizer",
)

replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''    assert result["chunks"] == ["Polished user-facing answer"]
''',
    '''    assert result["chunks"] == ["Polished ", "user-facing ", "answer"]
''',
    "update synthesis chunk expectation",
)


test_path = Path("backend/tests/test_chat_quality_runtime.py")
test_text = test_path.read_text(encoding="utf-8")
marker = "def test_fast_path_streams_directly_without_waiting_for_adk():"
if marker not in test_text:
    test_text += """


def test_fast_path_streams_directly_without_waiting_for_adk():
    result = _run_isolated(
        r'''\nimport asyncio\nimport json\n\nimport src.adk.runner as runner\nimport src.services.llm as llm_module\n\nrunner.use_adk = lambda: True\ncalled = {\"adk\": 0}\n\nasync def fake_adk_stream(*args, **kwargs):\n    called[\"adk\"] += 1\n    yield {\"event\": \"completed\", \"data\": {\"output\": \"slow adk\", \"conversation_id\": \"internal\", \"citations\": []}}\n\nasync def fake_direct_stream(*args, **kwargs):\n    yield \"Fast \"\n    yield \"streaming \"\n    yield \"answer\"\n\nrunner.process_message_stream = fake_adk_stream\nllm_module.llm_service.generate_stream = fake_direct_stream\n\nimport src.api.routes\n\nasync def main():\n    events = []\n    async for event in runner.process_fast_message_stream(\n        \"Explain this simply\",\n        user_id=\"u1\",\n        conversation_id=\"conversation-fast\",\n    ):\n        events.append(event)\n    chunks = [e[\"data\"][\"text\"] for e in events if e[\"event\"] == \"chunk\"]\n    completed = [e for e in events if e[\"event\"] == \"completed\"][-1]\n    print(json.dumps({\"chunks\": chunks, \"completed\": completed[\"data\"], \"adk_calls\": called[\"adk\"]}))\n\nasyncio.run(main())\n'''
    )

    assert result[\"chunks\"] == [\"Fast \", \"streaming \", \"answer\"]
    assert result[\"completed\"][\"output\"] == \"Fast streaming answer\"
    assert result[\"adk_calls\"] == 0
"""
    test_path.write_text(test_text, encoding="utf-8")
    print("applied: add direct fast-path regression test")
else:
    print("already applied: add direct fast-path regression test")

print("streaming repair complete")
