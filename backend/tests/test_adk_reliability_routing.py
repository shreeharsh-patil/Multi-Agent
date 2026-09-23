from types import SimpleNamespace

import pytest

from src.api.routes import chat as chat_module
from src.api.routes.chat import ChatRequest, _adk_routing_preamble, _generate_image_message, _use_compact_adk_boss
from src.orchestrator.dynamic import plan_dynamic
from src.orchestrator.router import AgentRouter


def _is_fast(message: str) -> bool:
    body = ChatRequest(message=message)
    plan = plan_dynamic(message, has_attachments=False, has_workspace=False)
    return _use_compact_adk_boss(body, plan, automatic_mode=True)


def test_pcce_location_question_requires_research_grounding():
    assert AgentRouter().route_smart("Where is PCCE Goa?") == "research"
    assert _is_fast("Where is PCCE Goa?") is False
    hint = _adk_routing_preamble("research", [])
    assert "Google Search" in hint
    assert "exact entity or acronym" in hint
    assert "official organisation domains" in hint


def test_plural_and_natural_image_requests_route_to_image_generation():
    router = AgentRouter()
    assert router.route_smart("Generate images of a futuristic Goa city") == "image"
    assert router.route_smart("Create three pictures of a drone at sunset") == "image"
    assert router.route_smart("Visualize an illustration of a robot classroom") == "image"


@pytest.mark.asyncio
async def test_image_request_returns_visual_without_prompt_paragraph(monkeypatch):
    async def fake_generate_and_store_image(**kwargs):
        return SimpleNamespace(
            download_url="/api/documents/generated-1/file",
            revised_prompt="long internal enhanced prompt that should stay hidden",
        )

    monkeypatch.setattr(chat_module, "generate_and_store_image", fake_generate_and_store_image)
    output = await _generate_image_message("Generate an image of a drone", "u1", None)
    assert output == "![Generated image](/api/documents/generated-1/file)"
    assert "Prompt used" not in output
    assert "enhanced prompt" not in output
