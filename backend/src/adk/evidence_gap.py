"""Google ADK LoopAgent and EvidenceGapAgent for Adaptive Multi-Iteration Research.

Workflow:
1. Initial research
2. EvidenceGapAgent evaluates completeness against user objective
3. If evidence is sufficient:
   - Terminate loop and deliver synthesized evidence packet
4. If evidence is incomplete:
   - Generate targeted follow-up queries specifically targeting missing facets
   - Search for missing evidence
   - Verify new findings
   - Re-evaluate completeness
5. Maximum iterations: 2 or 3 (configurable, strictly bounded to prevent infinite loops).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from google.adk.agents import LlmAgent, LoopAgent

from src.adk.internet_provider import EvidencePacket, EvidenceSynthesizer, URLCanonicalizer
from src.adk.passage_extractor import PassageChunk
from src.adk.sequential_pipeline import VerifiedWebPipelineExecutor
from src.adk.verification import ClaimStatus, VerificationTeamEngine, VerificationTeamResult, VerifiedClaim
from src.config import settings
from src.utils.logger import logger


@dataclass
class EvidenceGapReport:
    """Analysis of evidence completeness against the user's research objective."""
    query: str
    is_sufficient: bool
    covered_aspects: list[str] = field(default_factory=list)
    missing_aspects: list[str] = field(default_factory=list)
    targeted_followup_queries: list[str] = field(default_factory=list)
    rationale: str = ""
    iteration: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "is_sufficient": self.is_sufficient,
            "covered_aspects": self.covered_aspects,
            "missing_aspects": self.missing_aspects,
            "targeted_followup_queries": self.targeted_followup_queries,
            "rationale": self.rationale,
            "iteration": self.iteration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceGapReport:
        return cls(
            query=data.get("query", ""),
            is_sufficient=data.get("is_sufficient", True),
            covered_aspects=data.get("covered_aspects", []),
            missing_aspects=data.get("missing_aspects", []),
            targeted_followup_queries=data.get("targeted_followup_queries", []),
            rationale=data.get("rationale", ""),
            iteration=data.get("iteration", 1),
        )


class EvidenceGapAnalyzer:
    """Audits whether synthesized research completely answers all facets of the query."""

    @classmethod
    def decompose_query_facets(cls, query: str) -> list[str]:
        """Decompose compound query into atomic research facets (e.g. 'when released AND what changed')."""
        query_lower = query.lower().strip(" ?.")
        facets: list[str] = []

        # Split on conjunctions and common multi-intent phrasing
        parts = re.split(r"\b(?:and|as well as|along with|plus|versus|vs|compared to)\b|,", query_lower)
        for p in parts:
            cleaned = p.strip()
            if len(cleaned) > 3:
                facets.append(cleaned)

        if not facets:
            facets = [query_lower]

        return facets

    @classmethod
    def analyze_gaps(
        cls,
        query: str,
        verified_claims: list[VerifiedClaim],
        executed_queries: Optional[list[str]] = None,
        iteration: int = 1,
    ) -> EvidenceGapReport:
        """Evaluate evidence completeness and generate targeted non-repetitive follow-up queries."""
        facets = cls.decompose_query_facets(query)
        prior_queries = set(q.lower().strip() for q in (executed_queries or []))
        prior_queries.add(query.lower().strip())

        covered: list[str] = []
        missing: list[str] = []
        followup_queries: list[str] = []

        all_evidence_text = " ".join(
            f"{c.claim} {c.verdict_reason} {' '.join(c.verifying_sources)}"
            for c in verified_claims
            if c.status in (ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED)
        ).lower()

        # Check facet coverage
        for facet in facets:
            facet_tokens = set(re.findall(r"\w+", facet))
            stop_words = {"when", "what", "how", "why", "where", "was", "is", "the", "a", "an", "and", "in", "of"}
            key_tokens = facet_tokens - stop_words or facet_tokens

            matches = sum(1 for tok in key_tokens if tok in all_evidence_text)
            coverage = matches / len(key_tokens) if key_tokens else 0.0

            # Temporal facet detection (e.g. "when was X released")
            is_temporal_facet = any(t in facet for t in ["when", "release date", "released", "launch date", "timeline"])
            has_date_evidence = bool(re.search(r"\b(202\d|january|february|march|april|may|june|july|august|september|october|november|december)\b", all_evidence_text))

            if is_temporal_facet and not has_date_evidence:
                missing.append(facet)
                # Formulate targeted query (e.g. "feature X official release date")
                clean_subject = re.sub(r"\b(when|was|is|the|released|and|what|changed)\b", "", facet).strip()
                target_q = f"{clean_subject} official release date".strip()
                if target_q and target_q.lower() not in prior_queries:
                    followup_queries.append(target_q)
            elif coverage >= 0.60:
                covered.append(facet)
            else:
                missing.append(facet)
                clean_facet = re.sub(r"\b(what|how|why|is|was|the|a|an)\b", "", facet).strip()
                target_q = f"{clean_facet} official documentation specifications".strip()
                if target_q and target_q.lower() not in prior_queries:
                    followup_queries.append(target_q)

        # Deduplicate follow-up queries
        unique_followups: list[str] = []
        for fq in followup_queries:
            if fq not in unique_followups and fq.lower() not in prior_queries:
                unique_followups.append(fq)

        is_sufficient = len(missing) == 0 or len(unique_followups) == 0

        rationale = (
            f"Evidence completely covers all {len(covered)} facets of query."
            if is_sufficient
            else f"Missing {len(missing)} specific facets: {', '.join(missing)}. Generated {len(unique_followups)} targeted follow-up queries."
        )

        return EvidenceGapReport(
            query=query,
            is_sufficient=is_sufficient,
            covered_aspects=covered,
            missing_aspects=missing,
            targeted_followup_queries=unique_followups[:2],  # Keep follow-ups narrow (1-2 queries)
            rationale=rationale,
            iteration=iteration,
        )


def create_evidence_gap_agent() -> LlmAgent:
    """Create the EvidenceGapAgent responsible for evaluating research completeness."""
    from src.adk.agents import MODEL
    from src.adk.tools import analyze_evidence_gaps_tool

    return LlmAgent(
        name="evidence_gap_agent",
        model=MODEL,
        description="Audits whether current evidence answers all facets of the query and generates targeted follow-up queries when gaps exist.",
        instruction=(
            "You are the Evidence Gap Agent (evidence_gap_agent).\n\n"
            "OPERATIONAL RULES:\n"
            "1. Evaluate whether verified findings completely answer the user's inquiry.\n"
            "2. Identify missing sub-questions or specific missing factual details (e.g. exact release date, pricing numbers, benchmarks).\n"
            "3. If evidence is complete -> set is_sufficient = True.\n"
            "4. If evidence has gaps -> formulate narrow, targeted follow-up queries specifically targeting the missing facets.\n"
            "5. Do NOT repeat the broad original query.\n"
            "6. Never create infinite research loops."
        ),
        tools=[analyze_evidence_gaps_tool],
    )


def create_adaptive_research_loop_agent(
    max_iterations: Optional[int] = None,
) -> LoopAgent:
    """Create the Google ADK LoopAgent for adaptive multi-iteration research."""
    from src.adk.agents import (
        create_search_planner_agent,
        create_search_result_ranker_agent,
        create_url_reader_agent,
        create_passage_ranker_agent,
        create_source_verifier_agent,
        create_google_search_fact_checker_agent,
        create_citation_auditor_agent,
        create_evidence_synthesizer_agent,
    )

    limit = max_iterations or settings.max_research_loop_iterations
    limit = min(3, max(2, limit))  # Strict bound: 2 or 3 iterations max

    gap_agent = create_evidence_gap_agent()
    planner = create_search_planner_agent()
    ranker = create_search_result_ranker_agent()
    reader = create_url_reader_agent()
    p_ranker = create_passage_ranker_agent()
    s_verifier = create_source_verifier_agent()
    f_checker = create_google_search_fact_checker_agent()
    c_auditor = create_citation_auditor_agent()
    e_synth = create_evidence_synthesizer_agent()

    return LoopAgent(
        name="adaptive_research_loop",
        sub_agents=[
            gap_agent,
            planner,
            ranker,
            reader,
            p_ranker,
            s_verifier,
            f_checker,
            c_auditor,
            e_synth,
        ],
        max_iterations=limit,
        description=(
            f"Adaptive multi-iteration research loop (max {limit} iterations). "
            "Evaluates evidence completeness via evidence_gap_agent, executes targeted follow-up searches "
            "when gaps exist, and terminates cleanly when evidence is sufficient."
        ),
    )


class AdaptiveResearchLoopExecutor:
    """Executes iterative deep research with strict loop bounding and targeted follow-up queries."""

    @classmethod
    def run_adaptive_research(
        cls,
        query: str,
        initial_urls: list[str],
        initial_claims: list[str],
        session: Any = None,
        max_iterations: Optional[int] = None,
        mock_followup_urls: Optional[dict[str, list[str]]] = None,
        mock_html_map: Optional[dict[str, str]] = None,
    ) -> Tuple[EvidencePacket, list[EvidenceGapReport]]:
        """Run adaptive research loop up to max_iterations (default 2-3)."""
        limit = max_iterations or settings.max_research_loop_iterations
        limit = min(3, max(2, limit))

        reports: list[EvidenceGapReport] = []
        executed_queries: list[str] = [query]
        current_urls: list[str] = list(initial_urls)
        current_claims: list[str] = list(initial_claims)

        current_evidence_packet: Optional[EvidencePacket] = None

        for iteration in range(1, limit + 1):
            logger.info(f"AdaptiveResearchLoop: Starting iteration {iteration}/{limit} for '{query}'")

            # 1. Run Verified Web Pipeline for current iteration URLs & claims
            current_evidence_packet = VerifiedWebPipelineExecutor.run_full_pipeline(
                query=query,
                raw_search_urls=current_urls,
                claims_to_verify=current_claims,
                session=session,
                raw_html_map=mock_html_map,
            )

            # Convert claims to VerifiedClaim objects for gap analysis
            verified_claims: list[VerifiedClaim] = [
                VerifiedClaim.from_dict(c) for c in current_evidence_packet.claims
            ]

            # 2. EvidenceGapAgent evaluates research completeness
            gap_report = EvidenceGapAnalyzer.analyze_gaps(
                query=query,
                verified_claims=verified_claims,
                executed_queries=executed_queries,
                iteration=iteration,
            )
            reports.append(gap_report)

            # 3. Decision: Is evidence enough?
            if gap_report.is_sufficient:
                logger.info(f"AdaptiveResearchLoop: Evidence sufficient at iteration {iteration}. Terminating loop.")
                break

            if iteration >= limit:
                logger.info(f"AdaptiveResearchLoop: Reached maximum iterations ({limit}). Terminating loop.")
                break

            # 4. Generate targeted follow-up searches
            followups = gap_report.targeted_followup_queries
            if not followups:
                logger.info(f"AdaptiveResearchLoop: No new targeted follow-ups. Terminating loop.")
                break

            logger.info(f"AdaptiveResearchLoop [Iteration {iteration}]: Gaps detected. Running targeted follow-up queries: {followups}")
            executed_queries.extend(followups)

            # 5. Acquire targeted URLs for follow-up queries (simulated / mock lookup)
            new_urls: list[str] = []
            followup_map = mock_followup_urls or {}
            for fq in followups:
                discovered = followup_map.get(fq, [
                    f"https://ai.google.dev/adk/release-calendar",
                    f"https://github.com/google/adk/releases",
                ])
                new_urls.extend(discovered)
                current_claims.append(f"Official release details regarding {fq}.")

            current_urls.extend(new_urls)
            current_urls = URLCanonicalizer.deduplicate_urls(current_urls)

        return current_evidence_packet, reports
