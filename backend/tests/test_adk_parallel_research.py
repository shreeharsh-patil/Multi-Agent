"""Unit tests for Phase 4: Google ADK ParallelAgent Orchestration, Specialist Selection, Concurrency, Timeouts, and 429 Handling."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from google.adk.agents import LlmAgent, ParallelAgent

from src.adk.parallel_research import (
    create_parallel_web_research_agent,
    IndependentSpecialistSelector,
    ParallelWebResearchExecutor,
    INDEPENDENT_SEARCH_SPECIALISTS,
    DEPENDENT_ANALYSIS_SPECIALISTS,
    is_independent_specialist,
)
from src.adk.search_plan import (
    SearchPlan,
    SearchPlanQuery,
    SearchPlanMode,
    IntelligentSearchPlanner,
)
from src.adk.agents import build_all_adk_specialists
from src.config import settings


def test_create_parallel_web_research_agent_is_real_adk_parallel_agent():
    """Verify that create_parallel_web_research_agent returns a genuine Google ADK ParallelAgent."""
    specialists = [
        LlmAgent(name="google_search_technology", model="gemini-2.5-flash", instruction="Tech search"),
        LlmAgent(name="official_docs_researcher", model="gemini-2.5-flash", instruction="Docs search"),
        LlmAgent(name="google_news_researcher", model="gemini-2.5-flash", instruction="News search"),
        LlmAgent(name="github_researcher", model="gemini-2.5-flash", instruction="GitHub search"),
    ]
    parallel_agent = create_parallel_web_research_agent(specialists, name="parallel_web_research")

    assert isinstance(parallel_agent, ParallelAgent)
    assert parallel_agent.name == "parallel_web_research"
    assert len(parallel_agent.sub_agents) == 4
    sub_names = {sp.name for sp in parallel_agent.sub_agents}
    assert "google_search_technology" in sub_names
    assert "official_docs_researcher" in sub_names
    assert "google_news_researcher" in sub_names
    assert "github_researcher" in sub_names


def test_example_ecosystem_analysis_parallel_selection():
    """Verify 'Analyse the latest Google ADK ecosystem.' runs targeted independent specialists."""
    prompt = "Analyse the latest Google ADK ecosystem."
    plan = IntelligentSearchPlanner.generate_plan(prompt, mode=SearchPlanMode.DEEP)
    all_specialists = build_all_adk_specialists()

    selected = IndependentSpecialistSelector.select_specialists(plan, all_specialists)

    assert len(selected) >= 2
    assert len(selected) <= 8
    selected_names = {sp.name for sp in selected}

    # Verify independent specialists participate
    assert any(name in INDEPENDENT_SEARCH_SPECIALISTS for name in selected_names)
    # Verify dependent analysis agents are NOT included in initial parallel search
    assert not any(name in DEPENDENT_ANALYSIS_SPECIALISTS for name in selected_names)


def test_independent_vs_dependent_task_filtering():
    """Verify that only independent search specialists are allowed in ParallelAgent."""
    assert is_independent_specialist("google_search_technology") is True
    assert is_independent_specialist("official_docs_researcher") is True
    assert is_independent_specialist("google_news_researcher") is True
    assert is_independent_specialist("github_researcher") is True

    # Dependent tasks must be rejected from first-stage parallel search
    assert is_independent_specialist("url_reader") is False
    assert is_independent_specialist("documentation_reader") is False
    assert is_independent_specialist("search_result_ranker") is False
    assert is_independent_specialist("citation_auditor") is False
    assert is_independent_specialist("contradiction_detector") is False
    assert is_independent_specialist("evidence_synthesizer") is False


def test_specialist_count_bounds_per_mode():
    """Verify SearchPlanner bounds specialist counts: Simple (1), Standard (2-4), Deep (4-8)."""
    # Simple query / QUICK mode -> 1 search agent
    quick_min, quick_max = IndependentSpecialistSelector.get_target_agent_count(SearchPlanMode.QUICK)
    assert quick_min == 1
    assert quick_max == 1

    # Standard query -> 2-4 search agents
    std_min, std_max = IndependentSpecialistSelector.get_target_agent_count(SearchPlanMode.STANDARD)
    assert std_min == 2
    assert std_max == 4

    # Deep query -> 4-8 search agents
    deep_min, deep_max = IndependentSpecialistSelector.get_target_agent_count(SearchPlanMode.DEEP)
    assert deep_min == 4
    assert deep_max == 8


@pytest.mark.asyncio
async def test_parallel_execution_with_concurrency_and_timeout():
    """Verify ParallelWebResearchExecutor handles concurrency limits and per-task timeouts."""
    executor = ParallelWebResearchExecutor(max_concurrency=2, task_timeout=0.1)

    spec1 = LlmAgent(name="google_search_technology", model="gemini-2.5-flash", instruction="Tech")
    spec2 = LlmAgent(name="official_docs_researcher", model="gemini-2.5-flash", instruction="Docs")

    plan = SearchPlan(
        objective="Test concurrency and timeout",
        mode=SearchPlanMode.STANDARD,
        queries=[
            SearchPlanQuery(query="Fast query", purpose="Fast", agent="google_search_technology"),
            SearchPlanQuery(query="Slow query", purpose="Slow", agent="official_docs_researcher"),
        ],
    )

    async def mock_exec(agent: LlmAgent, query: str):
        if "Slow" in query:
            await asyncio.sleep(0.5)  # Triggers timeout
        return {"data": f"Result for {query}"}

    results = await executor.execute_parallel_plan(plan, [spec1, spec2], execution_func=mock_exec)

    assert len(results) == 2
    # Fast query succeeded
    fast_res = next(r for r in results if r["query"] == "Fast query")
    assert fast_res["success"] is True
    assert "data" in fast_res["result"]

    # Slow query timed out gracefully without crashing batch
    slow_res = next(r for r in results if r["query"] == "Slow query")
    assert slow_res["success"] is False
    assert "timed out" in slow_res["error"]


@pytest.mark.asyncio
async def test_parallel_execution_429_rate_limit_backoff():
    """Verify graceful handling of HTTP 429 / ResourceExhausted with exponential backoff and recovery."""
    executor = ParallelWebResearchExecutor(max_concurrency=2, max_retries=2, initial_backoff=0.01)
    spec = LlmAgent(name="google_search_technology", model="gemini-2.5-flash", instruction="Tech")

    plan = SearchPlan(
        objective="Rate limit test",
        mode=SearchPlanMode.QUICK,
        queries=[
            SearchPlanQuery(query="Rate limited query", purpose="Test 429", agent="google_search_technology")
        ],
    )

    call_count = 0

    async def rate_limited_mock(agent: LlmAgent, query: str):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("429 Too Many Requests: ResourceExhausted quota exceeded")
        return {"data": "Recovered successfully after backoff"}

    results = await executor.execute_parallel_plan(plan, [spec], execution_func=rate_limited_mock)

    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["retries"] == 1
    assert results[0]["result"]["data"] == "Recovered successfully after backoff"
    assert call_count == 2
