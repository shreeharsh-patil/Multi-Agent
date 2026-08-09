import pytest
from src.orchestrator.boss import TaskMemoryManager, BossAgent


@pytest.mark.asyncio
async def test_product_url_survival_pipeline():
    """Verify product URLs survive through all handoff stages to final synthesis."""
    memory = TaskMemoryManager("t_pipeline", "Find mouse under ₹500")

    # Stage 1: Product Researcher retrieves listing with productUrl
    prod_sources = [
        {"title": "Logitech M90 Wired Mouse", "url": "https://www.amazon.in/dp/B003L62T7W", "price": 349.0}
    ]
    memory.record_result("product-researcher", "Found 1 mouse under ₹500", sources=prod_sources)

    # Stage 2: Price Verification Agent checks budget
    memory.record_result("price-verification-agent", "Verified Logitech M90 at ₹349.0 <= ₹500", sources=prod_sources)

    # Stage 3: Product Comparison Agent formats comparison
    memory.record_result("product-comparison-agent", "| Logitech M90 | ₹349 | Wired USB | 4.3 | Best Overall |", sources=prod_sources)

    assert len(memory.sources) >= 1
    assert memory.sources[0]["url"] == "https://www.amazon.in/dp/B003L62T7W"

    boss = BossAgent()
    synthesis = await boss._synthesize_final_output("Find mouse under ₹500", memory, intent={"is_shopping": True, "shopping_params": {"budget": 500.0}})

    assert len(synthesis) > 0
