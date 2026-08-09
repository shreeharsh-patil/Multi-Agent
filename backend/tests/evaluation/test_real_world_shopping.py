import pytest
from src.orchestrator.boss import BossAgent
from src.agents.metadata import ProductResultObject


@pytest.mark.asyncio
async def test_real_shopping_intent_and_budget():
    """Verify shopping intent analysis extracts category, budget, currency, and country."""
    boss = BossAgent()

    user_query = "Find me the best mouse under ₹500 available in India."
    intent = await boss._analyze_intent(user_query)

    assert intent["is_shopping"] is True
    assert intent["shopping_params"]["category"] == "mouse"
    assert intent["shopping_params"]["budget"] == 500.0
    assert intent["shopping_params"]["currency"] == "INR"
    assert intent["shopping_params"]["country"] == "India"
    assert intent["is_live_data"] is True


def test_shopping_data_contract_fields():
    """Verify ProductResultObject satisfies all Section 3 metadata contract fields."""
    prod = ProductResultObject(
        productName="Logitech M90 Wired Mouse",
        brand="Logitech",
        model="M90",
        price=349.0,
        currency="INR",
        seller="Amazon",
        marketplace="Amazon.in",
        availability="In Stock",
        rating=4.3,
        reviewCount=12500,
        specifications={"DPI": 1000, "Connectivity": "Wired USB"},
        productUrl="https://www.amazon.in/dp/B003L62T7W",
        sourceUrl="https://www.amazon.in/dp/B003L62T7W",
        lastVerified="09 Aug 2026",
        confidence=0.95,
    )

    assert prod.productName == "Logitech M90 Wired Mouse"
    assert prod.price <= 500.0
    assert prod.currency == "INR"
    assert prod.productUrl.startswith("https://")
    assert prod.sourceUrl.startswith("https://")
    assert prod.lastVerified != ""
