import pytest
from src.orchestrator.boss import BossAgent


@pytest.mark.asyncio
async def test_real_time_shopping_parameters():
    """Verify shopping intent analysis extracts budget, category, currency, and country."""
    boss = BossAgent()

    # Test 1: Mouse under 500
    intent1 = await boss._analyze_intent("Find me a mouse under ₹500")
    assert intent1["is_shopping"] is True
    assert intent1["shopping_params"]["category"] == "mouse"
    assert intent1["shopping_params"]["budget"] == 500.0
    assert intent1["shopping_params"]["currency"] == "INR"
    assert intent1["shopping_params"]["country"] == "India"

    # Test 2: Wireless gaming mouse under 1000
    intent2 = await boss._analyze_intent("Best wireless gaming mouse under ₹1000")
    assert intent2["is_shopping"] is True
    assert intent2["shopping_params"]["category"] == "mouse"
    assert intent2["shopping_params"]["budget"] == 1000.0

    # Test 3: Laptop under 60000
    intent3 = await boss._analyze_intent("Best laptop under ₹60000")
    assert intent3["is_shopping"] is True
    assert intent3["shopping_params"]["category"] == "laptop"
    assert intent3["shopping_params"]["budget"] == 60000.0


@pytest.mark.asyncio
async def test_shopping_graph_nodes():
    """Verify shopping graph includes product discovery, price verification, and category comparison."""
    boss = BossAgent()

    intent = await boss._analyze_intent("Find headphones under ₹3000")
    graph = await boss._build_execution_graph("t_shop_nodes", "Find headphones under ₹3000", intent)

    assert "product-researcher" in graph.nodes
    assert "price-verification-agent" in graph.nodes
    assert "product-comparison-agent" in graph.nodes
