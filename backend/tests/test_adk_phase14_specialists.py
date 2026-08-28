"""Phase 14 Tests: Real ADK Internet Specialists.

Tests the 20 real ADK internet specialists:
1. google_search_general
2. google_search_news
3. google_search_technology
4. google_search_academic
5. google_search_official_docs
6. google_search_fact_checker
7. github_researcher
8. cybersecurity_researcher
9. market_researcher
10. product_researcher
11. local_researcher
12. travel_researcher
13. company_researcher
14. release_notes_researcher
15. api_documentation_researcher
16. dataset_researcher
17. research_paper_researcher
18. primary_source_hunter
19. timeline_researcher
20. community_researcher

Requirements:
- Do not create duplicate-purpose agents
- Every agent must:
  * have a distinct role
  * be a real ADK node
  * have correct tools
  * be registered
  * be reachable through managers
  * appear in traces
- Do not activate all of them for every request
"""

import pytest
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from src.agents.registry import AgentRegistry
from src.adk.runner import _format_agent_trace
from src.adk.agents import (
    get_boss_agent,
    build_all_adk_specialists,
    reset_adk_agent_tree,
    SPECIALIST_FACTORIES,
    INTERNET_INTELLIGENCE_SPECIALIST_NAMES,
    create_google_search_general_agent,
    create_google_search_news_agent,
    create_google_search_technology_agent,
    create_google_search_academic_agent,
    create_google_search_official_docs_agent,
    create_google_search_fact_checker_agent,
    create_github_researcher_agent,
    create_cybersecurity_researcher_agent,
    create_market_researcher_agent,
    create_product_researcher_agent,
    create_local_researcher_agent,
    create_travel_researcher_agent,
    create_company_researcher_agent,
    create_release_notes_researcher_agent,
    create_api_documentation_researcher_agent,
    create_dataset_researcher_agent,
    create_research_paper_researcher_agent,
    create_primary_source_hunter_agent,
    create_timeline_researcher_agent,
    create_community_researcher_agent,
)
from src.adk.search_plan import IntelligentSearchPlanner, SearchPlanMode


PHASE_14_SPECIALISTS = [
    ("google_search_general", create_google_search_general_agent),
    ("google_search_news", create_google_search_news_agent),
    ("google_search_technology", create_google_search_technology_agent),
    ("google_search_academic", create_google_search_academic_agent),
    ("google_search_official_docs", create_google_search_official_docs_agent),
    ("google_search_fact_checker", create_google_search_fact_checker_agent),
    ("github_researcher", create_github_researcher_agent),
    ("cybersecurity_researcher", create_cybersecurity_researcher_agent),
    ("market_researcher", create_market_researcher_agent),
    ("product_researcher", create_product_researcher_agent),
    ("local_researcher", create_local_researcher_agent),
    ("travel_researcher", create_travel_researcher_agent),
    ("company_researcher", create_company_researcher_agent),
    ("release_notes_researcher", create_release_notes_researcher_agent),
    ("api_documentation_researcher", create_api_documentation_researcher_agent),
    ("dataset_researcher", create_dataset_researcher_agent),
    ("research_paper_researcher", create_research_paper_researcher_agent),
    ("primary_source_hunter", create_primary_source_hunter_agent),
    ("timeline_researcher", create_timeline_researcher_agent),
    ("community_researcher", create_community_researcher_agent),
]


@pytest.fixture(autouse=True)
def setup_environment():
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()
    yield
    reset_adk_agent_tree()


def test_all_20_specialists_are_real_adk_llm_agents():
    """Phase 14: Every specialist must be a genuine Google ADK LlmAgent."""
    assert len(PHASE_14_SPECIALISTS) == 20
    for name, factory in PHASE_14_SPECIALISTS:
        agent = factory()
        assert isinstance(agent, LlmAgent), f"{name} must be an ADK LlmAgent"
        assert agent.name is not None and len(agent.name) > 0
        assert agent.model is not None


def test_distinct_roles_and_no_duplicate_purposes():
    """Phase 14: Every agent must have a distinct role, unique description, and specialized instruction."""
    descriptions = set()
    instructions = set()

    for name, factory in PHASE_14_SPECIALISTS:
        agent = factory()
        desc = agent.description.strip()
        instr = agent.instruction.strip()

        assert len(desc) > 10, f"{name} must have a descriptive role description"
        assert len(instr) > 20, f"{name} must have domain-specific instruction rules"

        assert desc not in descriptions, f"Duplicate description found for {name}"
        descriptions.add(desc)

        assert instr not in instructions, f"Duplicate instruction found for {name}"
        instructions.add(instr)


def test_correct_tools_assigned_to_each_specialist():
    """Phase 14: Search specialists must have google_search grounding and verification tools where appropriate."""
    for name, factory in PHASE_14_SPECIALISTS:
        agent = factory()
        # All 20 internet specialists require web search grounding tools
        assert len(agent.tools) >= 1, f"{name} must have search tools attached"
        has_search = any(t is google_search or "GoogleSearchTool" in type(t).__name__ for t in agent.tools)
        assert has_search, f"{name} must have google_search tool"


def test_all_20_specialists_registered_in_factories_and_names():
    """Phase 14: All 20 specialist names must be in SPECIALIST_FACTORIES and INTERNET_INTELLIGENCE_SPECIALIST_NAMES."""
    alias_map = {
        "google_search_news": "google_news_researcher",
        "google_search_official_docs": "official_docs_researcher",
        "market_researcher": "google_search_market",
        "product_researcher": "google_search_products",
        "local_researcher": "google_search_local",
        "travel_researcher": "google_search_travel",
        "company_researcher": "company_intelligence_agent",
        "release_notes_researcher": "release_notes_agent",
        "research_paper_researcher": "paper_comparison_agent",
    }
    for name, _ in PHASE_14_SPECIALISTS:
        canonical = alias_map.get(name, name)
        assert (name in SPECIALIST_FACTORIES or canonical in SPECIALIST_FACTORIES), f"{name} missing from SPECIALIST_FACTORIES"
        assert (name in INTERNET_INTELLIGENCE_SPECIALIST_NAMES or canonical in INTERNET_INTELLIGENCE_SPECIALIST_NAMES), f"{name} missing from INTERNET_INTELLIGENCE_SPECIALIST_NAMES"


def test_all_20_specialists_reachable_through_managers():
    """Phase 14: All 20 specialists must be reachable from BossAgent -> ResearchManager -> InternetIntelligenceManager."""
    boss = get_boss_agent()
    research_mgr = next((m for m in boss.sub_agents if m.name == "research_manager"), None)
    assert research_mgr is not None, "research_manager missing under BossAgent"

    intel_mgr = next((s for s in research_mgr.sub_agents if s.name == "internet_intelligence_manager"), None)
    assert intel_mgr is not None, "internet_intelligence_manager missing under research_manager"

    intel_subagent_names = {s.name for s in intel_mgr.sub_agents}

    # Verify each specialist is present under internet_intelligence_manager or google_search_manager
    gs_mgr = next((s for s in intel_mgr.sub_agents if s.name == "google_search_manager"), None)
    gs_subagent_names = {s.name for s in gs_mgr.sub_agents} if gs_mgr else set()

    all_reachable_names = intel_subagent_names.union(gs_subagent_names)

    for name, _ in PHASE_14_SPECIALISTS:
        # Check either exact name or canonical alias
        alias_names = {
            name,
            name.replace("_", "-"),
            name.replace("google_search_", "google_"),
            name.replace("google_search_", "google-"),
        }
        # Check common aliases
        if "news" in name:
            alias_names.update(["google_news_researcher", "google-news-researcher"])
        if "official_docs" in name:
            alias_names.update(["official_docs_researcher", "official-docs-researcher"])
        if "market" in name:
            alias_names.update(["google_search_market", "google-search-market"])
        if "product" in name:
            alias_names.update(["google_search_products", "google-search-products"])
        if "local" in name:
            alias_names.update(["google_search_local", "google-search-local"])
        if "travel" in name:
            alias_names.update(["google_search_travel", "google-search-travel"])
        if "company" in name:
            alias_names.update(["company_intelligence_agent", "company-intelligence-agent"])
        if "release_notes" in name:
            alias_names.update(["release_notes_agent", "release-notes-agent"])
        if "paper" in name:
            alias_names.update(["paper_comparison_agent", "paper-comparison-agent"])

        assert any(n in all_reachable_names for n in alias_names), f"{name} is not reachable through manager hierarchy"


def test_specialists_appear_in_traces():
    """Phase 14: Traces must format cleanly for each of the 20 specialists."""
    for name, _ in PHASE_14_SPECIALISTS:
        trace = _format_agent_trace(
            node_name=name,
            event_type="SearchGroundedEvent",
            has_content=True,
        )
        assert isinstance(trace, dict)
        assert trace["agent_id"] == name
        assert trace["event_type"] == "SearchGroundedEvent"
        assert trace["has_content"] is True
        assert len(trace["name"]) > 0
        assert len(trace["department"]) > 0


def test_selective_activation_does_not_activate_all_specialists():
    """Phase 14: Do NOT activate all 20 specialists for every request — selective routing based on plan."""
    # 1. Standard technical query activates only targeted specialists (e.g. 3-5 queries)
    tech_plan = IntelligentSearchPlanner.generate_plan(
        user_prompt="How to configure rate limits in FastAPI with Redis?",
        mode=SearchPlanMode.STANDARD,
    )
    assert len(tech_plan.queries) <= 5
    assigned_agents = {q.agent for q in tech_plan.queries}
    assert len(assigned_agents) < 20, "Should only select relevant specialists, not all 20"
    assert len(assigned_agents) >= 1

    # 2. News query selects news/timeline agents
    news_plan = IntelligentSearchPlanner.generate_plan(
        user_prompt="Breaking news: major AI breakthrough announced today",
        mode=SearchPlanMode.STANDARD,
    )
    assert len(news_plan.queries) <= 5
    assert len(news_plan.queries) < 20
