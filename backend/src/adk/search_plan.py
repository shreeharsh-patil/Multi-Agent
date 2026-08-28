"""Intelligent Search Planner and Search Plan State Management for Google ADK.

Decomposes complex user requests into targeted, non-repetitive search objectives
across specialized Internet Intelligence agents.
Prevents sending identical user prompts to multiple search agents.
Supports configurable search modes: QUICK, STANDARD, DEEP, CRITICAL.
Stores structured search plans in Google ADK Session State.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.config import settings
from src.utils.logger import logger


class SearchPlanMode(str, Enum):
    """Execution depth and verification rigor modes for search planning."""
    QUICK = "QUICK"         # 1-2 focused searches
    STANDARD = "STANDARD"   # 3-5 searches
    DEEP = "DEEP"           # 5-10 multi-angle searches
    CRITICAL = "CRITICAL"   # 8-15 independent verification & contradiction queries


@dataclass
class SearchPlanQuery:
    """A distinct, targeted search query assigned to a specialized agent."""
    query: str
    purpose: str
    agent: str = "google_search_technology"
    priority: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "purpose": self.purpose,
            "agent": self.agent,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchPlanQuery:
        return cls(
            query=data.get("query", ""),
            purpose=data.get("purpose", ""),
            agent=data.get("agent", "google_search_technology"),
            priority=data.get("priority", 10),
        )


@dataclass
class SearchPlan:
    """Structured search plan stored in ADK Session State."""
    objective: str
    mode: SearchPlanMode = SearchPlanMode.STANDARD
    queries: list[SearchPlanQuery] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "mode": self.mode.value if isinstance(self.mode, SearchPlanMode) else str(self.mode),
            "queries": [q.to_dict() for q in self.queries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchPlan:
        mode_val = data.get("mode", SearchPlanMode.STANDARD.value)
        try:
            mode = SearchPlanMode(mode_val.upper())
        except ValueError:
            mode = SearchPlanMode.STANDARD

        queries = [SearchPlanQuery.from_dict(q) for q in data.get("queries", [])]
        return cls(
            objective=data.get("objective", ""),
            mode=mode,
            queries=queries,
        )


class IntelligentSearchPlanner:
    """Generates decomposed multi-angle search plans with strict deduplication and mode limits."""

    @staticmethod
    def get_mode_limits(mode: Union[SearchPlanMode, str]) -> Tuple[int, int]:
        """Fetch configurable query count limits for the given planning mode."""
        if isinstance(mode, str):
            try:
                mode = SearchPlanMode(mode.upper())
            except ValueError:
                mode = SearchPlanMode.STANDARD

        if mode == SearchPlanMode.QUICK:
            return (settings.search_plan_quick_min_queries, settings.search_plan_quick_max_queries)
        elif mode == SearchPlanMode.DEEP:
            return (settings.search_plan_deep_min_queries, settings.search_plan_deep_max_queries)
        elif mode == SearchPlanMode.CRITICAL:
            return (settings.search_plan_critical_min_queries, settings.search_plan_critical_max_queries)
        else:  # STANDARD
            return (settings.search_plan_standard_min_queries, settings.search_plan_standard_max_queries)

    @staticmethod
    def normalize_query_text(query: str) -> str:
        """Normalize query string for exact and near-duplicate matching."""
        if not query:
            return ""
        q = query.lower().strip()
        q = re.sub(r"[^\w\s\.\-\/\+]", " ", q)
        q = re.sub(r"\s+", " ", q).strip()
        return q

    @classmethod
    def deduplicate_queries(cls, queries: list[SearchPlanQuery]) -> list[SearchPlanQuery]:
        """Filter out duplicate and near-identical queries while preserving priority and order."""
        seen_normalized: Set[str] = set()
        deduped: list[SearchPlanQuery] = []

        for item in queries:
            norm = cls.normalize_query_text(item.query)
            if not norm or norm in seen_normalized:
                continue
            seen_normalized.add(norm)
            deduped.append(item)

        return deduped

    @classmethod
    def extract_comparison_entities(cls, prompt: str) -> list[str]:
        """Detect and extract entities from comparison requests (e.g. 'Compare A, B and C')."""
        p = prompt.strip()
        
        # Patterns like: "Compare [latest] A, B and C" or "A vs B vs C" or "difference between A, B and C"
        compare_match = re.search(r"(?i)\b(?:compare|comparison\s+of|difference\s+between)\s+(?:latest\s+|recent\s+)?(.*?)(?:\.|\?|$)", p)
        if compare_match:
            raw_entities = compare_match.group(1).strip()
            # Split by comma, 'and', 'vs', 'versus', '&'
            parts = re.split(r",|\band\b|\bvs\.?\b|\bversus\b|&", raw_entities, flags=re.IGNORECASE)
            entities = [part.strip() for part in parts if part.strip() and len(part.strip()) > 1]
            if len(entities) >= 2:
                # Clean leading noise words like 'the', 'latest'
                cleaned = []
                for e in entities:
                    e_clean = re.sub(r"(?i)^(the|latest|recent|new)\s+", "", e).strip()
                    if e_clean:
                        cleaned.append(e_clean)
                return cleaned

        vs_match = re.search(r"(?i)([a-z0-9_\-\.\s]+)\s+(?:vs\.?|versus)\s+([a-z0-9_\-\.\s]+)(?:\s+(?:vs\.?|versus)\s+([a-z0-9_\-\.\s]+))?", p)
        if vs_match:
            groups = [g.strip() for g in vs_match.groups() if g and g.strip()]
            if len(groups) >= 2:
                return groups

        return []

    @classmethod
    def generate_plan(
        cls,
        user_prompt: str,
        mode: Union[SearchPlanMode, str] = SearchPlanMode.STANDARD,
    ) -> SearchPlan:
        """Decompose user prompt into structured non-repetitive search queries mapped to specialized agents."""
        if isinstance(mode, str):
            try:
                mode = SearchPlanMode(mode.upper())
            except ValueError:
                mode = SearchPlanMode.STANDARD

        min_q, max_q = cls.get_mode_limits(mode)
        entities = cls.extract_comparison_entities(user_prompt)
        prompt_lower = user_prompt.lower()

        candidates: list[SearchPlanQuery] = []

        if entities:
            objective = f"Structured multi-angle comparative research for {', '.join(entities)}"
            
            # 1. Feature queries per entity
            for entity in entities:
                candidates.append(SearchPlanQuery(
                    query=f"{entity} latest official features",
                    purpose=f"Retrieve official feature specifications and current architecture for {entity}",
                    agent="google_search_technology",
                    priority=10,
                ))

            # 2. Pricing queries per entity
            for entity in entities:
                candidates.append(SearchPlanQuery(
                    query=f"{entity} pricing official",
                    purpose=f"Retrieve live official pricing tiers, subscription costs, and enterprise plans for {entity}",
                    agent="price_monitor_researcher",
                    priority=9,
                ))

            # 3. Release and changelog information
            entities_str = " ".join(entities)
            candidates.append(SearchPlanQuery(
                query=f"{entities_str} recent release information",
                purpose="Retrieve recent version releases, changelogs, and breaking updates",
                agent="release_notes_agent",
                priority=8,
            ))

            # 4. Independent comparison & benchmarks
            candidates.append(SearchPlanQuery(
                query=f"{' vs '.join(entities)} recent independent comparison",
                purpose="Gather independent benchmarks, community feedback, and developer comparisons",
                agent="community_researcher",
                priority=8,
            ))

            # 5. Additional deep / critical verification queries
            if mode in (SearchPlanMode.DEEP, SearchPlanMode.CRITICAL):
                for entity in entities:
                    candidates.append(SearchPlanQuery(
                        query=f"{entity} documentation official developer guide",
                        purpose=f"Audit official documentation and developer ecosystem for {entity}",
                        agent="official_docs_researcher",
                        priority=7,
                    ))

            if mode == SearchPlanMode.CRITICAL:
                candidates.append(SearchPlanQuery(
                    query=f"{' '.join(entities)} limitations issues contradictions",
                    purpose="Audit developer complaints, known performance limitations, and conflicting claims",
                    agent="google_search_fact_checker",
                    priority=9,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{' '.join(entities)} security vulnerability CVE compliance",
                    purpose="Verify defensive security advisories, CVE reports, and compliance claims",
                    agent="cybersecurity_researcher",
                    priority=8,
                ))

        else:
            # Single topic or general investigative prompt
            objective = f"Investigate: {user_prompt.strip()}"
            clean_topic = re.sub(r"(?i)^(search for|search the web for|what is|find online|look up|research|find the)\s+", "", user_prompt).strip()

            # 1. Fact-check Search (e.g. "Is Python 4 released?", "Is claim X true?")
            if re.search(r"(?i)^(is|was|did|has|can)\b.*\b(released|true|fake|exist|announced|happen|real)\b", user_prompt) or "fact check" in prompt_lower or "fact-check" in prompt_lower:
                objective = f"Fact-check release and factual status for {clean_topic}"
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official confirmation fact check status",
                    purpose="Verify factual accuracy, check rumor status, and evaluate claim authenticity",
                    agent="google_search_fact_checker",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official release notes roadmap announcements",
                    purpose="Inspect official vendor release notes and authoritative roadmaps",
                    agent="official_docs_researcher",
                    priority=9,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} primary source announcement origin",
                    purpose="Locate primary canonical documentation and authoritative press releases",
                    agent="primary_source_hunter",
                    priority=8,
                ))

            # 2. Multi-source Changes & GitHub Activity (e.g. "Find the latest Google ADK changes")
            elif any(w in prompt_lower for w in ["adk", "github activity", "changes", "changelog", "commit activity"]) and any(w in prompt_lower for w in ["latest", "recent", "find", "new", "adk", "google"]):
                objective = f"Investigate latest changes and activity for {clean_topic}"
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official documentation changelog",
                    purpose="Retrieve official documentation and canonical changelog for the latest changes",
                    agent="official_docs_researcher",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} github repository commits pull requests releases",
                    purpose="Inspect active GitHub repository commits, issues, and release activity",
                    agent="github_researcher",
                    priority=9,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} latest features updates announcements",
                    purpose="Search Google for recent developer announcements and technological changes",
                    agent="google_search_technology",
                    priority=8,
                ))

            # 3. Security Advisory & CVE Research
            elif any(w in prompt_lower for w in ["security advisory", "cve", "vulnerability", "vulnerabilities", "security", "patch advisory", "exploit"]):
                objective = f"Investigate security advisories and vulnerabilities for {clean_topic}"
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} security advisory CVE vulnerability patch",
                    purpose="Retrieve verified CVE records and vendor security advisories",
                    agent="cybersecurity_researcher",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} NIST NVD CERT official vulnerability report",
                    purpose="Verify authoritative vulnerability metrics and CVSS severity",
                    agent="primary_source_hunter",
                    priority=9,
                ))

            # 4. Market / Stock / Company Status Research
            elif any(w in prompt_lower for w in ["company status", "stock", "market", "valuation", "market cap", "earnings"]):
                objective = f"Investigate market and corporate status for {clean_topic}"
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} public financial market status stock price",
                    purpose="Retrieve real-time market data, stock performance, and public valuation",
                    agent="google_search_market",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} corporate developments executive leadership announcements",
                    purpose="Inspect official corporate status, executive leadership, and strategic updates",
                    agent="company_intelligence_agent",
                    priority=9,
                ))

            # 5. Price / Availability / Products
            elif any(w in prompt_lower for w in ["price", "cost", "subscription", "pricing", "buy", "available", "availability"]):
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official pricing plans",
                    purpose="Retrieve authentic public pricing and subscription tiers",
                    agent="price_monitor_researcher",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} availability in stock purchase options",
                    purpose="Check real-time availability, retailer stock, and enterprise packaging",
                    agent="google_search_products",
                    priority=9,
                ))

            # 6. Releases & Versioning
            elif any(w in prompt_lower for w in ["release", "version", "update", "new features", "what's new", "whats new"]):
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official release notes changelog",
                    purpose="Extract release details, version numbers, and changelog updates",
                    agent="release_notes_agent",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} breaking changes migration guide",
                    purpose="Identify breaking architectural changes and migration steps",
                    agent="official_docs_researcher",
                    priority=9,
                ))

            # 7. Documentation & SDKs
            elif any(w in prompt_lower for w in ["doc", "docs", "documentation", "api", "sdk"]):
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official API reference guide",
                    purpose="Extract official API endpoints and SDK documentation",
                    agent="api_documentation_researcher",
                    priority=10,
                ))

            # 8. General technical & news fallback coverage
            else:
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} official documentation",
                    purpose="Retrieve primary source technical specifications and documentation",
                    agent="google_search_technology",
                    priority=9,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} recent developments news",
                    purpose="Retrieve recent news articles and authoritative coverage",
                    agent="google_news_researcher",
                    priority=8,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} practical guide developer tutorial",
                    purpose="Retrieve real-world implementation patterns and best practices",
                    agent="deep_web_researcher",
                    priority=7,
                ))

            if mode in (SearchPlanMode.DEEP, SearchPlanMode.CRITICAL):
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} github open source repository",
                    purpose="Examine open-source implementations and active codebase repositories",
                    agent="github_researcher",
                    priority=7,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} benchmarks performance evaluation",
                    purpose="Retrieve empirical benchmarks and performance evaluations",
                    agent="benchmark_researcher",
                    priority=7,
                ))

            if mode == SearchPlanMode.CRITICAL:
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} primary source verification fact check",
                    purpose="Verify primary sources, author credentials, and validate core claims",
                    agent="source_verifier",
                    priority=10,
                ))
                candidates.append(SearchPlanQuery(
                    query=f"{clean_topic} common issues known bugs drawbacks",
                    purpose="Identify potential contradictions, edge cases, and known limitations",
                    agent="contradiction_detector",
                    priority=8,
                ))

        # Deduplicate candidates
        deduped = cls.deduplicate_queries(candidates)

        # Enforce mode limits
        if len(deduped) > max_q:
            # Sort by priority descending and take top max_q
            sorted_q = sorted(deduped, key=lambda x: x.priority, reverse=True)
            selected = sorted_q[:max_q]
        elif len(deduped) < min_q:
            selected = deduped
        else:
            selected = deduped

        logger.info(
            f"Generated SearchPlan [mode={mode.value}, count={len(selected)}, min={min_q}, max={max_q}] "
            f"for prompt: {user_prompt[:80]}"
        )

        return SearchPlan(
            objective=objective,
            mode=mode,
            queries=selected,
        )


def store_search_plan_in_session(session: Any, plan: SearchPlan) -> None:
    """Store structured search_plan in Google ADK Session State."""
    if session is None:
        return

    plan_dict = plan.to_dict()

    if hasattr(session, "state") and isinstance(session.state, dict):
        session.state["search_plan"] = plan_dict
    elif isinstance(session, dict):
        session["search_plan"] = plan_dict


def get_search_plan_from_session(session: Any) -> Optional[dict[str, Any]]:
    """Retrieve structured search_plan from Google ADK Session State."""
    if session is None:
        return None

    if hasattr(session, "state") and isinstance(session.state, dict):
        return session.state.get("search_plan")
    elif isinstance(session, dict):
        return session.get("search_plan")

    return None
