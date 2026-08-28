"""Unit tests for Phase 3: ADK Intelligent Search Planning, Modes, Deduplication, and Session State."""

import json
import pytest
from google.adk.agents import LlmAgent

from src.adk.search_plan import (
    SearchPlan,
    SearchPlanQuery,
    SearchPlanMode,
    IntelligentSearchPlanner,
    store_search_plan_in_session,
    get_search_plan_from_session,
)
from src.adk.tools import create_search_plan, create_search_plan_tool
from src.adk.agents import create_search_planner_agent
from src.config import settings


def test_comparison_prompt_decomposition():
    """Verify example prompt 'Compare latest Cursor, Windsurf and GitHub Copilot.' generates required angles."""
    prompt = "Compare latest Cursor, Windsurf and GitHub Copilot."
    plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.DEEP)

    assert isinstance(plan, SearchPlan)
    assert "Cursor" in plan.objective
    assert "Windsurf" in plan.objective
    assert "GitHub Copilot" in plan.objective

    query_texts = [q.query for q in plan.queries]

    # Verify official feature queries per entity
    assert any("Cursor latest official features" in q for q in query_texts)
    assert any("Windsurf latest official features" in q for q in query_texts)
    assert any("GitHub Copilot latest official features" in q for q in query_texts)

    # Verify official pricing queries per entity
    assert any("Cursor pricing official" in q for q in query_texts)
    assert any("Windsurf pricing official" in q for q in query_texts)
    assert any("GitHub Copilot pricing official" in q for q in query_texts)

    # Verify release and independent comparison
    assert any("recent release information" in q for q in query_texts)
    assert any("recent independent comparison" in q for q in query_texts)


def test_structured_search_plan_state_schema():
    """Verify search plan serialization adheres to the exact requested structured state schema."""
    prompt = "Compare latest Cursor, Windsurf and GitHub Copilot."
    plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.STANDARD)
    plan_dict = plan.to_dict()

    assert "objective" in plan_dict
    assert "mode" in plan_dict
    assert "queries" in plan_dict
    assert isinstance(plan_dict["queries"], list)

    for item in plan_dict["queries"]:
        assert "query" in item
        assert "purpose" in item
        assert "agent" in item
        assert "priority" in item
        assert isinstance(item["query"], str)
        assert isinstance(item["purpose"], str)
        assert isinstance(item["agent"], str)
        assert isinstance(item["priority"], int)


def test_adk_session_state_storage():
    """Verify structured search_plan stores in and retrieves from ADK session state."""
    class MockADKSession:
        def __init__(self):
            self.state = {}

    session = MockADKSession()
    prompt = "Latest Google ADK release features and migration"
    plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.STANDARD)

    store_search_plan_in_session(session, plan)
    retrieved = get_search_plan_from_session(session)

    assert retrieved is not None
    assert retrieved["objective"] == plan.objective
    assert len(retrieved["queries"]) == len(plan.queries)
    assert retrieved["queries"][0]["query"] == plan.queries[0].query


def test_query_deduplication():
    """Verify query normalization and deduplication prevents redundant searches."""
    raw_queries = [
        SearchPlanQuery(query="Cursor latest official features", purpose="Official features"),
        SearchPlanQuery(query="cursor   latest  official  features", purpose="Duplicate check"),
        SearchPlanQuery(query="Cursor latest official features!", purpose="Punctuation check"),
        SearchPlanQuery(query="Cursor pricing official", purpose="Pricing"),
    ]
    deduped = IntelligentSearchPlanner.deduplicate_queries(raw_queries)
    assert len(deduped) == 2
    assert deduped[0].query == "Cursor latest official features"
    assert deduped[1].query == "Cursor pricing official"


def test_search_planning_modes_and_config_limits():
    """Verify mode query counts respect configurable limits from settings."""
    prompt = "Compare latest Cursor, Windsurf and GitHub Copilot."

    # QUICK Mode (1-2 queries)
    quick_plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.QUICK)
    assert settings.search_plan_quick_min_queries <= len(quick_plan.queries) <= settings.search_plan_quick_max_queries
    assert len(quick_plan.queries) <= 2

    # STANDARD Mode (3-5 queries)
    standard_plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.STANDARD)
    assert settings.search_plan_standard_min_queries <= len(standard_plan.queries) <= settings.search_plan_standard_max_queries
    assert len(standard_plan.queries) <= 5

    # DEEP Mode (5-10 queries)
    deep_plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.DEEP)
    assert settings.search_plan_deep_min_queries <= len(deep_plan.queries) <= settings.search_plan_deep_max_queries
    assert len(deep_plan.queries) <= 10

    # CRITICAL Mode (8-15 queries)
    critical_plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.CRITICAL)
    assert settings.search_plan_critical_min_queries <= len(critical_plan.queries) <= settings.search_plan_critical_max_queries
    assert len(critical_plan.queries) <= 15


def test_create_search_plan_tool_invocation():
    """Verify create_search_plan tool executes and returns valid JSON search plan."""
    raw_json = create_search_plan("Compare Cursor and Windsurf", mode="QUICK")
    parsed = json.loads(raw_json)
    assert "objective" in parsed
    assert "queries" in parsed
    assert len(parsed["queries"]) <= 2


def test_search_planner_agent_has_planning_tool_and_instructions():
    """Verify create_search_planner_agent instantiates an LlmAgent equipped with create_search_plan_tool."""
    agent = create_search_planner_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "search_planner"
    assert len(agent.tools) == 1
    assert "NEVER send the identical raw user prompt" in agent.instruction
    assert "QUICK" in agent.instruction
    assert "CRITICAL" in agent.instruction
