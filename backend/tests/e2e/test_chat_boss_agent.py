import pytest
from unittest.mock import AsyncMock, patch
from src.orchestrator.boss import BossAgent, get_boss_agent
from src.services.freshness_analyzer import freshness_analyzer


@pytest.mark.asyncio
async def test_chat_boss_agent_mouse():
    """Verify shopping query 'Best mouse under ₹500' enters BossAgent orchestrator."""
    boss = get_boss_agent()
    intent = await boss._analyze_intent("Best mouse under ₹500")

    assert intent["is_shopping"] is True
    assert intent["requires_live_data"] is True
    assert intent["shopping_params"]["category"] == "mouse"
    assert intent["shopping_params"]["budget"] == 500.0


@pytest.mark.asyncio
async def test_chat_boss_agent_pcce():
    """Verify institution research query 'PCCE Goa information' enters BossAgent orchestrator."""
    boss = get_boss_agent()
    intent = await boss._analyze_intent("PCCE Goa information")

    assert intent["is_institution_research"] is True
    assert intent["requires_live_data"] is True


@pytest.mark.asyncio
async def test_chat_boss_agent_latest_ai():
    """Verify freshness query 'latest AI models' enters BossAgent orchestrator."""
    boss = get_boss_agent()
    intent = await boss._analyze_intent("latest AI models")

    assert intent["requires_live_data"] is True
    assert intent["freshness"]["research_required"] is True


@pytest.mark.asyncio
async def test_chat_boss_agent_linked_list():
    """Verify educational query 'What is a linked list?' is evaluated by BossAgent decision maker."""
    boss = get_boss_agent()
    intent = await boss._analyze_intent("What is a linked list?")

    assert intent["is_coding"] is True or intent["complexity"] in ["simple", "moderate"]


@pytest.mark.asyncio
async def test_boss_agent_full_task_execution():
    """Verify end-to-end task execution emits boss_received and intent_analyzed events."""
    boss = get_boss_agent()
    events = []

    def on_event(evt, payload):
        events.append(evt)

    with patch("src.services.llm.llm_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Verified product response"
        res = await boss.execute_task("best mouse under 500", user_id="test_user", on_event=on_event)

    assert "boss_received" in events
    assert "intent_analyzed" in events
    assert res["status"] in ["completed", "partial_success"]
