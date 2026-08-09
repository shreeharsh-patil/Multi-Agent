import pytest
from unittest.mock import AsyncMock, patch
from src.orchestrator.boss import BossAgent
from src.tools.shopping_tool import ShoppingTool, shopping_tool


@pytest.mark.asyncio
async def test_shopping_intent_classification():
    """Verify shopping queries classify as is_shopping=True and is_live_data=True."""
    boss = BossAgent()
    intent = await boss._analyze_intent("best mouse under 500")

    assert intent["is_shopping"] is True
    assert intent["is_live_data"] is True
    assert intent["shopping_params"]["category"] == "mouse"
    assert intent["shopping_params"]["budget"] == 500.0
    assert intent["shopping_params"]["currency"] == "INR"


def test_shopping_tool_url_verification():
    """Verify ShoppingTool rejects empty URLs and generic marketplace homepages."""
    tool = ShoppingTool()

    assert tool.is_valid_product_url("https://www.amazon.in/dp/B0093H4VBU") is True
    assert tool.is_valid_product_url("https://www.amazon.in/") is False
    assert tool.is_valid_product_url("https://www.flipkart.com") is False
    assert tool.is_valid_product_url("") is False
    assert tool.is_valid_product_url("not_a_url") is False


@pytest.mark.asyncio
async def test_shopping_tool_hard_budget_filter():
    """Verify ShoppingTool filters out products exceeding hard budget constraint."""
    res = await shopping_tool.search_live_products(category="mouse", budget=400.0)

    assert res["success"] is True
    assert res["total_verified"] > 0
    for offer in res["offers"]:
        assert offer["price"] <= 400.0
        assert offer["currency"] == "INR"
        assert tool_is_valid_url(offer["productUrl"])


def tool_is_valid_url(url: str) -> bool:
    return url.startswith("http") and url.rstrip("/") not in {
        "https://www.amazon.in", "https://www.flipkart.com"
    }


@pytest.mark.asyncio
async def test_shopping_anti_hallucination_empty_result():
    """Verify that when no products exist under budget, BossAgent states failure rather than hallucinating."""
    boss = BossAgent()
    mock_search = AsyncMock(return_value={"success": False, "total_verified": 0, "offers": []})
    with patch("src.tools.shopping_tool.shopping_tool.search_live_products", mock_search):
        with patch("src.services.llm.llm_service.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Mocked LLM generation"
            res = await boss.execute_task("mouse under ₹1", user_id="test_user")

    assert res["status"] in ["completed", "partial_success"]
    output = res["output"]
    assert "couldn't verify" in output.lower() or "no verified products" in output.lower()


@pytest.mark.asyncio
async def test_shopping_execution_trace():
    """Verify BossAgent execution trace records shopping retrieval gate events."""
    boss = BossAgent()
    traces = []

    def on_event(event_type, payload):
        traces.append(event_type)

    with patch("src.services.llm.llm_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Mocked LLM generation"
        res = await boss.execute_task("best mouse under 500", user_id="test_user", on_event=on_event)

    assert "shopping_retrieval_started" in traces
    assert "shopping_retrieval_completed" in traces or "shopping_retrieval_failed" in traces
