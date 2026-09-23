from src.api.routes.chat import ChatRequest, _use_compact_adk_boss
from src.orchestrator.dynamic import plan_dynamic


def _is_fast(message: str, conversation_id: str | None = None) -> bool:
    body = ChatRequest(message=message, conversation_id=conversation_id)
    plan = plan_dynamic(message, has_attachments=False, has_workspace=False)
    return _use_compact_adk_boss(body, plan, automatic_mode=True)


def test_binary_search_explanation_stays_on_fast_stream_path():
    assert _is_fast("Explain binary search in simple words") is True


def test_general_followup_can_stay_on_fast_stream_path():
    assert _is_fast("Explain that with a simple example", conversation_id="conversation-123") is True


def test_live_and_web_requests_keep_full_agent_runtime():
    assert _is_fast("Search the web for the latest AI news") is False
    assert _is_fast("What is the current Bitcoin price?") is False


def test_tool_and_code_requests_keep_full_agent_runtime():
    assert _is_fast("Debug this Python code") is False
    assert _is_fast("Check my calendar schedule") is False
