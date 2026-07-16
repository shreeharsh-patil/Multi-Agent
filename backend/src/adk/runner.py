"""Google ADK Runner wrapper.

Manages ADK sessions and provides a clean API for executing
the multi-agent orchestrator via FastAPI endpoints.

When the LLM provider is not Gemini, falls back to the custom agent
system since ADK is tightly coupled to Google's GenAI SDK.
"""

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.adk.agents import create_orchestrator_agent
from src.config import settings
from src.utils.logger import logger

SESSION_SERVICE = InMemorySessionService()
APP_NAME = "multi-agent-platform"


def use_adk() -> bool:
    """ADK only works with the Gemini provider.

    Returns True if a Gemini API key is configured (even if other
    fallback providers are available via the RotatingProvider).
    """
    return bool(settings.gemini_api_key)


async def get_or_create_session(user_id: str, conversation_id: str):
    """Get an existing session or create a new one."""
    session = SESSION_SERVICE.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=conversation_id,
    )
    if not session:
        session = SESSION_SERVICE.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=conversation_id,
        )
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
    """
    if conversation_id in ("default", ""):
        return ""
    try:
        from src.models.conversation import Conversation
        conv = await Conversation.get(conversation_id)
        if not conv or not conv.messages:
            return ""

        # Take all messages except the last user message (that's the current one)
        # to build the prior context
        context_parts = []
        for m in conv.messages:
            role = "User" if m.role == "user" else "Assistant"
            if m.content.strip():
                context_parts.append(f"{role}: {m.content.strip()}")

            # Include attachment names from metadata so the LLM knows what
            # files were attached in previous turns (e.g. image names).
            metadata = m.metadata
            if metadata and isinstance(metadata, dict):
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

        output = await llm_service.generate(
            prompt=full_prompt,
            system_instruction=(
                "You are a helpful AI assistant on a multi-agent platform. "
                "You are having a conversation with a user. Use the conversation "
                "history provided before the latest message to understand context. "
                "Be creative, expressive, and provide thorough, well-structured "
                "answers. Use rich formatting: **bold** for emphasis, *italic* for "
                "terms, bullet points for lists, headings for structure, and "
                "examples or analogies to explain concepts."
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
        ):
            event_type = type(event).__name__
            agent_id = event.node_name if hasattr(event, "node_name") else "unknown"

            content_piece = _get_content_piece(event)

            if content_piece:
                accumulated_content += content_piece

            if agent_id != current_agent:
                current_agent = agent_id
                yield {"event": "agent", "data": {"agent_id": agent_id}}

            if content_piece:
                yield {"event": "chunk", "data": {"text": content_piece}}

            yield {
                "event": "trace",
                "data": {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "has_content": bool(content_piece),
                },
            }

            if hasattr(event, "is_final_response") and event.is_final_response():
                yield {
                    "event": "complete",
                    "data": {
                        "output": accumulated_content,
                        "conversation_id": conversation_id,
                    },
                }
                return

        yield {
            "event": "complete",
            "data": {
                "output": accumulated_content,
                "conversation_id": conversation_id,
            },
        }
    except Exception as e:
        logger.warning(f"ADK stream failed ({e}), falling back to RotatingProvider")
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

    accumulated = ""
    try:
        async for chunk in llm_service.generate_stream(
            prompt=prompt_with_context,
            system_instruction=(
                "You are a helpful AI assistant on a multi-agent platform. "
                "You are having a conversation with a user. Use the conversation "
                "history provided before the latest message to understand context. "
                "Be creative, expressive, and provide thorough, well-structured "
                "answers. Use rich formatting: **bold** for emphasis, *italic* for "
                "terms, bullet points for lists, headings for structure, and "
                "examples or analogies to explain concepts."
            ),
        ):
            if chunk:
                accumulated += chunk
                yield {"event": "chunk", "data": {"text": chunk}}
        yield {
            "event": "complete",
            "data": {"output": accumulated, "conversation_id": conversation_id},
        }
    except Exception as e:
        if accumulated:
            yield {"event": "chunk", "data": {"text": "\n\n[Error during streaming, partial response returned]"}}
        error_msg = f"I encountered an error: {e}"
        yield {"event": "chunk", "data": {"text": error_msg}}
        yield {
            "event": "complete",
            "data": {"output": accumulated + error_msg, "conversation_id": conversation_id},
        }
