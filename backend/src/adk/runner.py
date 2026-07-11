"""Google ADK Runner wrapper.

Manages ADK sessions and provides a clean API for executing
the multi-agent orchestrator via FastAPI endpoints.
"""

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from src.adk.agents import create_orchestrator_agent
from src.utils.logger import logger

SESSION_SERVICE = InMemorySessionService()
APP_NAME = "multi-agent-platform"


def get_or_create_session(user_id: str, conversation_id: str):
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


_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator_agent()
        logger.info("ADK orchestrator agent created")
    return _orchestrator


def create_runner(user_id: str, conversation_id: str) -> Runner:
    """Create an ADK Runner bound to a user session."""
    get_or_create_session(user_id, conversation_id)
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

    events = []
    async for event in runner.run_async(
        session_id=conversation_id,
        user_id=user_id,
        new_message=message,
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
