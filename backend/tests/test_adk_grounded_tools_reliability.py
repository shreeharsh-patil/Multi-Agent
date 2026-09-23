from src.adk.agents import create_research_agent
from src.api.routes import _chat_quality as quality
from src.api.routes.chat import ChatRequest, _use_compact_adk_boss
from src.orchestrator.dynamic import plan_dynamic
from src.orchestrator.router import AgentRouter


def _is_fast(message: str) -> bool:
    body = ChatRequest(message=message)
    plan = plan_dynamic(message, has_attachments=False, has_workspace=False)
    return _use_compact_adk_boss(body, plan, automatic_mode=True)


def test_named_external_entity_variants_require_research():
    router = AgentRouter()
    for prompt in (
        "Where is PCCE Goa?",
        "What is PCCE Goa?",
        "Tell me about PCCE Goa",
        "Give me details about PCCE Goa",
    ):
        assert router.route_smart(prompt) == "research"
        assert plan_dynamic(prompt)["steps"][0]["agent_id"] == "research"
        assert _is_fast(prompt) is False
        assert quality._requires_live_verification(prompt) is True


def test_timeless_general_question_does_not_require_external_grounding():
    assert quality._requires_live_verification("Explain binary search with an example") is False


def test_research_agent_has_native_google_search_grounding():
    agent = create_research_agent()
    assert agent.tools
    assert any(
        tool is not None
        and (
            "GoogleSearchTool" in type(tool).__name__
            or str(getattr(tool, "name", "")).lower() in {"google_search", "google-search"}
        )
        for tool in agent.tools
    )


def test_more_visual_generation_phrases_route_to_image():
    router = AgentRouter()
    assert router.route_smart("Create a wallpaper of a futuristic Goa skyline") == "image"
    assert router.route_smart("Generate a thumbnail for a robotics video") == "image"
    assert router.route_smart("Design concept art of an autonomous drone") == "image"
