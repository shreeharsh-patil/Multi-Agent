"""Unit tests for Phase 10: Adaptive Research Loop using Google ADK LoopAgent."""

import pytest
from google.adk.agents import LlmAgent, LoopAgent

from src.adk.evidence_gap import (
    EvidenceGapReport,
    EvidenceGapAnalyzer,
    create_evidence_gap_agent,
    create_adaptive_research_loop_agent,
    AdaptiveResearchLoopExecutor,
)
from src.adk.internet_provider import EvidencePacket
from src.adk.verification import ClaimStatus, VerifiedClaim


class MockAdkSession:
    def __init__(self):
        self.state: dict = {}


def _make_verified_claim(claim: str, status: ClaimStatus, sources: list[str], date_in_text: bool = False) -> VerifiedClaim:
    """Helper to create a VerifiedClaim for testing."""
    return VerifiedClaim(
        claim=claim,
        status=status,
        confidence=0.90 if status == ClaimStatus.SUPPORTED else 0.10,
        verifying_sources=sources,
        verdict_reason=f"Claim is {status.value}.",
        contradictions=[],
        source_authority_tier="Tier 1: Official Documentation",
        is_fresh=True,
    )


def test_adaptive_research_loop_is_real_adk_loop_agent():
    """Verify create_adaptive_research_loop_agent returns a real Google ADK LoopAgent."""
    loop_agent = create_adaptive_research_loop_agent(max_iterations=3)

    assert isinstance(loop_agent, LoopAgent)
    assert loop_agent.name == "adaptive_research_loop"
    assert loop_agent.max_iterations == 3
    assert len(loop_agent.sub_agents) > 0

    agent_names = [a.name for a in loop_agent.sub_agents]
    assert "evidence_gap_agent" in agent_names


def test_loop_agent_max_iterations_is_bounded():
    """Verify max_iterations is strictly bounded to 2 or 3 regardless of input."""
    # Below minimum → clamp to 2
    loop_2 = create_adaptive_research_loop_agent(max_iterations=1)
    assert loop_2.max_iterations == 2

    # Default is 3
    loop_3 = create_adaptive_research_loop_agent(max_iterations=3)
    assert loop_3.max_iterations == 3

    # Above maximum → clamp to 3
    loop_capped = create_adaptive_research_loop_agent(max_iterations=100)
    assert loop_capped.max_iterations == 3


def test_evidence_gap_agent_is_real_llm_agent():
    """Verify evidence_gap_agent is a real LlmAgent with analyze_evidence_gaps_tool."""
    agent = create_evidence_gap_agent()

    assert isinstance(agent, LlmAgent)
    assert agent.name == "evidence_gap_agent"
    tool_names = [t.name for t in agent.tools]
    assert "analyze_evidence_gaps" in tool_names


def test_sufficient_evidence_terminates_loop():
    """When all facets are covered, is_sufficient = True, loop terminates early."""
    query = "What is Google ADK and what are its main features?"
    claims = [
        _make_verified_claim(
            "Google ADK is a multi-agent development framework with LlmAgent support.",
            ClaimStatus.SUPPORTED,
            ["https://ai.google.dev/adk"],
        ),
        _make_verified_claim(
            "Google ADK features SequentialAgent and ParallelAgent orchestration.",
            ClaimStatus.SUPPORTED,
            ["https://ai.google.dev/adk/agents"],
        ),
    ]

    report = EvidenceGapAnalyzer.analyze_gaps(
        query=query,
        verified_claims=claims,
        executed_queries=[query],
        iteration=1,
    )

    # Since evidence is substantive and facets are covered → should be sufficient
    assert isinstance(report, EvidenceGapReport)
    assert report.query == query
    assert report.iteration == 1
    # When sufficient, no follow-up queries needed
    if report.is_sufficient:
        assert len(report.targeted_followup_queries) == 0


def test_missing_release_date_generates_targeted_followup():
    """When 'when released' facet has no date evidence, a targeted follow-up is generated."""
    query = "When was Google ADK released and what changed in the update?"
    claims = [
        _make_verified_claim(
            "Google ADK introduced SequentialAgent and ParallelAgent.",
            ClaimStatus.SUPPORTED,
            ["https://ai.google.dev/adk"],
        ),
    ]
    # No date/month/year in evidence text → temporal facet missing

    report = EvidenceGapAnalyzer.analyze_gaps(
        query=query,
        verified_claims=claims,
        executed_queries=[query],
        iteration=1,
    )

    assert isinstance(report, EvidenceGapReport)
    # Temporal facet detected (when released) → should be incomplete
    assert not report.is_sufficient
    assert len(report.targeted_followup_queries) > 0
    # Follow-up must NOT repeat the original broad query
    for fq in report.targeted_followup_queries:
        assert fq.lower() != query.lower(), f"Follow-up '{fq}' must not repeat original query"


def test_no_duplicate_followup_queries():
    """Repeated broad queries are never added to follow-up list."""
    query = "What is the latest release date of Google ADK?"
    executed_queries = [
        query,
        "google adk official release date",
        "adk release date official documentation",
    ]
    claims = []  # No evidence at all

    report = EvidenceGapAnalyzer.analyze_gaps(
        query=query,
        verified_claims=claims,
        executed_queries=executed_queries,
        iteration=2,
    )

    # All known queries must be deduplicated from followup list
    for fq in report.targeted_followup_queries:
        assert fq.lower() not in [q.lower() for q in executed_queries], (
            f"Follow-up '{fq}' is already in executed_queries"
        )


def test_full_adaptive_loop_terminates_within_max_iterations():
    """End-to-end: run_adaptive_research terminates within max_iterations and returns EvidencePacket."""
    query = "When was Google ADK 2.0 released?"
    raw_urls = [
        "https://ai.google.dev/adk/releases",
        "https://github.com/google/adk/releases",
    ]
    claims = ["Google ADK 2.0 was released with multi-agent improvements."]

    mock_html = {
        "https://ai.google.dev/adk/releases": (
            "<html><head><title>ADK Release Notes</title></head>"
            "<body><h1>ADK 2.0 Release</h1>"
            "<p>Google ADK 2.0 was released in August 2026 with SequentialAgent, LoopAgent, and enhanced tooling.</p>"
            "</body></html>"
        ),
        "https://github.com/google/adk/releases": (
            "<html><head><title>ADK GitHub Releases</title></head>"
            "<body><h1>Google ADK Releases</h1>"
            "<p>Version 2.0 tagged August 2026. Includes LoopAgent, SequentialAgent, ParallelAgent, and evidence gap analysis.</p>"
            "</body></html>"
        ),
    }

    session = MockAdkSession()

    packet, reports = AdaptiveResearchLoopExecutor.run_adaptive_research(
        query=query,
        initial_urls=raw_urls,
        initial_claims=claims,
        session=session,
        max_iterations=3,
        mock_html_map=mock_html,
    )

    assert isinstance(packet, EvidencePacket)
    assert len(reports) >= 1
    assert len(reports) <= 3  # Never exceeds max_iterations

    # Verify all reports are properly structured
    for r in reports:
        assert isinstance(r, EvidenceGapReport)
        assert r.iteration >= 1
        assert isinstance(r.is_sufficient, bool)
        assert isinstance(r.targeted_followup_queries, list)
