import pytest
from src.orchestrator.boss import BossAgent
from src.agents.metadata import TaskMode


@pytest.mark.asyncio
async def test_multi_domain_complex_task():
    """Verify BossAgent combines specialists from multiple departments for complex multi-domain queries."""
    boss = BossAgent()

    user_prompt = "Research the best AI SaaS ideas, analyze competitors, estimate pricing, and design a landing page"
    intent = await boss._analyze_intent(user_prompt)

    assert intent["complexity"] in ["moderate", "complex"]
    assert intent["mode"] in [TaskMode.DEEP, TaskMode.CRITICAL, TaskMode.STANDARD]

    graph = await boss._build_execution_graph("t_multi_domain", user_prompt, intent)
    node_ids = set(graph.nodes.keys())

    # Should activate research, technical, coding/architecture nodes
    assert len(node_ids) >= 3
    assert "intent-detector" in node_ids
    assert "final-synthesizer" in node_ids
