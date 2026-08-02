"""Google ADK Runner wrapper.

Manages ADK sessions and provides a clean API for executing
the multi-agent orchestrator via FastAPI endpoints.

When the LLM provider is not Gemini, falls back to the custom agent
system since ADK is tightly coupled to Google's GenAI SDK.
"""

from google.adk import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.adk.agents import create_orchestrator_agent
from src.config import settings
from src.utils.logger import logger

SESSION_SERVICE = InMemorySessionService()
APP_NAME = "agentic"


def use_adk() -> bool:
    """ADK only works with the Gemini provider.

    Returns True if a Gemini API key is configured (even if other
    fallback providers are available via the RotatingProvider).
    """
    return bool(settings.gemini_api_key)


async def get_or_create_session(user_id: str, conversation_id: str):
    """Get an existing session or create a new one."""
    import inspect
    session_res = SESSION_SERVICE.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=conversation_id,
    )
    session = await session_res if inspect.iscoroutine(session_res) else session_res

    if not session:
        create_res = SESSION_SERVICE.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=conversation_id,
        )
        session = await create_res if inspect.iscoroutine(create_res) else create_res
        logger.info(f"Created session: {conversation_id} for user: {user_id}")
    return session


def _to_content(message: str) -> types.Content:
    """Wrap a plain text string into a google.genai.types.Content object.

    The ADK Runner.run_async() expects new_message to be a Content
    object with a .role attribute, not a raw string.
    """
    return types.Content(role="user", parts=[types.Part(text=message)])


_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator_agent()
        logger.info("ADK orchestrator agent created")
    return _orchestrator


async def create_runner(user_id: str, conversation_id: str) -> Runner:
    """Create an ADK Runner bound to a user session."""
    await get_or_create_session(user_id, conversation_id)
    return Runner(
        agent=get_orchestrator(),
        app_name=APP_NAME,
        session_service=SESSION_SERVICE,
        auto_create_session=False,
    )


def _get_content_piece(event) -> str:
    """Extract text content from an ADK Event object.

    Handles both real ADK Events (where content/message are Content/Part structures)
    and mock events from unit tests (where content/message might be plain strings).
    """
    if not event:
        return ""

    # 1. Try event.content
    content = getattr(event, "content", None)
    if content:
        if isinstance(content, str):
            return content
        parts = getattr(content, "parts", None)
        if parts:
            pieces = []
            for p in parts:
                text = getattr(p, "text", None)
                if text is not None:
                    pieces.append(str(text))
            return "".join(pieces)
        return str(content)

    # 2. Try event.message
    message = getattr(event, "message", None)
    if message:
        if isinstance(message, str):
            return message
        text = getattr(message, "text", None)
        if text is not None:
            return str(text)
        return str(message)

    return ""


async def process_message(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
) -> dict:
    """Process a user message through the ADK multi-agent system.

    Uses ADK when Gemini is available. If ADK/Gemini fails (e.g. quota
    exhausted), falls back to direct LLM via the RotatingProvider which
    auto-rotates through AIand, Groq, OpenRouter, etc.
    """
    if not use_adk():
        return await _fallback_process_message(message, user_id, conversation_id)

    # Try ADK first, fall back to RotatingProvider on failure
    try:
        runner = await create_runner(user_id, conversation_id)
        content = _to_content(message)

        events = []
        async for event in runner.run_async(
            session_id=conversation_id,
            user_id=user_id,
            new_message=content,
        ):
            events.append(event)

        final_event = None
        for event in reversed(events):
            if event.is_final_response():
                final_event = event
                break

        output = ""
        if final_event:
            output = _get_content_piece(final_event)

        agent_traces = []
        for event in events:
            agent_traces.append({
                "agent_id": event.node_name if hasattr(event, "node_name") else "unknown",
                "event_type": str(type(event).__name__),
                "has_content": bool(_get_content_piece(event)),
            })

        logger.info(
            f"ADK processed message",
            extra={
                "conversation_id": conversation_id,
                "events_count": len(events),
                "final_output_length": len(output),
            },
        )

        return {
            "output": output,
            "citations": [],
            "agent_traces": agent_traces,
            "events_count": len(events),
        }
    except Exception as e:
        logger.warning(f"ADK failed ({e}), falling back to RotatingProvider")
        return await _fallback_process_message(message, user_id, conversation_id)


async def _build_conversation_context(conversation_id: str) -> str:
    """Load conversation history from MongoDB and format it.

    Returns a formatted string of previous messages, or an empty string
    if the conversation doesn't exist yet or has no history.

    Uses a MongoDB projection to fetch only the messages array instead of
    the entire document — much faster for long conversations.
    """
    if conversation_id in ("default", ""):
        return ""
    try:
        from beanie import PydanticObjectId
        from src.models.conversation import Conversation
        from src.utils.db import get_motor_collection

        # Use projection to fetch only messages — avoids transferring
        # the full document (title, metadata, timestamps, etc.) over the wire.
        raw = await get_motor_collection(Conversation).find_one(
            {"_id": PydanticObjectId(conversation_id)},
            {"messages": 1},
        )
        if not raw or "messages" not in raw:
            return ""

        messages_raw = raw["messages"]
        if not messages_raw:
            return ""

        context_parts = []
        for m in messages_raw:
            role = "User" if m.get("role") == "user" else "Assistant"
            content = (m.get("content") or "").strip()
            if content:
                context_parts.append(f"{role}: {content}")

            # Include attachment names from metadata so the LLM knows what
            # files were attached in previous turns (e.g. image names).
            metadata = m.get("metadata") or {}
            attachments = metadata.get("attachments")
            if attachments and isinstance(attachments, list):
                for att in attachments:
                    name = att.get("name") if isinstance(att, dict) else getattr(att, "name", None)
                    if name:
                        context_parts.append(f"   📎 attached: {name}")

        if not context_parts:
            return ""

        context_str = "\n".join(context_parts)
        # Keep last ~8000 chars to fit within context windows
        if len(context_str) > 8000:
            context_str = "... (earlier messages omitted)\n" + context_str[-8000:]
        return context_str
    except Exception as e:
        logger.warning(f"Could not load conversation context: {e}")
        return ""


async def _fallback_process_message(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
) -> dict:
    """Fallback: use the LLM provider directly without ADK.

    Includes prior conversation history so the model understands context.
    """
    from src.services.llm import llm_service

    try:
        # Load prior conversation history for context
        history = await _build_conversation_context(conversation_id)
        if history:
            full_prompt = (
                f"Previous conversation:\n{history}\n\n"
                f"User: {message}\n\n"
                f"Assistant:"
            )
        else:
            full_prompt = message

        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M:%S UTC")

        output = await llm_service.generate(
            prompt=full_prompt,
            system_instruction=(
                f"Current Real-Time System Date & Time: {now_utc}.\n"
                "You are an AI Assistant for the Agentic Multi-Agent Workspace platform.\n"
                "CREATOR ATTRIBUTION: This website, application, and platform were created, built, and designed by Shreeharsh. "
                "When asked 'who created this app', 'who made this website', 'who built this platform', or similar questions, respond directly and clearly: "
                "'This website and application were created and developed by **Shreeharsh**.'\n"
                "Always provide accurate, up-to-date real-time information based on current date and live web search when applicable. "
                "Never claim you cannot generate or export PDF files — this platform HAS automated PDF generation, study book publishing, and PDF export capabilities. "
                "Never claim you cannot access calendars, external applications, or tools in general — "
                "this platform integrates Google Calendar, Google Contacts, Google Drive, Gmail, RAG Document Analysis, Web Search, PDF Generation, and Python Execution. "
                "If a user asks about their contacts, calendar, or emails and their account is not connected, instruct them to connect Google in Settings → Integrations. "
                "Be thorough and well-structured: **bold** for emphasis, *italic* for terms, bullet points for lists, headings for structure."
            ),
        )
        return {
            "output": output,
            "citations": [],
            "agent_traces": [{"agent_id": "direct", "event_type": "DirectResponse", "has_content": True}],
            "events_count": 1,
        }
    except Exception as e:
        logger.error(f"Fallback LLM failed: {e}")
        return {
            "output": f"I encountered an error: {e}",
            "citations": [],
            "agent_traces": [{"agent_id": "direct", "event_type": "Error", "has_content": False}],
            "events_count": 1,
        }


async def process_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Process a user message and yield SSE events.

    Uses ADK for Gemini provider. If ADK/Gemini fails (e.g. quota
    exhausted), falls back to direct LLM via the RotatingProvider.
    """
    if not use_adk():
        async for event in _fallback_process_message_stream(message, user_id, conversation_id):
            yield event
        return

    # Try ADK first, fall back to RotatingProvider on failure
    try:
        runner = await create_runner(user_id, conversation_id)
        content = _to_content(message)

        accumulated_content = ""
        current_agent = "orchestrator"

        yield {"event": "start", "data": {"conversation_id": conversation_id}}

        async for event in runner.run_async(
            session_id=conversation_id,
            user_id=user_id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            event_type = type(event).__name__
            agent_id = event.node_name if hasattr(event, "node_name") else "unknown"

            content_piece = _get_content_piece(event)
            is_partial = bool(getattr(event, "partial", False))
            is_final = bool(getattr(event, "is_final_response", None) and event.is_final_response())

            if agent_id != current_agent:
                current_agent = agent_id
                yield {"event": "agent", "data": {"agent_id": agent_id}}

            # In SSE mode ADK emits incremental partial events followed by a
            # final aggregated event that repeats the full text. Only stream
            # (and accumulate) the partial chunks to avoid duplicating output.
            if content_piece and is_partial:
                accumulated_content += content_piece
                yield {"event": "chunk", "data": {"text": content_piece}}

            yield {
                "event": "trace",
                "data": {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "has_content": bool(content_piece),
                },
            }

            if is_final:
                # Prefer the aggregated final text; fall back to accumulated
                # partials if the final event carried no content.
                final_output = content_piece if content_piece else accumulated_content
                # If nothing was streamed as partial, emit the full text now
                # so the client still renders a response.
                if not accumulated_content and final_output:
                    yield {"event": "chunk", "data": {"text": final_output}}
                yield {
                    "event": "complete",
                    "data": {
                        "output": final_output,
                        "conversation_id": conversation_id,
                        "citations": [],
                    },
                }
                return

        yield {
            "event": "complete",
            "data": {
                "output": accumulated_content,
                "conversation_id": conversation_id,
                "citations": [],
            },
        }
    except Exception as e:
        logger.warning(f"ADK stream failed ({e}), falling back to RotatingProvider")
        async for event in _fallback_process_message_stream(message, user_id, conversation_id):
            yield event


async def process_fast_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Low-latency stream for ordinary chat with no tool or document needs.

    This intentionally bypasses ADK planning overhead. Requests that need
    tools, retrieval, attachments, or specialist collaboration use the full
    orchestrated path instead.
    """
    async for event in _fallback_process_message_stream(message, user_id, conversation_id):
        yield event


async def _fallback_process_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Fallback streaming: yield tokens from the LLM provider as they arrive.

    Includes prior conversation history so the model understands context.
    """
    from src.services.llm import llm_service

    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "direct"}}

    # Load prior conversation history for context
    history = await _build_conversation_context(conversation_id)
    if history:
        prompt_with_context = (
            f"Previous conversation:\n{history}\n\n"
            f"User: {message}\n\n"
            f"Assistant:"
        )
    else:
        prompt_with_context = message

    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M:%S UTC")

    accumulated = ""
    try:
        async for chunk in llm_service.generate_stream(
            prompt=prompt_with_context,
            system_instruction=(
                f"Current Real-Time System Date & Time: {now_utc}.\n"
                "You are an AI Assistant for the Agentic Multi-Agent Workspace platform.\n"
                "CREATOR ATTRIBUTION: This website, application, and platform were created, built, and designed by Shreeharsh. "
                "When asked 'who created this app', 'who made this website', 'who built this platform', or similar questions, respond directly and clearly: "
                "'This website and application were created and developed by **Shreeharsh**.'\n"
                "Always provide accurate, up-to-date real-time information based on current date and live web search when applicable. "
                "Never claim you cannot generate or export PDF files — this platform HAS automated PDF generation, study book publishing, and PDF export capabilities. "
                "Never claim you cannot access calendars, external applications, or tools in general — "
                "this platform integrates Google Calendar, Google Contacts, Google Drive, Gmail, RAG Document Analysis, Web Search, PDF Generation, and Python Execution. "
                "If a user asks about their contacts, calendar, or emails and their account is not connected, instruct them to connect Google in Settings → Integrations. "
                "Be thorough and well-structured: **bold** for emphasis, *italic* for terms, bullet points for lists, headings for structure."
            ),
        ):
            if chunk:
                accumulated += chunk
                yield {"event": "chunk", "data": {"text": chunk}}
        yield {
            "event": "complete",
            "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []},
        }
    except Exception as e:
        if accumulated:
            yield {"event": "chunk", "data": {"text": "\n\n[Error during streaming, partial response returned]"}}
        error_msg = f"I encountered an error: {e}"
        yield {"event": "chunk", "data": {"text": error_msg}}
        yield {
            "event": "complete",
            "data": {"output": accumulated + error_msg, "conversation_id": conversation_id, "citations": []},
        }
