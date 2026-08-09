import pytest
from src.orchestrator.boss import BossAgent


@pytest.mark.asyncio
async def test_latest_information_flags():
    """Verify latest information triggers is_live_data flag in BossAgent intent analysis."""
    boss = BossAgent()

    test_queries = [
        "What is the latest open source LLM?",
        "Current price of Nvidia RTX 4090",
        "Latest release of Next.js",
        "Today's tech headlines",
    ]

    for q in test_queries:
        intent = await boss._analyze_intent(q)
        assert intent["is_live_data"] is True, f"Failed for query: {q}"
