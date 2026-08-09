import pytest
from src.orchestrator.boss import BossAgent


@pytest.mark.asyncio
async def test_laptop_shopping_agent_selection():
    """Verify laptop shopping query under ₹60000 selects product specialists and excludes unrelated visual agents."""
    boss = BossAgent()

    user_query = "Find a good laptop under ₹60000 for coding."
    intent = await boss._analyze_intent(user_query)

    graph = await boss._build_execution_graph("t_laptop", user_query, intent)
    node_ids = set(graph.nodes.keys())

    assert "product-researcher" in node_ids
    assert "price-verification-agent" in node_ids
    assert "product-comparison-agent" in node_ids
    assert "image-generation-agent" not in node_ids
    assert "ui-designer" not in node_ids


@pytest.mark.asyncio
async def test_coding_bug_agent_selection():
    """Verify Next.js bug fix query selects developers and excludes database engineer when no DB issues exist."""
    boss = BossAgent()

    user_query = "Fix my Next.js authentication bug."
    intent = await boss._analyze_intent(user_query)

    graph = await boss._build_execution_graph("t_nextjs", user_query, intent)
    node_ids = set(graph.nodes.keys())

    assert "intent-detector" in node_ids
    assert "product-researcher" not in node_ids
    assert "image-generation-agent" not in node_ids


@pytest.mark.asyncio
async def test_logo_design_agent_selection():
    """Verify futuristic logo design request selects FLUX image pipeline specialists."""
    boss = BossAgent()

    user_query = "Create a modern futuristic logo for my AI startup."
    intent = await boss._analyze_intent(user_query)

    graph = await boss._build_execution_graph("t_logo", user_query, intent)
    node_ids = set(graph.nodes.keys())

    assert "prompt-engineer" in node_ids
    assert "image-generation-agent" in node_ids
    assert "visual-critic" in node_ids
    assert "database-engineer" not in node_ids
