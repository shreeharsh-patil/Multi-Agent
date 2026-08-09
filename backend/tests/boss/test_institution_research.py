import pytest
from unittest.mock import AsyncMock, patch
from src.orchestrator.boss import BossAgent
from src.tools.research_tool import InstitutionResearchTool, institution_research_tool


def test_entity_resolution_and_scope():
    """Verify Entity Resolution and Scope Classification."""
    tool = InstitutionResearchTool()

    res = tool.resolve_entity("pcce goa information")
    assert "Padre Conceicao College of Engineering" in res["resolved_entity"]
    assert "Goa" in res["location"]

    scope_general = tool.detect_research_scope("pcce goa information")
    assert scope_general["is_general"] is True

    scope_fees = tool.detect_research_scope("pcce goa fees")
    assert scope_fees["is_specific_only"] is True
    assert scope_fees["fees"] is True


def test_source_hierarchy_categorization():
    """Verify source classification into Level 1 (Official) vs Level 3 (General)."""
    tool = InstitutionResearchTool()

    assert tool.categorize_source("https://pccegoa.org/academics") == "level_1_official"
    assert tool.categorize_source("https://www.goauniversity.ac.in") == "level_1_official"
    assert tool.categorize_source("https://someblog.com/pcce-review") == "level_3_web"


@pytest.mark.asyncio
async def test_institution_research_intent_classification():
    """Verify prompt 'pcce goa information' classifies as is_institution_research=True."""
    boss = BossAgent()
    intent = await boss._analyze_intent("pcce goa information")

    assert intent["is_institution_research"] is True
    assert intent["is_live_data"] is True


@pytest.mark.asyncio
async def test_focused_research_execution():
    """Verify InstitutionResearchTool retrieves live sources and builds claim objects."""
    res = await institution_research_tool.execute_focused_research("pcce goa information")

    assert res["success"] is True
    assert res["total_sources"] > 0
    assert len(res["claims"]) > 0
    assert "Padre Conceicao" in res["entity"]["resolved_entity"]


@pytest.mark.asyncio
async def test_boss_institution_execution_trace():
    """Verify BossAgent execution trace records institution research gate events."""
    boss = BossAgent()
    traces = []

    def on_event(event_type, payload):
        traces.append(event_type)

    with patch("src.services.llm.llm_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Mocked LLM generation"
        res = await boss.execute_task("pcce goa information", user_id="test_user", on_event=on_event)

    assert "institution_research_started" in traces
    assert "institution_research_completed" in traces or "boss_received" in traces
