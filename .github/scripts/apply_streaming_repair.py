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


# 1) Route ordinary knowledge/chat turns through the low-latency streaming path,
# including follow-ups. Tool/research/specialist intents remain on full ADK.
replace_once(
    "backend/src/api/routes/chat.py",
    '''def _use_compact_adk_boss(body: "ChatRequest", dynamic_plan: dict | None, automatic_mode: bool) -> bool:\n    """Use the low-latency ADK Boss when no tools or delegation are needed."""\n    simple_greeting = bool(re.fullmatch(\n        r"(?i)\\s*(?:hi|hello|hey|hiya|howdy|good\\s+(?:morning|afternoon|evening)|namaste)[!?.\\s]*",\n        body.message,\n    ))\n    direct_boss_mode = body.agent_id in (None, "auto", "boss_agent") and not body.team_agents\n    return bool(\n        direct_boss_mode\n        and not body.attachments\n        and not body.workspace_id\n        and (\n            simple_greeting\n            or (\n                automatic_mode\n                and not body.conversation_id\n                and len((dynamic_plan or {}).get("steps", [])) <= 1\n                and not re.search(r"(?i)\\b(research|latest|current|search|calculate|calendar|drive|file|pdf|web)\\b", body.message)\n            )\n        )\n    )\n''',
    '''def _use_compact_adk_boss(body: "ChatRequest", dynamic_plan: dict | None, automatic_mode: bool) -> bool:\n    """Use the low-latency direct stream for ordinary conversational turns."""\n    simple_greeting = bool(re.fullmatch(\n        r"(?i)\\s*(?:hi|hello|hey|hiya|howdy|good\\s+(?:morning|afternoon|evening)|namaste)[!?.\\s]*",\n        body.message,\n    ))\n    direct_boss_mode = body.agent_id in (None, "auto", "boss_agent") and not body.team_agents\n    steps = (dynamic_plan or {}).get("steps", [])\n    planned_agent = steps[0].get("agent_id") if steps else None\n    general_turn = planned_agent in (None, "knowledge")\n    needs_full_runtime = bool(re.search(\n        r"(?i)\\b(?:research|latest|current|search|calculate|calendar|drive|file|pdf|web|"\n        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"\n        r"code|debug|python|javascript|typescript|medical|health|finance)\\b",\n        body.message,\n    ))\n    return bool(\n        direct_boss_mode\n        and not body.attachments\n        and not body.workspace_id\n        and (\n            simple_greeting\n            or (\n                automatic_mode\n                and len(steps) <= 1\n                and general_turn\n                and not needs_full_runtime\n            )\n        )\n    )\n''',
    "broaden safe fast-stream routing",
)

# Preserve recent conversation context for fast follow-up turns without paying
# the full memory/attachment context cost.
replace_once(
    "backend/src/api/routes/chat.py",
    '''            if fast_path:\n                memory_context, attachment_context, history_snippet = "", "", ""\n            else:\n''',
    '''            if fast_path:\n                memory_context, attachment_context = "", ""\n                history_snippet = ""\n                if body.conversation_id:\n                    try:\n                        async with asyncio.timeout(min(settings.chat_context_timeout_seconds, 1.5)):\n                            history_snippet = await _build_full_conversation_history(\n                                body.conversation_id, max_messages=12, max_chars=12_000\n                            )\n                    except TimeoutError:\n                        history_snippet = ""\n            else:\n''',
    "retain bounded history on fast follow-ups",
)

# 2) Add exact-preserving word/token pieces and streaming synthesis helper.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''async def _direct_answer(message: str) -> str:\n''',
    '''def _stream_pieces(text: str) -> list[str]:\n    """Split text into display-friendly word/token pieces without changing it."""\n    return re.findall(r"\\S+\\s*|\\s+", str(text or ""))\n\n\nasync def _direct_answer(message: str) -> str:\n''',
    "add stream piece helper",
)

replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''async def _synthesize_draft(message: str, draft: str) -> str:\n    """Convert an internal specialist final into one clean user-facing answer."""\n    from src.services.llm import llm_service\n\n    prompt = (\n        "USER REQUEST AND CONTEXT:\\n"\n        f"{_compact_prompt(message, 18_000)}\\n\\n"\n        "INTERNAL DRAFT TO SYNTHESIZE:\\n"\n        f"{_compact_prompt(draft, 14_000)}"\n    )\n    try:\n        result = await llm_service.generate(\n            prompt=prompt,\n            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,\n            temperature=0.2,\n            max_output_tokens=4096,\n        )\n        return result.strip() or draft.strip()\n    except Exception:\n        # A valid specialist answer is better than replacing useful work with a\n        # second-provider failure. The stream boundary still hides raw partials.\n        return draft.strip()\n\n\ndef _grounding_unavailable_message() -> str:\n''',
    '''async def _synthesize_draft(message: str, draft: str) -> str:\n    """Convert an internal specialist final into one clean user-facing answer."""\n    from src.services.llm import llm_service\n\n    prompt = (\n        "USER REQUEST AND CONTEXT:\\n"\n        f"{_compact_prompt(message, 18_000)}\\n\\n"\n        "INTERNAL DRAFT TO SYNTHESIZE:\\n"\n        f"{_compact_prompt(draft, 14_000)}"\n    )\n    try:\n        result = await llm_service.generate(\n            prompt=prompt,\n            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,\n            temperature=0.2,\n            max_output_tokens=4096,\n        )\n        return result.strip() or draft.strip()\n    except Exception:\n        # A valid specialist answer is better than replacing useful work with a\n        # second-provider failure. The stream boundary still hides raw partials.\n        return draft.strip()\n\n\nasync def _synthesize_draft_stream(message: str, draft: str) -> AsyncIterator[str]:\n    """Stream final synthesis so complex answers do not appear all at once."""\n    from src.services.llm import llm_service\n\n    prompt = (\n        "USER REQUEST AND CONTEXT:\\n"\n        f"{_compact_prompt(message, 18_000)}\\n\\n"\n        "INTERNAL DRAFT TO SYNTHESIZE:\\n"\n        f"{_compact_prompt(draft, 14_000)}"\n    )\n    emitted = False\n    try:\n        async for chunk in llm_service.generate_stream(\n            prompt=prompt,\n            system_instruction=_SYNTHESIS_SYSTEM_INSTRUCTION,\n            temperature=0.2,\n            max_output_tokens=4096,\n        ):\n            if chunk:\n                emitted = True\n                yield str(chunk)\n        if emitted:\n            return\n    except Exception:\n        if emitted:\n            return\n\n    fallback = await _synthesize_draft(message, draft)\n    if fallback:\n        yield fallback\n\n\ndef _grounding_unavailable_message() -> str:\n''',
    "add streaming final synthesis",
)

# 3) Fast path: stream directly from rotating LLM provider. This avoids ADK
# setup/probing for ordinary conversation and lowers time-to-first-token.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''    ):\n        if not adk_runner.use_adk():\n            yield {"event": "start", "data": {"conversation_id": conversation_id}}\n''',
    '''    ):\n        if fast_path and not _requires_live_verification(message):\n            yield {"event": "start", "data": {"conversation_id": conversation_id}}\n            yield {"event": "agent", "data": {"agent_id": "direct"}}\n            direct_chunks: list[str] = []\n            try:\n                async for chunk in _direct_stream(message):\n                    for piece in _stream_pieces(chunk):\n                        direct_chunks.append(piece)\n                        yield {"event": "chunk", "data": {"text": piece}}\n                output = "".join(direct_chunks).strip()\n                if not output:\n                    raise RuntimeError("Direct fast stream returned an empty response")\n                yield {\n                    "event": "completed",\n                    "data": {"output": output, "conversation_id": conversation_id, "citations": []},\n                }\n            except Exception:\n                output = "".join(direct_chunks).strip()\n                if not output:\n                    output = "Unable to generate a response right now. Please retry."\n                    for piece in _stream_pieces(output):\n                        yield {"event": "chunk", "data": {"text": piece}}\n                yield {\n                    "event": "error",\n                    "data": {"error": "The response stream was interrupted. Please retry.", "conversation_id": conversation_id},\n                }\n                yield {\n                    "event": "completed",\n                    "data": {"output": output, "conversation_id": conversation_id, "citations": []},\n                }\n            return\n\n        if not adk_runner.use_adk():\n            yield {"event": "start", "data": {"conversation_id": conversation_id}}\n''',
    "add true direct fast stream",
)

# Word/token pieces for direct fallback rather than provider-sized blobs.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                async for chunk in _direct_stream(message):\n                    chunks.append(chunk)\n                    yield {"event": "chunk", "data": {"text": chunk}}\n''',
    '''                async for chunk in _direct_stream(message):\n                    for piece in _stream_pieces(chunk):\n                        chunks.append(piece)\n                        yield {"event": "chunk", "data": {"text": piece}}\n''',
    "rechunk non-ADK direct stream",
)

# Word/token pieces for Boss/final-synthesizer partials.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                            if text:\n                                boss_chunks.append(text)\n                                exposed_answer_text = True\n                                yield {"event": "chunk", "data": {"text": text}}\n''',
    '''                            if text:\n                                exposed_answer_text = True\n                                for piece in _stream_pieces(text):\n                                    boss_chunks.append(piece)\n                                    yield {"event": "chunk", "data": {"text": piece}}\n''',
    "rechunk boss partials",
)

# Stream synthesis and aggregated finals progressively.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                if completed_output and not _is_adk_failure(completed_output):\n                    if _is_user_facing(current_agent):\n                        final_output = completed_output\n                    else:\n                        final_output = await _synthesize_draft(message, completed_output)\n                        yield {"event": "agent", "data": {"agent_id": "final_synthesizer"}}\n                    yield {"event": "chunk", "data": {"text": final_output}}\n                    yield {\n                        "event": "completed",\n                        "data": {\n                            "output": final_output,\n                            "conversation_id": conversation_id,\n                            "citations": completed_citations,\n                        },\n                    }\n                    return\n''',
    '''                if completed_output and not _is_adk_failure(completed_output):\n                    final_chunks: list[str] = []\n                    if _is_user_facing(current_agent):\n                        for piece in _stream_pieces(completed_output):\n                            final_chunks.append(piece)\n                            yield {"event": "chunk", "data": {"text": piece}}\n                    else:\n                        yield {"event": "agent", "data": {"agent_id": "final_synthesizer"}}\n                        async for chunk in _synthesize_draft_stream(message, completed_output):\n                            for piece in _stream_pieces(chunk):\n                                final_chunks.append(piece)\n                                yield {"event": "chunk", "data": {"text": piece}}\n                    final_output = "".join(final_chunks).strip() or completed_output\n                    yield {\n                        "event": "completed",\n                        "data": {\n                            "output": final_output,\n                            "conversation_id": conversation_id,\n                            "citations": completed_citations,\n                        },\n                    }\n                    return\n''',
    "stream aggregated and synthesized finals",
)

# Stream ordinary fallback progressively instead of awaiting a full response.
replace_once(
    "backend/src/api/routes/_chat_quality.py",
    '''                fallback_failed = False\n                if _requires_live_verification(message):\n                    output = _grounding_unavailable_message()\n                    fallback_failed = True\n                else:\n                    try:\n                        output = await _direct_answer(message)\n                    except Exception:\n                        fallback_failed = True\n                        output = str((pending_error or {}).get("error", "") or "").strip()\n                        if not output:\n                            output = "Unable to generate a response right now. Please retry."\n\n                if not exposed_answer_text:\n                    yield {"event": "chunk", "data": {"text": output}}\n                if fallback_failed:\n''',
    '''                fallback_failed = False\n                fallback_chunks: list[str] = []\n                if _requires_live_verification(message):\n                    output = _grounding_unavailable_message()\n                    fallback_failed = True\n                    if not exposed_answer_text:\n                        for piece in _stream_pieces(output):\n                            fallback_chunks.append(piece)\n                            yield {"event": "chunk", "data": {"text": piece}}\n                else:\n                    try:\n                        async for chunk in _direct_stream(message):\n                            for piece in _stream_pieces(chunk):\n                                fallback_chunks.append(piece)\n                                if not exposed_answer_text:\n                                    yield {"event": "chunk", "data": {"text": piece}}\n                        output = "".join(fallback_chunks).strip()\n                        if not output:\n                            raise RuntimeError("Direct fallback returned an empty response")\n                    except Exception:\n                        fallback_failed = True\n                        output = "".join(fallback_chunks).strip()\n                        if not output:\n                            output = str((pending_error or {}).get("error", "") or "").strip()\n                        if not output:\n                            output = "Unable to generate a response right now. Please retry."\n                        if not fallback_chunks and not exposed_answer_text:\n                            for piece in _stream_pieces(output):\n                                yield {"event": "chunk", "data": {"text": piece}}\n\n                if fallback_failed:\n''',
    "stream fallback response progressively",
)

# 4) Update quality tests to assert progressive chunks and direct fast-path bypass.
replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''    assert result["chunks"] == ["Clean final answer"]\n''',
    '''    assert result["chunks"] == ["Clean ", "final ", "answer"]\n''',
    "update boss chunk expectation",
)

replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''async def fake_generate(*args, **kwargs):\n    return "Polished user-facing answer"\n\nllm_module.llm_service.generate = fake_generate\n''',
    '''async def fake_generate(*args, **kwargs):\n    return "Polished user-facing answer"\n\nasync def fake_generate_stream(*args, **kwargs):\n    yield "Polished "\n    yield "user-facing "\n    yield "answer"\n\nllm_module.llm_service.generate = fake_generate\nllm_module.llm_service.generate_stream = fake_generate_stream\n''',
    "mock streaming synthesizer",
)

replace_once(
    "backend/tests/test_chat_quality_runtime.py",
    '''    assert result["chunks"] == ["Polished user-facing answer"]\n''',
    '''    assert result["chunks"] == ["Polished ", "user-facing ", "answer"]\n''',
    "update synthesis chunk expectation",
)

append_marker = "\ndef test_fast_path_streams_directly_without_waiting_for_adk():\n"
test_path = Path("backend/tests/test_chat_quality_runtime.py")
test_text = test_path.read_text(encoding="utf-8")
if append_marker not in test_text:
    test_text += r'''


def test_fast_path_streams_directly_without_waiting_for_adk():
    result = _run_isolated(
        r'''
import asyncio
import json

import src.adk.runner as runner
import src.services.llm as llm_module

runner.use_adk = lambda: True
called = {"adk": 0}

async def fake_adk_stream(*args, **kwargs):
    called["adk"] += 1
    yield {"event": "completed", "data": {"output": "slow adk", "conversation_id": "internal", "citations": []}}

async def fake_direct_stream(*args, **kwargs):
    yield "Fast "
    yield "streaming "
    yield "answer"

runner.process_message_stream = fake_adk_stream
llm_module.llm_service.generate_stream = fake_direct_stream

import src.api.routes

async def main():
    events = []
    async for event in runner.process_fast_message_stream(
        "Explain this simply",
        user_id="u1",
        conversation_id="conversation-fast",
    ):
        events.append(event)
    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    completed = [e for e in events if e["event"] == "completed"][-1]
    print(json.dumps({"chunks": chunks, "completed": completed["data"], "adk_calls": called["adk"]}))

asyncio.run(main())
'''
    )

    assert result["chunks"] == ["Fast ", "streaming ", "answer"]
    assert result["completed"]["output"] == "Fast streaming answer"
    assert result["adk_calls"] == 0
'''
    test_path.write_text(test_text, encoding="utf-8")
    print("applied: add direct fast-path regression test")
else:
    print("already applied: add direct fast-path regression test")

print("streaming repair complete")
