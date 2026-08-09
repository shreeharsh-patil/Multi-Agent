import pytest
from src.agents.registry import AgentRegistry


def test_tool_selection_by_specialist():
    """Verify specialists declare exact required tools matching their domain."""
    AgentRegistry.initialize(force=True)

    img_meta = AgentRegistry.get_metadata("image-generation-agent")
    assert img_meta is not None
    assert "image_generation" in img_meta.required_tools

    prod_meta = AgentRegistry.get_metadata("product-researcher")
    assert prod_meta is not None
    assert "web_search" in prod_meta.required_tools

    code_meta = AgentRegistry.get_metadata("python-developer")
    assert code_meta is not None
    assert "code_execution" in code_meta.required_tools
