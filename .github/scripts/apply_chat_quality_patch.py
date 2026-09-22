from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"could not find expected block for: {label}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


replace_once(
    "backend/src/api/routes/chat.py",
    '''    return bool(\n        direct_boss_mode\n        and not body.attachments\n        and not body.workspace_id\n        and (\n            simple_greeting\n            or (\n                automatic_mode\n                and not body.conversation_id\n                and len((dynamic_plan or {}).get("steps", [])) <= 1\n                and not re.search(r"(?i)\\b(research|latest|current|search|calculate|calendar|drive|file|pdf|web)\\b", body.message)\n            )\n        )\n    )\n''',
    '''    return bool(\n        direct_boss_mode\n        and not body.attachments\n        and not body.workspace_id\n        # Existing conversations must keep their stored history and memory.\n        # The compact route is intentionally stateless, so using it for a\n        # follow-up makes the assistant appear to forget earlier turns.\n        and not body.conversation_id\n        and (\n            simple_greeting\n            or (\n                automatic_mode\n                and len((dynamic_plan or {}).get("steps", [])) <= 1\n                and not re.search(r"(?i)\\b(research|latest|current|search|calculate|calendar|drive|file|pdf|web)\\b", body.message)\n            )\n        )\n    )\n''',
    "disable stateless compact route for existing conversations",
)

context_old = '''        from src.services.memory.service import memory_service\n        try:\n            async with asyncio.timeout(settings.chat_context_timeout_seconds):\n                memory_context, attachment_context, history_snippet = await asyncio.gather(\n                    memory_service.build_context(user_id, body.message),\n                    _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),\n                    _build_full_conversation_history(body.conversation_id),\n                )\n        except TimeoutError:\n            _chat_log(request_id, "context", "error", request_started_at, error="context timeout")\n            memory_context, attachment_context, history_snippet = "", "", ""\n'''
context_new = '''        from src.services.memory.service import memory_service\n        # Resolve context pieces independently. A slow memory lookup or file\n        # parser must never erase already available conversation history.\n        memory_result, attachment_result, history_result = await asyncio.gather(\n            asyncio.wait_for(\n                memory_service.build_context(user_id, body.message),\n                timeout=settings.chat_context_timeout_seconds,\n            ),\n            asyncio.wait_for(\n                _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),\n                timeout=settings.chat_context_timeout_seconds,\n            ),\n            asyncio.wait_for(\n                _build_full_conversation_history(body.conversation_id),\n                timeout=settings.chat_context_timeout_seconds,\n            ),\n            return_exceptions=True,\n        )\n        memory_context = "" if isinstance(memory_result, Exception) else memory_result\n        attachment_context = "" if isinstance(attachment_result, Exception) else attachment_result\n        history_snippet = "" if isinstance(history_result, Exception) else history_result\n        if any(isinstance(item, Exception) for item in (memory_result, attachment_result, history_result)):\n            _chat_log(request_id, "context", "partial", request_started_at, error="one or more context sources timed out or failed")\n'''
replace_once(
    "backend/src/api/routes/chat.py",
    context_old,
    context_new,
    "preserve partial context in non-stream chat",
)

stream_context_old = '''            if fast_path:\n                memory_context, attachment_context, history_snippet = "", "", ""\n            else:\n                try:\n                    async with asyncio.timeout(settings.chat_context_timeout_seconds):\n                        memory_context, attachment_context, history_snippet = await asyncio.gather(\n                            memory_service.build_context(user_id, body.message),\n                            _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),\n                            _build_full_conversation_history(body.conversation_id),\n                        )\n                except TimeoutError:\n                    _chat_log(request_id, "context", "error", context_started_at, error="context timeout")\n                    memory_context, attachment_context, history_snippet = "", "", ""\n'''
stream_context_new = '''            if fast_path:\n                # Fast path is allowed only for brand-new conversations.\n                memory_context, attachment_context, history_snippet = "", "", ""\n            else:\n                memory_result, attachment_result, history_result = await asyncio.gather(\n                    asyncio.wait_for(\n                        memory_service.build_context(user_id, body.message),\n                        timeout=settings.chat_context_timeout_seconds,\n                    ),\n                    asyncio.wait_for(\n                        _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),\n                        timeout=settings.chat_context_timeout_seconds,\n                    ),\n                    asyncio.wait_for(\n                        _build_full_conversation_history(body.conversation_id),\n                        timeout=settings.chat_context_timeout_seconds,\n                    ),\n                    return_exceptions=True,\n                )\n                memory_context = "" if isinstance(memory_result, Exception) else memory_result\n                attachment_context = "" if isinstance(attachment_result, Exception) else attachment_result\n                history_snippet = "" if isinstance(history_result, Exception) else history_result\n                if any(isinstance(item, Exception) for item in (memory_result, attachment_result, history_result)):\n                    _chat_log(request_id, "context", "partial", context_started_at, error="one or more context sources timed out or failed")\n'''
replace_once(
    "backend/src/api/routes/chat.py",
    stream_context_old,
    stream_context_new,
    "preserve partial context in streaming chat",
)

replace_once(
    "backend/src/adk/runner.py",
    '''            instruction=(\n                "You are Boss Agent. Answer greetings and ordinary conversational questions "\n                "directly, accurately, and concisely. Do not claim to have searched the web. "\n                "This compact route is used only when no tools, documents, current information, "\n                "or specialist delegation are required."\n            ),\n''',
    '''            instruction=(\n                "You are Boss Agent, the user-facing conversational assistant. Give the answer "\n                "the user is actually asking for, with natural wording and strong instruction "\n                "following. Be concise for simple questions, but give enough explanation, steps, "\n                "examples, or code when the request needs them. Preserve context supplied in the "\n                "prompt, do not expose internal agent or routing details, and do not invent facts. "\n                "Do not claim to have searched the web. This compact route is used only for a "\n                "brand-new conversation when no tools, documents, current information, or "\n                "specialist delegation are required."\n            ),\n''',
    "improve compact Boss conversational instruction",
)

replace_once(
    "backend/src/adk/agents.py",
    '''    "FINAL-ANSWER AUTHORITY (MANDATORY): You alone are the user-facing responder. "\n    "Specialists and managers provide internal reports only. After delegation, take "\n    "back control, reconcile their evidence, and write the final answer yourself. "\n    "Never leave a specialist's raw report as the final user response.\\n\\n"\n''',
    '''    "FINAL-ANSWER AUTHORITY (MANDATORY): You alone are the user-facing responder. "\n    "Specialists and managers provide internal reports only. After delegation, take "\n    "back control, reconcile their evidence, and write the final answer yourself. "\n    "Never leave a specialist's raw report as the final user response.\\n\\n"\n    "CONVERSATION QUALITY BAR (MANDATORY): Respond like a polished general-purpose chat "\n    "assistant, not like an orchestration log. Start with the useful answer, not internal process. "\n    "Match the user's requested depth, language, format, and tone. Keep simple answers compact; "\n    "for complex requests provide clear reasoning summaries, steps, examples, and implementation "\n    "details where useful. Use prior conversation context to resolve follow-ups and pronouns. "\n    "Never mention delegation, routing, departments, managers, confidence scores, or specialist "\n    "reports unless the user explicitly asks about the multi-agent system itself. Do not repeat "\n    "the user's prompt unnecessarily, do not pad answers with generic headings, and ask a "\n    "clarifying question only when a missing fact prevents a useful answer.\\n\\n"\n''',
    "add user-facing conversation quality contract",
)

print("chat quality patch complete")
