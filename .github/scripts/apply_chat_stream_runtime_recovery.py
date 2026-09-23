from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing expected block: {label}")
    return text.replace(old, new, 1)


# Backend: recover an SSE failure that happens before any user-visible text by
# running the already-hardened non-streaming ADK path once. This avoids turning
# transient streaming/runtime exceptions into a blank generic retry bubble.
path = Path('backend/src/api/routes/chat.py')
text = path.read_text(encoding='utf-8')

marker = '''def _chat_error_status(error: Exception) -> int:
    message = str(error).lower()
    if "429" in message or "rate limit" in message or "quota" in message:
        return 429
    if "timeout" in message or "timed out" in message:
        return 504
    return 503


class AttachmentInfo(BaseModel):
'''
replacement = '''def _chat_error_status(error: Exception) -> int:
    message = str(error).lower()
    if "429" in message or "rate limit" in message or "quota" in message:
        return 429
    if "timeout" in message or "timed out" in message:
        return 504
    return 503


async def _recover_stream_response(
    message: str,
    user_id: str,
    conversation_id: str,
    workspace_id: str | None,
    request_id: str,
) -> dict | None:
    """Best-effort recovery when SSE execution fails before producing text.

    The non-streaming path uses the same production ADK quality boundary and
    provider failover, but is independent of SSE/runner streaming mechanics.
    Keeping this recovery at the HTTP boundary prevents a transient streaming
    failure from becoming an empty generic retry response.
    """
    recovery_started_at = time.perf_counter()
    try:
        timeout_seconds = min(float(settings.chat_stream_timeout_seconds), 45.0)
        async with asyncio.timeout(timeout_seconds):
            result = await process_message(
                message=message,
                user_id=user_id,
                conversation_id=conversation_id,
                workspace_id=workspace_id,
            )
    except Exception as recovery_error:
        _chat_log(
            request_id,
            "stream_recovery",
            "error",
            recovery_started_at,
            error=str(recovery_error)[:500],
        )
        logger.warning(
            "chat_stream_recovery_failed",
            extra={"request_id": request_id, "error": str(recovery_error)[:500]},
        )
        return None

    output = str((result or {}).get("output", "") or "").strip()
    if not output:
        _chat_log(
            request_id,
            "stream_recovery",
            "error",
            recovery_started_at,
            error="empty recovery output",
        )
        return None

    _chat_log(
        request_id,
        "stream_recovery",
        "complete",
        recovery_started_at,
        output_chars=len(output),
    )
    return result


class AttachmentInfo(BaseModel):
'''
text = replace_once(text, marker, replacement, 'backend recovery helper')

text = replace_once(
    text,
    '''    async def event_generator():
        nonlocal accumulated_output
        try:
''',
    '''    async def event_generator():
        nonlocal accumulated_output
        recovery_message = body.message
        try:
''',
    'event generator recovery state',
)

text = replace_once(
    text,
    '''            augmented_message = f"SYSTEM TIME CONTEXT: Current server time is {now_str}.\\n\\n" + augmented_message
            stream_google_context = {
''',
    '''            augmented_message = f"SYSTEM TIME CONTEXT: Current server time is {now_str}.\\n\\n" + augmented_message
            recovery_message = augmented_message
            stream_google_context = {
''',
    'recovery augmented message',
)

old_except = '''        except Exception as e:
            friendly_error = _friendly_chat_error(e)
            logger.error(f"Stream error: {e}", exc_info=True)
            _chat_log(request_id, "request", "error", request_started_at, error=str(e)[:500], output_chars=len(accumulated_output))
            # Still try to save what we have
            if accumulated_output:
                await _save_messages(
                    conv_id=conv_id,
                    user_id=user_id,
                    user_message=body.message,
                    agent_message=accumulated_output,
                    agent_id=effective_agent_id or body.agent_id,
                    is_new=is_new,
                    request_id=request_id,
                )
            yield f"event: error\\ndata: {json.dumps({'error': friendly_error, 'code': 'CHAT_REQUEST_FAILED', 'request_id': request_id})}\\n\\n"
            yield f"event: complete\\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\\n\\n"
'''
new_except = '''        except Exception as e:
            friendly_error = _friendly_chat_error(e)
            logger.error(f"Stream error: {e}", exc_info=True)
            _chat_log(request_id, "request", "error", request_started_at, error=str(e)[:500], output_chars=len(accumulated_output))

            # If SSE/ADK streaming itself failed before any answer text became
            # visible, try the hardened non-streaming ADK path once. The same
            # request ID is persisted idempotently, so this cannot create a
            # duplicate conversation turn.
            if not accumulated_output and routed_agent_id != "image":
                recovery = await _recover_stream_response(
                    recovery_message,
                    user_id,
                    conv_id,
                    body.workspace_id,
                    request_id,
                )
                if recovery:
                    recovered_output = str(recovery.get("output", "") or "").strip()
                    recovered_citations = list(recovery.get("citations", []) or [])
                    accumulated_output = recovered_output
                    yield f"event: agent\\ndata: {json.dumps({'agent_id': 'stream_recovery'})}\\n\\n"
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
                    yield f"event: complete\\ndata: {json.dumps({'output': recovered_output, 'conversation_id': conv_id, 'citations': recovered_citations, 'recovered': True}, ensure_ascii=False)}\\n\\n"
                    return

            # If answer text already escaped before the exception, never replay
            # the model and risk mixing two generations. Persist the partial and
            # let the client preserve a non-empty completed payload.
            if accumulated_output:
                await _save_messages(
                    conv_id=conv_id,
                    user_id=user_id,
                    user_message=body.message,
                    agent_message=accumulated_output,
                    agent_id=effective_agent_id or body.agent_id,
                    is_new=is_new,
                    request_id=request_id,
                )
            yield f"event: error\\ndata: {json.dumps({'error': friendly_error, 'code': 'CHAT_REQUEST_FAILED', 'request_id': request_id})}\\n\\n"
            yield f"event: complete\\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\\n\\n"
'''
text = replace_once(text, old_except, new_except, 'backend stream exception recovery')
path.write_text(text, encoding='utf-8')


# Frontend: an SSE error event can legitimately be followed by a completed
# fallback payload. Do not permanently poison the request after the first error
# event; completed non-empty output wins.
path = Path('frontend/src/app/(dashboard)/chat/page.tsx')
text = path.read_text(encoding='utf-8')

old_error_event = '''            } else if (currentEvent === 'error' && data.error) {
                streamServerError = String(data.error)
                setChatDebug((current) => current ? { ...current, status: 'error', step: 'server_error', error: data.error } : current)
                if (frameId !== null) cancelAnimationFrame(frameId)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: `Error: ${data.error}` }
                      : msg,
                  ),
                )
            }
'''
new_error_event = '''            } else if (currentEvent === 'error' && data.error) {
                // The backend may recover and send a valid `complete` event
                // after an error marker. Keep the diagnostic pending instead
                // of overwriting the assistant bubble immediately.
                streamServerError = String(data.error)
                setChatDebug((current) => current ? { ...current, status: 'error', step: 'server_error', error: data.error } : current)
                if (frameId !== null) cancelAnimationFrame(frameId)
            }
'''
text = replace_once(text, old_error_event, new_error_event, 'frontend error event behavior')

old_complete_output = '''                accumulatedContent = data.output || accumulatedContent
                setConversationId(data.conversation_id)
'''
new_complete_output = '''                accumulatedContent = data.output || accumulatedContent
                // A non-empty completed fallback is authoritative even when an
                // earlier SSE error marker was emitted during provider failover.
                if (accumulatedContent.trim()) streamServerError = ''
                setConversationId(data.conversation_id)
'''
text = replace_once(text, old_complete_output, new_complete_output, 'frontend complete clears recovered error')

old_terminal_checks = '''      if (streamServerError) {
        throw new Error(streamServerError)
      }
      if (!streamCompleted) {
        throw new Error(`Chat stream closed before completion${streamRequestId ? ` (request ${streamRequestId})` : ''}.`)
      }
      if (!accumulatedContent.trim()) {
        throw new Error('The model returned an empty response.')
      }
'''
new_terminal_checks = '''      if (!streamCompleted) {
        throw new Error(streamServerError || `Chat stream closed before completion${streamRequestId ? ` (request ${streamRequestId})` : ''}.`)
      }
      if (!accumulatedContent.trim()) {
        throw new Error(streamServerError || 'The model returned an empty response.')
      }
'''
text = replace_once(text, old_terminal_checks, new_terminal_checks, 'frontend terminal stream checks')

old_final_bubble = '''                content: accumulatedContent || `Unable to generate a response. Please retry.${streamRequestId ? ` (Request ID: ${streamRequestId})` : ''}`,
                error: true,
'''
new_final_bubble = '''                content: accumulatedContent || `${errorMessage || 'Unable to generate a response. Please retry.'}${streamRequestId ? ` (Request ID: ${streamRequestId})` : ''}`,
                error: true,
'''
text = replace_once(text, old_final_bubble, new_final_bubble, 'frontend preserve server-friendly error')
path.write_text(text, encoding='utf-8')


# Backend tests for the recovery helper.
Path('backend/tests/test_chat_stream_runtime_recovery.py').write_text('''import pytest\n\n\n@pytest.mark.asyncio\nasync def test_stream_recovery_uses_non_streaming_adk_path(monkeypatch):\n    from src.api.routes import chat\n\n    async def fake_process_message(**kwargs):\n        assert kwargs["message"] == "augmented request"\n        assert kwargs["user_id"] == "user-1"\n        assert kwargs["conversation_id"] == "conv-1"\n        return {\n            "output": "Recovered answer",\n            "citations": [{"file_name": "Source", "url": "https://example.com"}],\n        }\n\n    monkeypatch.setattr(chat, "process_message", fake_process_message)\n    result = await chat._recover_stream_response(\n        "augmented request", "user-1", "conv-1", None, "req-12345678"\n    )\n\n    assert result is not None\n    assert result["output"] == "Recovered answer"\n\n\n@pytest.mark.asyncio\nasync def test_stream_recovery_returns_none_when_fallback_fails(monkeypatch):\n    from src.api.routes import chat\n\n    async def failing_process_message(**kwargs):\n        raise RuntimeError("provider exploded")\n\n    monkeypatch.setattr(chat, "process_message", failing_process_message)\n    result = await chat._recover_stream_response(\n        "request", "user-1", "conv-1", None, "req-12345678"\n    )\n\n    assert result is None\n''', encoding='utf-8')


# Frontend source regression tests for SSE error/completion semantics.
Path('frontend/tests/chat-stream-runtime-recovery.test.ts').write_text('''import fs from 'node:fs'\nimport path from 'node:path'\nimport { describe, expect, it } from 'vitest'\n\nconst source = fs.readFileSync(\n  path.join(process.cwd(), 'src/app/(dashboard)/chat/page.tsx'),\n  'utf8',\n)\n\ndescribe('chat stream runtime recovery', () => {\n  it('does not overwrite the assistant bubble immediately on an SSE error marker', () => {\n    const errorBranch = source.split("currentEvent === 'error'")[1]?.split('}\\n          } catch')[0] || ''\n    expect(errorBranch).toContain('streamServerError = String(data.error)')\n    expect(errorBranch).not.toContain('content: `Error: ${data.error}`')\n  })\n\n  it('lets a completed non-empty fallback clear a prior stream error', () => {\n    expect(source).toContain("if (accumulatedContent.trim()) streamServerError = ''")\n    expect(source).toContain("throw new Error(streamServerError || 'The model returned an empty response.')")\n  })\n\n  it('shows the server-friendly error with the request id when recovery is impossible', () => {\n    expect(source).toContain("content: accumulatedContent || `${errorMessage || 'Unable to generate a response. Please retry.'}")\n  })\n})\n''', encoding='utf-8')

print('chat stream runtime recovery patch applied')
