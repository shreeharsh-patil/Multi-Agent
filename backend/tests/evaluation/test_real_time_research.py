import pytest
from src.orchestrator.boss import BossAgent


@pytest.mark.asyncio
async def test_real_time_research_queries():
    """Verify live-data task classification and graph building for time-sensitive queries."""
    boss = BossAgent()

    queries = [
        "What's the latest AI news?",
        "What's the latest AI model?",
        "What is the latest Python version?",
        "What are the current Cloudflare Workers AI image models?",
        "What's the current price of a 1TB SSD?",
    ]

    for query in queries:
        intent = await boss._analyze_intent(query)
        assert intent["is_live_data"] is True, f"Failed for query: {query}"

        graph = await boss._build_execution_graph("t_eval_res", query, intent)
        node_ids = set(graph.nodes.keys())

        # Must include live search, product discovery, or image generation nodes
        assert "live-search-specialist" in node_ids or "product-researcher" in node_ids or "image-generation-agent" in node_ids
