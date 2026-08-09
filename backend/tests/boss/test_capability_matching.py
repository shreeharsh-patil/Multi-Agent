import pytest
from src.agents.registry import AgentRegistry
from src.orchestrator.boss import BossAgent


def test_registry_capability_search():
    """Verify registry search by capability tags returns exact matching agents."""
    AgentRegistry.initialize(force=True)
    all_meta = AgentRegistry.get_all_metadata()
    assert len(all_meta) >= 100

    code_caps = AgentRegistry.get_by_capability("python-coding")
    assert len(code_caps) >= 1
    assert any(a.manifest.id == "python-developer" for a in code_caps)


def test_agent_relevance_scoring():
    """Verify BossAgent scores relevance based on capability overlap, tools, and domain expertise."""
    AgentRegistry.initialize(force=True)
    boss = BossAgent()
    meta_product = AgentRegistry.get_metadata("product-researcher")
    meta_python = AgentRegistry.get_metadata("python-developer")

    assert meta_product is not None
    assert meta_python is not None

    req_caps = ["product-discovery", "current-prices", "specifications"]
    req_tools = ["web_search"]

    score_product = boss._score_agent_relevance(meta_product, req_caps, req_tools)
    score_python = boss._score_agent_relevance(meta_python, req_caps, req_tools)

    assert score_product > score_python, f"Product Researcher ({score_product}) should score higher than Python Developer ({score_python}) for product discovery"
