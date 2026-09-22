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
    "backend/src/adk/runner.py",
    '''def _to_content(message: str) -> types.Content:\n    """Wrap a plain text string into a google.genai.types.Content object.\n\n    The ADK Runner.run_async() expects new_message to be a Content\n    object with a .role attribute, not a raw string.\n    """\n    return types.Content(role="user", parts=[types.Part(text=message)])\n\n\n_boss_agent = None\n''',
    '''def _to_content(message: str) -> types.Content:\n    """Wrap a plain text string into a google.genai.types.Content object.\n\n    The ADK Runner.run_async() expects new_message to be a Content\n    object with a .role attribute, not a raw string.\n    """\n    return types.Content(role="user", parts=[types.Part(text=message)])\n\n\ndef _strip_persisted_history(message: str) -> str:\n    """Remove the MongoDB history block when ADK already owns the session.\n\n    The API hydrates prompts from persistent conversation history so a chat can\n    recover after a process restart. On a warm process ADK already retains the\n    same turns in its session; injecting the block again duplicates context and\n    causes needless token growth. Other prompt prefixes (time, memory, files,\n    routing hints) are intentionally preserved.\n    """\n    start_marker = "=== PREVIOUS CONVERSATION HISTORY ===\\n"\n    end_marker = "====================================\\n\\n"\n    start = message.find(start_marker)\n    if start < 0:\n        return message\n    end = message.find(end_marker, start + len(start_marker))\n    if end < 0:\n        return message\n    return message[:start] + message[end + len(end_marker):]\n\n\nasync def _session_exists(user_id: str, session_id: str) -> bool:\n    """Return whether this worker already has an ADK session for the chat."""\n    session = await SESSION_SERVICE.get_session(\n        app_name=APP_NAME,\n        user_id=user_id,\n        session_id=session_id,\n    )\n    return session is not None\n\n\n_boss_agent = None\n''',
    "add persistent-history deduplication helpers",
)

replace_once(
    "backend/src/adk/runner.py",
    '''        run_session_id = conversation_id if _failover_attempt == 0 else f"{conversation_id}-retry-{_failover_attempt}"\n        runner, route, grounding_route = await create_runner(user_id, run_session_id, workspace_id)\n        content = _to_content(message)\n''',
    '''        run_session_id = conversation_id if _failover_attempt == 0 else f"{conversation_id}-retry-{_failover_attempt}"\n        session_existed = await _session_exists(user_id, run_session_id)\n        runner, route, grounding_route = await create_runner(user_id, run_session_id, workspace_id)\n        effective_message = _strip_persisted_history(message) if session_existed else message\n        content = _to_content(effective_message)\n''',
    "deduplicate history in non-stream ADK requests",
)

replace_once(
    "backend/src/adk/runner.py",
    '''        run_session_id = conversation_id if _failover_attempt == 0 else f"{conversation_id}-retry-{_failover_attempt}"\n        runner, route, grounding_route = await create_runner(user_id, run_session_id, workspace_id, fast_path=fast_path)\n        content = _to_content(message)\n''',
    '''        run_session_id = conversation_id if _failover_attempt == 0 else f"{conversation_id}-retry-{_failover_attempt}"\n        session_existed = await _session_exists(user_id, run_session_id)\n        runner, route, grounding_route = await create_runner(user_id, run_session_id, workspace_id, fast_path=fast_path)\n        effective_message = _strip_persisted_history(message) if session_existed else message\n        content = _to_content(effective_message)\n''',
    "deduplicate history in streaming ADK requests",
)

print("ADK session quality patch complete")
