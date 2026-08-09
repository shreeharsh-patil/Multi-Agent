import pytest
from src.orchestrator.boss import BossAgent


@pytest.mark.asyncio
async def test_live_data_semantic_detection():
    """Verify BossAgent semantically detects time-sensitive queries requiring live retrieval."""
    boss = BossAgent()

    test_queries = [
        "latest AI models",
        "current laptop prices",
        "best mouse under ₹500",
        "today's tech news",
        "latest Python version",
        "current Cloudflare Workers AI models",
        "What are the latest breaking security updates?",
    ]

    for q in test_queries:
        intent = await boss._analyze_intent(q)
        assert intent["is_live_data"] is True, f"Failed to detect is_live_data for query: '{q}'"


@pytest.mark.asyncio
async def test_live_data_graph_construction():
    """Verify live-data queries construct graph with live-search-specialist and real-time-data-verifier."""
    boss = BossAgent()

    intent = await boss._analyze_intent("What are the latest AI models released today?")
    graph = await boss._build_execution_graph("t_live_graph", "What are the latest AI models released today?", intent)

    assert "live-search-specialist" in graph.nodes
    assert "real-time-data-verifier" in graph.nodes
    assert "fact-checker" in graph.nodes
