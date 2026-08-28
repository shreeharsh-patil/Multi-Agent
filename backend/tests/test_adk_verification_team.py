"""Unit tests for Phase 8: Verification Team (source_verifier, fact_checker, freshness_checker, citation_auditor, contradiction_detector)."""

import json
import pytest
from google.adk.agents import LlmAgent

from src.adk.passage_extractor import PassageChunk
from src.adk.verification import (
    ClaimStatus,
    VerifiedClaim,
    VerificationTeamResult,
    VerificationTeamEngine,
)
from src.adk.tools import (
    verify_research_claim,
    verify_research_claim_tool,
)
from src.adk.agents import (
    create_source_verifier_agent,
    create_google_search_fact_checker_agent,
    create_fact_checker_agent,
    create_freshness_checker_agent,
    create_citation_auditor_agent,
    create_contradiction_detector_agent,
)


def test_verification_team_agents_are_real_llm_agents_with_verification_tools():
    """Verify all 5 verification specialists are genuine ADK LlmAgents with appropriate tools."""
    source_ver = create_source_verifier_agent()
    assert isinstance(source_ver, LlmAgent)
    assert source_ver.name == "source_verifier"
    assert verify_research_claim_tool in source_ver.tools
    assert "source authority" in source_ver.instruction.lower()

    fact_chk = create_google_search_fact_checker_agent()
    assert isinstance(fact_chk, LlmAgent)
    assert fact_chk.name == "google_search_fact_checker"
    assert verify_research_claim_tool in fact_chk.tools
    assert "SUPPORTED" in fact_chk.instruction

    fact_chk_alias = create_fact_checker_agent()
    assert isinstance(fact_chk_alias, LlmAgent)

    fresh_chk = create_freshness_checker_agent()
    assert isinstance(fresh_chk, LlmAgent)
    assert fresh_chk.name == "freshness_checker"
    assert verify_research_claim_tool in fresh_chk.tools
    assert "OUTDATED" in fresh_chk.instruction

    cite_aud = create_citation_auditor_agent()
    assert isinstance(cite_aud, LlmAgent)
    assert cite_aud.name == "citation_auditor"
    assert verify_research_claim_tool in cite_aud.tools
    assert "citation hallucination" in cite_aud.instruction.lower()

    contra_det = create_contradiction_detector_agent()
    assert isinstance(contra_det, LlmAgent)
    assert contra_det.name == "contradiction_detector"
    assert verify_research_claim_tool in contra_det.tools
    assert "CONFLICTING" in contra_det.instruction


def test_example_supported_claim_with_official_documentation():
    """Verify claim: 'Google ADK introduced feature X in August 2026' backed by official docs."""
    claim = "Google ADK introduced feature X in August 2026."

    passages = [
        PassageChunk(
            source_id="src_official_1",
            url="https://ai.google.dev/adk/releases/august-2026",
            title="Google ADK August 2026 Release Notes",
            heading="Release Notes - August 2026",
            text="In the August 2026 release, Google ADK introduced feature X to enhance agentic workflow orchestration.",
            retrieval_timestamp="2026-08-28T12:00:00Z",
        )
    ]

    result = VerificationTeamEngine.verify_claim(claim, passages)

    assert isinstance(result, VerifiedClaim)
    assert result.status == ClaimStatus.SUPPORTED
    assert result.confidence >= 0.90
    assert result.verifying_sources == ["https://ai.google.dev/adk/releases/august-2026"]
    assert "Tier 1" in result.source_authority_tier
    assert result.is_fresh is True
    assert "Verified with high confidence" in result.verdict_reason


def test_unverified_claim_without_supporting_evidence():
    """Verify that claims without supporting evidence are marked UNVERIFIED and never approved."""
    claim = "Google ADK supports quantum teleportation protocol in Python 3.14."

    passages = [
        PassageChunk(
            source_id="src_docs_1",
            url="https://ai.google.dev/adk",
            title="Google ADK Overview",
            heading="Overview",
            text="Google ADK provides tools for building hierarchical multi-agent systems in Python.",
            retrieval_timestamp="2026-08-28T12:00:00Z",
        )
    ]

    result = VerificationTeamEngine.verify_claim(claim, passages)

    assert result.status == ClaimStatus.UNVERIFIED
    assert result.confidence == 0.0
    assert len(result.verifying_sources) == 0
    assert "cannot be approved without evidence" in result.verdict_reason


def test_outdated_claim_rejection_for_fresh_question():
    """Freshness Checker: Verify that stale evidence for a current question is marked OUTDATED."""
    claim = "Latest Next.js features in 2026."

    passages = [
        PassageChunk(
            source_id="src_stale_1",
            url="https://nextjs.org/blog/next-11",
            title="Next.js 11 Release",
            heading="Next.js 11 features",
            text="Released in 2021, Next.js 11 features Conformance and Image optimization.",
            retrieval_timestamp="2021-06-15T10:00:00Z",
        )
    ]

    result = VerificationTeamEngine.verify_claim(claim, passages)

    assert result.status == ClaimStatus.OUTDATED
    assert result.is_fresh is False
    assert "rejected by Freshness Checker" in result.verdict_reason


def test_contradiction_detection_between_sources():
    """Contradiction Detector: Verify that conflicting statements between sources mark claim CONFLICTING."""
    claim = "Cursor IDE pricing model."

    passages = [
        PassageChunk(
            source_id="src_source_a",
            url="https://cursor.com/pricing",
            title="Cursor Pricing",
            heading="Subscription Tiers",
            text="Cursor offers a free tier for hobbyists alongside pro plans.",
            retrieval_timestamp="2026-08-28T12:00:00Z",
        ),
        PassageChunk(
            source_id="src_source_b",
            url="https://techblog.com/cursor-review",
            title="Cursor Review",
            heading="Review & Cost",
            text="Cursor is paid only with subscription required after trial.",
            retrieval_timestamp="2026-08-28T12:00:00Z",
        ),
    ]

    result = VerificationTeamEngine.verify_claim(claim, passages)

    assert result.status == ClaimStatus.CONFLICTING
    assert len(result.contradictions) > 0
    assert "pricing model" in result.contradictions[0].lower()


def test_batch_claim_verification_and_tool_json():
    """Verify batch claim verification and verify_research_claim_tool JSON output schema."""
    passages = [
        PassageChunk(
            source_id="src_python_1",
            url="https://docs.python.org/3/whatsnew/3.14.html",
            title="What's New In Python 3.14",
            heading="Python 3.14 Highlights",
            text="Python 3.14 includes support for template string literals and interpreter performance improvements.",
            retrieval_timestamp="2026-08-28T12:00:00Z",
        )
    ]

    passages_json = json.dumps([p.to_dict() for p in passages])

    tool_res_json = verify_research_claim(
        claim="Python 3.14 includes template string literals.",
        passages_json=passages_json,
    )

    data = json.loads(tool_res_json)
    assert data["status"] == "SUPPORTED"
    assert data["confidence"] > 0.8
    assert "https://docs.python.org/3/whatsnew/3.14.html" in data["verifying_sources"]
    assert data["is_fresh"] is True

    # Test batch engine
    batch_res = VerificationTeamEngine.verify_claims_batch(
        claims=[
            "Python 3.14 includes template string literals.",
            "Python 3.14 supports teleportation.",
        ],
        passages=passages,
    )
    assert isinstance(batch_res, VerificationTeamResult)
    assert batch_res.supported_count == 1
    assert batch_res.unverified_count == 1
    assert batch_res.overall_verdict == ClaimStatus.PARTIALLY_SUPPORTED
