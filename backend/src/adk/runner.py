"""Google ADK Runner wrapper.

Manages ADK sessions and provides a clean API for executing
the multi-agent orchestrator via FastAPI endpoints.
"""

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.adk.agents import create_orchestrator_agent
from src.utils.logger import logger

SESSION_SERVICE = InMemorySessionService()
APP_NAME = "multi-agent-platform"


async def get_or_create_session(user_id: str, conversation_id: str):
    """Get an existing session or create a new one."""
    session = await SESSION_SERVICE.get_session(
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


async def process_message(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
) -> dict:
    """Process a user message through the ADK multi-agent system.

    Returns the final response with agent trace information.
    """
    runner = create_runner(user_id, conversation_id)
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
    citations = []
    agent_traces = []

    if final_event:
        output = final_event.content if hasattr(final_event, 'content') else str(final_event.message)

    for event in events:
        agent_traces.append({
            "agent_id": event.node_name if hasattr(event, 'node_name') else "unknown",
            "event_type": str(type(event).__name__),
            "has_content": bool(event.content if hasattr(event, 'content') else False),
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
        "citations": citations,
        "agent_traces": agent_traces,
        "events_count": len(events),
    }


async def process_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Process a user message and yield SSE events as the ADK runner produces them.

    Yields dicts with 'event' and 'data' fields for SSE serialization.
    """
    runner = create_runner(user_id, conversation_id)
    content = _to_content(message)

    accumulated_content = ""
    current_agent = "unknown"

    yield {"event": "start", "data": {"conversation_id": conversation_id}}

    async for event in runner.run_async(
        session_id=conversation_id,
        user_id=user_id,
        new_message=content,
    ):
        event_type = type(event).__name__
        agent_id = event.node_name if hasattr(event, 'node_name') else "unknown"

        content_piece = ""
        if hasattr(event, 'content') and event.content:
            content_piece = str(event.content)
        elif hasattr(event, 'message') and event.message:
            content_piece = str(event.message)

        # Accumulate content
        if content_piece:
            accumulated_content += content_piece

        # Yield agent switch events
        if agent_id != current_agent:
            current_agent = agent_id
            yield {"event": "agent", "data": {"agent_id": agent_id}}

        # Yield content chunk
        if content_piece:
            yield {"event": "chunk", "data": {"text": content_piece}}

        # Yield trace
        yield {
            "event": "trace",
            "data": {
                "agent_id": agent_id,
                "event_type": event_type,
                "has_content": bool(content_piece),
            },
        }

        # If this is the final response, yield the completion event
        if hasattr(event, 'is_final_response') and event.is_final_response():
            yield {
                "event": "complete",
                "data": {
                    "output": accumulated_content,
                    "conversation_id": conversation_id,
                },
            }
            return

    # Fallback: yield complete if no final event was found
    yield {
        "event": "complete",
        "data": {
            "output": accumulated_content,
            "conversation_id": conversation_id,
        },
    }
