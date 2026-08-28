import pytest
from collections import Counter
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from src.agents.metadata import AgentDepartment, AgentMetadata
from src.agents.registry import AgentRegistry
from src.adk.agents import (
    create_boss_agent,
    get_boss_agent,
    get_adk_hierarchy_summary,
    build_all_adk_specialists,
    safe_adk_name,
    adk_name_to_registry_id,
    registry_id_to_adk_name,
    reset_adk_agent_tree,
    SPECIALIST_FACTORIES,
    ADK_TOOL_MAP,
)
from src.adk.runner import (
    get_adk_status,
    _format_agent_trace,
)


@pytest.fixture(autouse=True)
def setup_adk_environment():
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()
    yield
    reset_adk_agent_tree()


EXPECTED_GOOGLE_SEARCH_AGENTS = [
    "google-search-general",
    "google-search-news",
    "google-search-deep-research",
    "google-search-fact-checker",
    "google-search-technology",
    "google-search-academic",
    "google-search-market",
    "google-search-products",
    "google-search-local",
    "google-search-travel",
    "google-search-cybersecurity",
    "google-search-source-verifier",
]


def test_native_google_search_importable():
    """Test 1: google_search can be imported from Google ADK."""
    from google.adk.tools import google_search as gs
    assert gs is not None
    assert "GoogleSearchTool" in type(gs).__name__


def test_every_google_search_specialist_is_real_llm_agent():
    """Test 2: Every Google Search specialist is a real LlmAgent."""
    specialists = build_all_adk_specialists()
    for agent_id in EXPECTED_GOOGLE_SEARCH_AGENTS:
        assert agent_id in specialists, f"Missing specialist {agent_id} in built specialists"
        agent = specialists[agent_id]
        assert isinstance(agent, LlmAgent), f"{agent_id} is not an LlmAgent"
        assert agent.name == safe_adk_name(agent_id)


def test_every_google_search_specialist_uses_isolated_google_search_tool():
    """Test 3 & 16: Every Google Search specialist has google_search tool and does not mix conflicting custom function tools."""
    specialists = build_all_adk_specialists()
    for agent_id in EXPECTED_GOOGLE_SEARCH_AGENTS:
        agent = specialists[agent_id]
        assert len(agent.tools) == 1, f"{agent_id} expected exactly 1 tool, got {len(agent.tools)}"
        tool = agent.tools[0]
        assert tool is google_search or "GoogleSearchTool" in type(tool).__name__


def test_google_search_agents_registered_under_research_department():
    """Test 4: Google Search agents are registered under the Research department in AgentRegistry."""
    for agent_id in EXPECTED_GOOGLE_SEARCH_AGENTS:
        meta = AgentRegistry.get_metadata(agent_id)
        assert meta is not None, f"Metadata for {agent_id} not found in registry"
        assert meta.department == AgentDepartment.RESEARCH, (
            f"{agent_id} department is {meta.department}, expected RESEARCH"
        )
        assert meta.enabled is True
        assert "google-search" in meta.capabilities


def test_google_search_manager_contains_all_12_specialists():
    """Test 5: Google Search Manager contains all 12 search specialists as sub_agents."""
    boss = get_boss_agent()
    research_mgr = next((m for m in boss.sub_agents if m.name == "research_manager"), None)
    assert research_mgr is not None, "research_manager not found under BossAgent"

    gs_mgr = next((s for s in research_mgr.sub_agents if s.name == "google_search_manager"), None)
    assert gs_mgr is not None, "google_search_manager not found under research_manager"
    assert isinstance(gs_mgr, LlmAgent)

    gs_specialist_names = {s.name for s in gs_mgr.sub_agents}
    expected_adk_names = {safe_adk_name(aid) for aid in EXPECTED_GOOGLE_SEARCH_AGENTS}
    assert gs_specialist_names == expected_adk_names, (
        f"Mismatch in google_search_manager sub-agents. Missing: {expected_adk_names - gs_specialist_names}"
    )


def test_research_manager_contains_google_search_manager_and_other_research_agents():
    """Test 6: ResearchManager contains google_search_manager as well as existing scraping/research specialists."""
    boss = get_boss_agent()
    research_mgr = next((m for m in boss.sub_agents if m.name == "research_manager"), None)
    assert research_mgr is not None

    sub_names = {s.name for s in research_mgr.sub_agents}
    assert "google_search_manager" in sub_names
    assert "research" in sub_names
    assert "weather_news" in sub_names
    assert "youtube" in sub_names

    # Verify existing research agent retains web_search_tool and scrape_page_tool
    research_agent = next(s for s in research_mgr.sub_agents if s.name == "research")
    assert len(research_agent.tools) >= 2


def test_boss_agent_reaches_google_search_division():
    """Test 7: BossAgent reaches Google Search agents hierarchically."""
    boss = get_boss_agent()
    assert boss.name == "boss_agent"
    assert len(boss.sub_agents) == 10

    # Path: BossAgent -> research_manager -> google_search_manager -> google_search_news
    research_mgr = next(m for m in boss.sub_agents if m.name == "research_manager")
    gs_mgr = next(s for s in research_mgr.sub_agents if s.name == "google_search_manager")
    news_agent = next(s for s in gs_mgr.sub_agents if s.name == "google_search_news")
    assert news_agent is not None
    assert news_agent.tools == [google_search]


def test_all_adk_names_are_unique():
    """Test 14: All ADK agent names across the entire system are unique."""
    specialists = build_all_adk_specialists()
    names = [s.name for s in specialists.values()]
    names.append("boss_agent")
    names.append("google_search_manager")
    names.extend([
        "command_planning_manager",
        "coding_manager",
        "research_manager",
        "content_manager",
        "visual_manager",
        "data_manager",
        "product_department_manager",
        "ai_ml_manager",
        "automation_manager",
        "business_quality_manager",
    ])
    assert len(names) == len(set(names)), f"Duplicate ADK node names detected: {[k for k, v in Counter(names).items() if v > 1]}"


def test_registry_and_adk_counts_consistency():
    """Test 15: Registry and ADK leaf counts are consistent and include Google Search division."""
    summary = get_adk_hierarchy_summary()
    assert summary["registry_agents"] == 143
    assert summary["adk_specialists"] == 143
    assert summary["google_search_agents"] == 12
    assert summary["department_managers"] == 10
    assert summary["division_managers"] == 1
    assert summary["root_agents"] == 1
    assert summary["total_adk_nodes"] == 155
    assert summary["departments"]["Research"] == 29  # 17 legacy + 12 Google Search


def test_google_search_trace_formatting():
    """Test 20: Google Search Division node tracing and department resolution."""
    trace_mgr = _format_agent_trace("google_search_manager", "ManagerDelegation", True)
    assert trace_mgr["department"] == "Google Search Division"
    assert trace_mgr["name"] == "Google Search Manager"

    trace_tech = _format_agent_trace("google_search_technology", "SearchGroundedEvent", True)
    assert trace_tech["registry_id"] == "google-search-technology"
    assert trace_tech["department"] == "Research"
    assert trace_tech["name"] == "Google Technology Search"

    trace_news = _format_agent_trace("google_search_news", "SearchGroundedEvent", True)
    assert trace_news["registry_id"] == "google-search-news"
    assert trace_news["department"] == "Research"
    assert trace_news["name"] == "Google News Search"


def test_google_search_manager_routing_rules_in_instruction():
    """Test 5 & 8-11: Manager instruction includes all essential query routing rules."""
    boss = get_boss_agent()
    research_mgr = next(m for m in boss.sub_agents if m.name == "research_manager")
    gs_mgr = next(s for s in research_mgr.sub_agents if s.name == "google_search_manager")
    instruction = gs_mgr.instruction

    # Verify key routing rules are present
    assert "google_search_news" in instruction
    assert "google_search_technology" in instruction
    assert "google_search_academic" in instruction
    assert "google_search_fact_checker" in instruction
    assert "google_search_deep_research" in instruction
    assert "google_search_cybersecurity" in instruction
    assert "google_search_local" in instruction
    assert "google_search_travel" in instruction
    assert "google_search_market" in instruction
    assert "google_search_products" in instruction
    assert "google_search_source_verifier" in instruction


def test_google_deep_research_query_planning_workflow():
    """Test 8: Google Deep Research agent implements multi-query decomposition and evidence synthesis."""
    specialists = build_all_adk_specialists()
    deep_agent = specialists["google-search-deep-research"]
    instruction = deep_agent.instruction
    assert "multi-step research workflow" in instruction
    assert "Decompose" in instruction
    assert "synthesize" in instruction.lower()
    assert deep_agent.tools == [google_search]


def test_date_awareness_and_anti_hallucination_instructions():
    """Test 9, 10, 11, 12: Google search agents require fresh searches and strictly forbid source fabrication."""
    specialists = build_all_adk_specialists()
    for aid in EXPECTED_GOOGLE_SEARCH_AGENTS:
        agent = specialists[aid]
        instruction = agent.instruction
        assert "fabricat" in instruction.lower() or "authentic" in instruction.lower() or "verify" in instruction.lower()
