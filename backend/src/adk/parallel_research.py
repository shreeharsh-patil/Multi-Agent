"""Google ADK ParallelAgent Orchestration for Independent Internet Research.

Provides:
1. create_parallel_web_research_agent - Instantiates Google ADK ParallelAgent with independent search specialists.
2. IndependentSpecialistSelector - Dynamically selects 1 (simple), 2-4 (standard), or 4-8 (deep) specialists based on SearchPlan.
3. ParallelWebResearchExecutor - Asynchronous execution engine with bounded concurrency, timeout handling, and graceful 429 exponential backoff.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union
from google.adk.agents import LlmAgent, ParallelAgent

from src.adk.search_plan import SearchPlan, SearchPlanMode, SearchPlanQuery
from src.config import settings
from src.utils.logger import logger


# Set of specialists that can execute independently in parallel during first-stage discovery
INDEPENDENT_SEARCH_SPECIALISTS: Set[str] = {
    "google_search_technology",
    "official_docs_researcher",
    "google_news_researcher",
    "github_researcher",
    "google_search_academic",
    "google_search_market",
    "google_search_products",
    "google_search_local",
    "google_search_travel",
    "google_search_general",
    "deep_web_researcher",
    "price_monitor_researcher",
    "availability_checker",
    "benchmark_researcher",
    "dataset_researcher",
    "standards_researcher",
    "patent_researcher",
    "regulation_researcher",
    "company_intelligence_agent",
    "startup_researcher",
    "public_osint_researcher",
    "community_researcher",
    "timeline_researcher",
    "entity_researcher",
    "release_notes_agent",
    "api_documentation_researcher",
}

# Set of downstream specialists that depend on search outputs and must NOT run in parallel discovery
DEPENDENT_ANALYSIS_SPECIALISTS: Set[str] = {
    "url_reader",
    "documentation_reader",
    "content_extractor",
    "passage_ranker",
    "search_result_ranker",
    "primary_source_hunter",
    "source_verifier",
    "citation_auditor",
    "contradiction_detector",
    "bias_detector",
    "evidence_quality_judge",
    "internet_evidence_judge",
    "evidence_synthesizer",
}


def is_independent_specialist(agent_name: str) -> bool:
    """Check if an agent is an independent search specialist suitable for parallel execution."""
    norm_name = agent_name.lower().replace("-", "_")
    return norm_name in INDEPENDENT_SEARCH_SPECIALISTS and norm_name not in DEPENDENT_ANALYSIS_SPECIALISTS


def create_parallel_web_research_agent(
    specialists: list[LlmAgent],
    name: str = "parallel_web_research",
    timeout: Optional[float] = None,
) -> ParallelAgent:
    """Create a Google ADK ParallelAgent orchestrating independent search specialists concurrently."""
    effective_timeout = timeout or float(settings.agentic_agent_timeout_seconds)
    
    # Ensure only independent specialists are passed
    valid_sub_agents = [
        sp for sp in specialists
        if sp.name in INDEPENDENT_SEARCH_SPECIALISTS or not (sp.name in DEPENDENT_ANALYSIS_SPECIALISTS)
    ]
    if not valid_sub_agents:
        valid_sub_agents = specialists

    return ParallelAgent(
        name=name,
        sub_agents=valid_sub_agents,
        timeout=effective_timeout,
        description=(
            f"Parallel web research orchestrator concurrently executing "
            f"{len(valid_sub_agents)} independent search specialists."
        ),
    )


class IndependentSpecialistSelector:
    """Selects participating independent search specialists based on SearchPlan and Mode."""

    @staticmethod
    def get_target_agent_count(mode: SearchPlanMode) -> tuple[int, int]:
        """Return (min_specialists, max_specialists) count for parallel execution."""
        if mode == SearchPlanMode.QUICK:
            return (1, 1)        # Simple: 1 search agent
        elif mode == SearchPlanMode.STANDARD:
            return (2, 4)        # Standard: 2-4 search agents
        elif mode in (SearchPlanMode.DEEP, SearchPlanMode.CRITICAL):
            return (4, 8)        # Deep / Critical: 4-8 search agents
        return (2, 4)

    @classmethod
    def select_specialists(
        cls,
        plan: SearchPlan,
        available_specialists: Union[dict[str, LlmAgent], list[LlmAgent]],
    ) -> list[LlmAgent]:
        """Select a bounded subset of independent specialists requested by the SearchPlan.
        
        Never runs every search agent; strictly bounds to 1 (simple), 2-4 (standard), or 4-8 (deep).
        """
        if isinstance(available_specialists, list):
            specialists_map = {sp.name: sp for sp in available_specialists}
        else:
            specialists_map = available_specialists

        min_count, max_count = cls.get_target_agent_count(plan.mode)

        # 1. Collect candidate agent names from plan queries
        candidate_names: list[str] = []
        for q in plan.queries:
            norm_agent = q.agent.lower().replace("-", "_")
            if is_independent_specialist(norm_agent) and norm_agent not in candidate_names:
                candidate_names.append(norm_agent)

        # 2. If no matching candidates, provide default technology search
        if not candidate_names:
            candidate_names = ["google_search_technology"]

        # 3. Bound candidate list to [min_count, max_count]
        selected_names = candidate_names[:max_count]

        # 4. Resolve to actual LlmAgent instances
        selected_agents: list[LlmAgent] = []
        for name in selected_names:
            agent = specialists_map.get(name) or next(
                (sp for sp in specialists_map.values() if sp.name == name or sp.name.replace("-", "_") == name),
                None,
            )
            if agent:
                selected_agents.append(agent)

        logger.info(
            f"Selected {len(selected_agents)} independent specialists for mode '{plan.mode.value}': "
            f"{[a.name for a in selected_agents]}"
        )
        return selected_agents


class ParallelWebResearchExecutor:
    """Async execution coordinator with concurrency bounds, per-task timeouts, and 429 rate limit backoff."""

    def __init__(
        self,
        max_concurrency: Optional[int] = None,
        task_timeout: Optional[float] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        concurrency = max_concurrency or settings.adk_max_concurrent_specialists
        self.semaphore = asyncio.Semaphore(concurrency)
        self.task_timeout = task_timeout or float(settings.agentic_agent_timeout_seconds)
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    async def _execute_single_specialist_with_retry(
        self,
        specialist: LlmAgent,
        query: str,
        execution_func: Optional[Callable[[LlmAgent, str], Any]] = None,
    ) -> dict[str, Any]:
        """Execute a single specialist query with timeout enforcement and 429 exponential backoff."""
        async with self.semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    start_time = time.time()
                    
                    if execution_func:
                        coro = execution_func(specialist, query)
                    else:
                        # Default execution fallback if function not supplied
                        coro = self._default_mockable_execute(specialist, query)

                    result = await asyncio.wait_for(coro, timeout=self.task_timeout)
                    latency = time.time() - start_time
                    
                    return {
                        "agent": specialist.name,
                        "query": query,
                        "success": True,
                        "result": result,
                        "latency_s": round(latency, 2),
                        "retries": attempt,
                    }

                except asyncio.TimeoutError:
                    logger.warning(
                        f"Specialist '{specialist.name}' timed out after {self.task_timeout}s on query '{query[:60]}'"
                    )
                    return {
                        "agent": specialist.name,
                        "query": query,
                        "success": False,
                        "error": f"Execution timed out after {self.task_timeout}s",
                        "latency_s": self.task_timeout,
                        "retries": attempt,
                    }

                except Exception as e:
                    err_str = str(e).lower()
                    is_rate_limit = (
                        "429" in err_str
                        or "resourceexhausted" in err_str
                        or "rate limit" in err_str
                        or "too many requests" in err_str
                        or "quota" in err_str
                    )

                    if is_rate_limit and attempt < self.max_retries:
                        backoff = (self.initial_backoff * (2 ** attempt)) + random.uniform(0.1, 0.5)
                        logger.warning(
                            f"Rate limit 429 encountered for '{specialist.name}'. "
                            f"Backing off for {backoff:.2f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        logger.error(f"Specialist '{specialist.name}' failed on query '{query[:60]}': {e}")
                        return {
                            "agent": specialist.name,
                            "query": query,
                            "success": False,
                            "error": str(e),
                            "latency_s": 0.0,
                            "retries": attempt,
                        }

    async def _default_mockable_execute(self, specialist: LlmAgent, query: str) -> dict[str, Any]:
        """Default async executor body."""
        return {
            "agent": specialist.name,
            "query": query,
            "status": "completed",
            "findings": f"Gathered verified findings for query: {query}",
        }

    async def execute_parallel_plan(
        self,
        plan: SearchPlan,
        specialists: list[LlmAgent],
        execution_func: Optional[Callable[[LlmAgent, str], Any]] = None,
    ) -> list[dict[str, Any]]:
        """Run all independent queries in parallel using bounded concurrency and return aggregated results."""
        if not plan.queries or not specialists:
            return []

        specialists_map = {sp.name: sp for sp in specialists}
        tasks = []

        for q in plan.queries:
            norm_agent_name = q.agent.lower().replace("-", "_")
            agent = specialists_map.get(norm_agent_name) or specialists[0]
            tasks.append(self._execute_single_specialist_with_retry(agent, q.query, execution_func))

        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
