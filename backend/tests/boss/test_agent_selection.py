import pytest
from src.orchestrator.boss import BossAgent
from src.agents.metadata import TaskMode


@pytest.mark.asyncio
async def test_simple_task_agent_selection():
    """Verify simple questions activate minimal team and exclude unrelated agents."""
    boss = BossAgent()

    # Query 1: Conceptual explanation
    intent1 = await boss._analyze_intent("What is a linked list?")
    graph1 = await boss._build_execution_graph("t_simple1", "What is a linked list?", intent1)

    node_ids1 = set(graph1.nodes.keys())
    assert len(node_ids1) <= 4, f"Simple task activated too many agents: {node_ids1}"
    assert "intent-detector" in node_ids1
    assert "final-synthesizer" in node_ids1
    assert "python-developer" not in node_ids1
    assert "product-researcher" not in node_ids1
    assert "database-engineer" not in node_ids1
    assert "image-generation-agent" not in node_ids1


@pytest.mark.asyncio
async def test_shopping_task_agent_selection():
    """Verify shopping request selects shopping specialists and excludes unrelated coding/data agents."""
    boss = BossAgent()

    intent = await boss._analyze_intent("Find me a mouse under ₹500")
    graph = await boss._build_execution_graph("t_shop_sel", "Find me a mouse under ₹500", intent)

    node_ids = set(graph.nodes.keys())
    assert "product-researcher" in node_ids
    assert "price-verification-agent" in node_ids
    assert "product-comparison-agent" in node_ids

    # Must NOT activate unrelated developers or financial analysts
    assert "python-developer" not in node_ids
    assert "database-engineer" not in node_ids
    assert "financial-analyst" not in node_ids
    assert "image-generation-agent" not in node_ids


@pytest.mark.asyncio
async def test_visual_logo_agent_selection():
    """Verify logo design request selects visual/branding team and excludes database or coding agents."""
    boss = BossAgent()

    intent = await boss._analyze_intent("Create a futuristic logo for my AI startup")
    graph = await boss._build_execution_graph("t_visual_sel", "Create a futuristic logo for my AI startup", intent)

    node_ids = set(graph.nodes.keys())
    assert "image-generation-agent" in node_ids
    assert "visual-critic" in node_ids

    assert "database-engineer" not in node_ids
    assert "web-researcher" not in node_ids
    assert "sql-analyst" not in node_ids


@pytest.mark.asyncio
async def test_data_csv_agent_selection():
    """Verify CSV analysis selects data specialists and excludes unrelated research or web agents."""
    boss = BossAgent()

    intent = await boss._analyze_intent("Analyze this CSV dataset and compute summary statistics and charts")
    graph = await boss._build_execution_graph("t_data_sel", "Analyze this CSV dataset", intent)

    node_ids = set(graph.nodes.keys())
    assert "data-analyst" in node_ids
    assert "product-researcher" not in node_ids
    assert "image-generation-agent" not in node_ids
