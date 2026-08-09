import pytest
from src.agents.metadata import ProductResultObject
from src.orchestrator.boss import TaskMemoryManager, BossAgent


def test_product_result_object_url_fields():
    """Verify ProductResultObject contains productUrl and sourceUrl fields."""
    prod = ProductResultObject(
        productName="Logitech M90 Mouse",
        brand="Logitech",
        price=399.0,
        currency="INR",
        productUrl="https://www.amazon.in/dp/B003L62T7W",
        sourceUrl="https://www.amazon.in/dp/B003L62T7W",
        lastVerified="09 Aug 2026",
    )

    assert prod.productUrl == "https://www.amazon.in/dp/B003L62T7W"
    assert prod.sourceUrl == "https://www.amazon.in/dp/B003L62T7W"
    assert prod.price <= 500.0


@pytest.mark.asyncio
async def test_memory_preserves_sources_and_urls():
    """Verify TaskMemoryManager retains source URLs and product URLs for synthesis."""
    memory = TaskMemoryManager("t_url", "Find mouse under ₹500")

    sources = [
        {"title": "Logitech M90", "url": "https://www.amazon.in/dp/B003L62T7W"},
        {"title": "Dell MS116", "url": "https://www.dell.com/en-in/shop/ms116"},
    ]
    memory.record_result("product-researcher", "Found 2 mice under ₹500", sources=sources)

    assert len(memory.sources) == 2
    assert memory.sources[0]["url"] == "https://www.amazon.in/dp/B003L62T7W"
    assert memory.sources[1]["url"] == "https://www.dell.com/en-in/shop/ms116"
