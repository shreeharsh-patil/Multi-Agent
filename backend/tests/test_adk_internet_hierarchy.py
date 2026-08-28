"""Unit tests validating Google ADK Internet Intelligence hierarchy, real ADK LlmAgents, and router rules."""

import pytest
from src.adk.agents import (
    create_web_intent_agent,
    create_freshness_agent,
    create_search_planner_agent,
    create_internet_intelligence_manager,
    create_boss_agent,
    get_adk_hierarchy_summary,
)
from src.agents.registry import AgentRegistry
from src.orchestrator.router import AgentRouter
from google.adk.agents import LlmAgent


def test_adk_planning_agents_are_real_llm_agents():
    """Verify that web_intent_agent, freshness_agent, and search_planner are genuine ADK LlmAgents."""
    web_intent = create_web_intent_agent()
    assert isinstance(web_intent, LlmAgent)
    assert web_intent.name == "web_intent_agent"
    assert "internet access" in web_intent.instruction.lower()
    assert "timeless" in web_intent.instruction.lower()
    assert len(web_intent.tools) == 0  # Does not perform web searches yet

    freshness = create_freshness_agent()
    assert isinstance(freshness, LlmAgent)
    assert freshness.name == "freshness_agent"
    assert "temporal" in freshness.instruction.lower()
    assert "realtime" in freshness.instruction.lower()
    assert len(freshness.tools) == 0  # Does not perform web searches yet

    planner = create_search_planner_agent()
    assert isinstance(planner, LlmAgent)
    assert planner.name == "search_planner"
    assert "research objectives" in planner.instruction.lower()
    assert len(planner.tools) == 0  # Does not perform web searches yet


def test_internet_intelligence_manager_hierarchy():
    """Verify that InternetIntelligenceManager is a real ADK LlmAgent coordinating the specialists."""
    specialists = [
        create_web_intent_agent(),
        create_freshness_agent(),
        create_search_planner_agent(),
    ]
    manager = create_internet_intelligence_manager(specialists)
    assert isinstance(manager, LlmAgent)
    assert manager.name == "internet_intelligence_manager"
    assert len(manager.sub_agents) >= 3

    sub_agent_names = {sp.name for sp in manager.sub_agents}
    assert "web_intent_agent" in sub_agent_names
    assert "freshness_agent" in sub_agent_names
    assert "search_planner" in sub_agent_names


def test_full_hierarchy_includes_internet_intelligence_subsystem():
    """Verify full hierarchical orchestration tree: BossAgent -> ResearchManager -> InternetIntelligenceManager."""
    boss = create_boss_agent()
    assert isinstance(boss, LlmAgent)
    assert boss.name == "boss_agent"

    research_dept = next((sub for sub in boss.sub_agents if sub.name == "research_manager"), None)
    assert research_dept is not None, "research_manager must exist under BossAgent"

    intel_manager = next((sub for sub in research_dept.sub_agents if sub.name == "internet_intelligence_manager"), None)
    assert intel_manager is not None, "internet_intelligence_manager must exist under research_manager"

    sub_names = {sub.name for sub in intel_manager.sub_agents}
    assert "web_intent_agent" in sub_names
    assert "freshness_agent" in sub_names
    assert "search_planner" in sub_names


def test_routing_timeless_programming_questions():
    """Verify that timeless computer science & programming questions route to normal agent with NO web access."""
    router = AgentRouter()

    assert router.route("What is recursion?") == "coding"
    assert router.route("What is OOP?") == "coding"
    assert router.route("Explain linked lists") == "coding"
    assert router.route("How does binary search work?") == "coding"
    assert router.route("Explain polymorphism and inheritance") == "coding"


def test_routing_fresh_and_realtime_questions():
    """Verify that fresh/temporal questions route to research (InternetIntelligenceManager) or weather_news."""
    router = AgentRouter()

    assert router.route("Latest Google ADK update") == "research"
    assert router.route("Latest Next.js release and breaking changes") == "research"
    assert router.route("Today's breaking news in technology") == "research"
    assert router.route("What is the weather in Goa today?") == "weather_news"


def test_routing_explicit_search_questions():
    """Verify that explicit web search requests route to research (InternetIntelligenceManager)."""
    router = AgentRouter()

    assert router.route("Search the web for quantum computing startups") == "research"
    assert router.route("Search google for recent SpaceX launches") == "research"
    assert router.route("Find online the latest python documentation") == "research"
    assert router.route("Look up online AI benchmarks") == "research"
