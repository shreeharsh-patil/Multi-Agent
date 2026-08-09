import pytest
from src.orchestrator.boss import BossAgent
from src.agents.metadata import TaskMode


@pytest.mark.asyncio
async def test_complex_reasoning_saas_llm():
    """Verify complex SaaS LLM request builds DEEP / CRITICAL mode graph with multi-domain specialists."""
    boss = BossAgent()

    user_query = "Research the latest open-source LLMs, compare their capabilities and costs, then recommend which one I should use for my SaaS."
    intent = await boss._analyze_intent(user_query)

    assert intent["complexity"] == "complex"
    assert intent["mode"] in [TaskMode.DEEP, TaskMode.CRITICAL]

    graph = await boss._build_execution_graph("t_saas_llm", user_query, intent)
    node_ids = set(graph.nodes.keys())

    assert len(node_ids) >= 3
    assert "intent-detector" in node_ids
