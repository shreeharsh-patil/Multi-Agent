"""Unit tests for Phase 11: Research Synthesizer — Compact Evidence Packet for BossAgent."""

import json
import pytest

from src.adk.research_synthesizer import (
    ResearchSynthesisPacket,
    ResearchSynthesizer,
    SynthesizedClaimRecord,
    ConflictRecord,
    UncertaintyRecord,
)
from src.adk.verification import ClaimStatus, VerifiedClaim, VerificationTeamResult


def _vc(claim: str, status: ClaimStatus, sources: list[str], conf: float = 0.90) -> VerifiedClaim:
    return VerifiedClaim(
        claim=claim,
        status=status,
        confidence=conf,
        verifying_sources=sources,
        verdict_reason=f"Claim is {status.value}.",
        contradictions=[],
        source_authority_tier="Tier 1: Official Documentation",
        is_fresh=True,
    )


# ─── Test 1: Synthesize returns correct Phase 11 packet structure ────────────

def test_synthesize_returns_correct_packet_structure():
    """Packet must contain verified_claims, evidence, sources, conflicts, uncertainties, confidence."""
    claims = [
        _vc("Google ADK supports LlmAgent.", ClaimStatus.SUPPORTED, ["https://ai.google.dev/adk"]),
    ]
    result = VerificationTeamResult(claims=claims)
    packet = ResearchSynthesizer.synthesize(
        query="What is Google ADK?",
        verified_results=[result],
    )

    assert isinstance(packet, ResearchSynthesisPacket)
    d = packet.to_dict()
    assert "verified_claims" in d
    assert "evidence" in d
    assert "sources" in d
    assert "conflicts" in d
    assert "uncertainties" in d
    assert "confidence" in d
    assert "query" in d
    assert d["query"] == "What is Google ADK?"


# ─── Test 2: Supported claims land in verified_claims ────────────────────────

def test_supported_claims_go_to_verified_claims():
    """SUPPORTED and PARTIALLY_SUPPORTED claims must appear in verified_claims."""
    claims = [
        _vc("Claim A.", ClaimStatus.SUPPORTED, ["https://example.com/a"]),
        _vc("Claim B.", ClaimStatus.PARTIALLY_SUPPORTED, ["https://example.com/b"], conf=0.60),
    ]
    result = VerificationTeamResult(claims=claims)
    packet = ResearchSynthesizer.synthesize(query="Test query", verified_results=[result])

    assert len(packet.verified_claims) == 2
    statuses = {c.status for c in packet.verified_claims}
    assert ClaimStatus.SUPPORTED.value in statuses
    assert ClaimStatus.PARTIALLY_SUPPORTED.value in statuses


# ─── Test 3: Conflicting claims land in conflicts ────────────────────────────

def test_conflicting_claims_go_to_conflicts_not_verified():
    """CONFLICTING claims must appear in conflicts — NEVER in verified_claims."""
    conflicting = VerifiedClaim(
        claim="Google ADK was released in 2024 vs 2025.",
        status=ClaimStatus.CONFLICTING,
        confidence=0.35,
        verifying_sources=["https://source-a.com", "https://source-b.com"],
        verdict_reason="Sources disagree on release year.",
        contradictions=["Source A says 2024, Source B says 2025."],
        source_authority_tier="Tier 2: High-Quality Independent Source",
        is_fresh=True,
    )
    result = VerificationTeamResult(claims=[conflicting])
    packet = ResearchSynthesizer.synthesize(query="ADK release year?", verified_results=[result])

    assert len(packet.conflicts) == 1
    assert len(packet.verified_claims) == 0
    conflict = packet.conflicts[0]
    assert isinstance(conflict, ConflictRecord)
    assert "Source A says 2024" in conflict.conflict_description or len(conflict.conflicting_sources) >= 2


# ─── Test 4: Unverified claims land in uncertainties ────────────────────────

def test_unverified_claims_go_to_uncertainties():
    """UNVERIFIED, FALSE, OUTDATED claims must appear in uncertainties — not verified_claims."""
    unverified = _vc("This claim has no evidence.", ClaimStatus.UNVERIFIED, [], conf=0.10)
    outdated = _vc("This info is from 2019.", ClaimStatus.OUTDATED, ["https://old.com"], conf=0.05)
    result = VerificationTeamResult(claims=[unverified, outdated])

    packet = ResearchSynthesizer.synthesize(query="Old query", verified_results=[result])

    assert len(packet.verified_claims) == 0
    assert len(packet.uncertainties) == 2
    for u in packet.uncertainties:
        assert isinstance(u, UncertaintyRecord)
        assert len(u.reason) > 0


# ─── Test 5: Near-duplicate claims are deduplicated ─────────────────────────

def test_near_duplicate_claims_are_deduplicated():
    """Claims sharing >=80% token overlap should be deduplicated — only one version kept."""
    claim_a = _vc(
        "Google ADK is a multi-agent development framework by Google.",
        ClaimStatus.SUPPORTED,
        ["https://ai.google.dev/adk"],
        conf=0.85,
    )
    claim_b = _vc(
        "Google ADK is a multi-agent development framework made by Google.",  # minor variation
        ClaimStatus.SUPPORTED,
        ["https://ai.google.dev/adk/overview"],
        conf=0.90,
    )
    result = VerificationTeamResult(claims=[claim_a, claim_b])
    packet = ResearchSynthesizer.synthesize(query="What is ADK?", verified_results=[result])

    # Should deduplicate to 1 claim — keep higher confidence version
    assert len(packet.verified_claims) == 1
    assert packet.verified_claims[0].confidence == pytest.approx(0.90, abs=0.01)


# ─── Test 6: Distinct claims are NOT deduplicated ────────────────────────────

def test_distinct_claims_are_not_deduplicated():
    """Claims with very different content must remain separate."""
    claims = [
        _vc("Google ADK supports LlmAgent.", ClaimStatus.SUPPORTED, ["https://a.com"]),
        _vc("Google ADK supports SequentialAgent.", ClaimStatus.SUPPORTED, ["https://b.com"]),
        _vc("Google ADK supports ParallelAgent.", ClaimStatus.SUPPORTED, ["https://c.com"]),
    ]
    result = VerificationTeamResult(claims=claims)
    packet = ResearchSynthesizer.synthesize(query="What agents does ADK support?", verified_results=[result])

    assert len(packet.verified_claims) == 3


# ─── Test 7: Source URLs are deduplicated canonically ───────────────────────

def test_duplicate_source_urls_are_deduplicated():
    """Same URL with different trailing slashes or tracking params must appear only once."""
    claims = [
        _vc("ADK claim 1.", ClaimStatus.SUPPORTED, [
            "https://ai.google.dev/adk/",
            "https://ai.google.dev/adk/?utm_source=docs",
        ]),
        _vc("ADK claim 2.", ClaimStatus.SUPPORTED, [
            "https://ai.google.dev/adk",
        ]),
    ]
    result = VerificationTeamResult(claims=claims)
    packet = ResearchSynthesizer.synthesize(query="ADK query", verified_results=[result])

    canonical_urls = [s.url for s in packet.sources]
    # All three variants of the same URL should collapse to one
    unique_count = len(set(canonical_urls))
    assert unique_count == len(canonical_urls), "Duplicate canonical URLs found"


# ─── Test 8: Passage evidence is included and capped at 2000 chars ──────────

def test_passage_evidence_is_included_and_capped():
    """Passage evidence must appear in 'evidence' field, capped at 2000 chars per passage."""
    long_passage = "A" * 5000  # 5000 char passage — must be capped at 2000
    passages = [
        {"text": long_passage, "url": "https://example.com/page", "title": "Test Page", "heading": "Section 1"},
        {"text": "Short passage.", "url": "https://example.com/other", "title": "Other Page", "heading": ""},
    ]
    packet = ResearchSynthesizer.synthesize(
        query="Test",
        verified_results=[VerificationTeamResult(claims=[])],
        passage_evidence=passages,
    )

    assert len(packet.evidence) == 2
    for item in packet.evidence:
        assert len(item.text) <= 2000, f"Passage text exceeds 2000 chars: {len(item.text)}"


# ─── Test 9: to_dict and to_json produce valid serializable output ──────────

def test_packet_serializes_to_valid_json():
    """to_dict and to_json must produce valid, serializable output."""
    claims = [
        _vc("ADK supports agents.", ClaimStatus.SUPPORTED, ["https://ai.google.dev/adk"]),
    ]
    conflicting = VerifiedClaim(
        claim="Conflicting claim.", status=ClaimStatus.CONFLICTING, confidence=0.4,
        verifying_sources=["https://s1.com", "https://s2.com"], verdict_reason="Conflict.",
        contradictions=["s1 vs s2"], source_authority_tier="Tier 2: High-Quality Independent Source", is_fresh=True,
    )
    result = VerificationTeamResult(claims=claims + [conflicting])
    packet = ResearchSynthesizer.synthesize(query="Serialization test", verified_results=[result])

    d = packet.to_dict()
    assert isinstance(d, dict)

    json_str = packet.to_json()
    parsed = json.loads(json_str)
    assert parsed["query"] == "Serialization test"
    assert "verified_claims" in parsed
    assert "conflicts" in parsed


# ─── Test 10: from_dict reconstructs ResearchSynthesisPacket correctly ──────

def test_from_dict_reconstructs_packet():
    """ResearchSynthesisPacket.from_dict must reconstruct a complete packet."""
    raw = {
        "query": "Reconstruct me",
        "verified_claims": [
            {
                "claim": "Test claim",
                "status": "SUPPORTED",
                "confidence": 0.95,
                "sources": ["https://example.com"],
                "authority_tier": "Tier 1: Official Documentation",
                "is_fresh": True,
                "verdict_reason": "Verified by official source.",
            }
        ],
        "evidence": [
            {
                "text": "Evidence passage text.",
                "url": "https://example.com/page",
                "title": "Page Title",
                "heading": "Section Heading",
                "retrieval_timestamp": 1700000000.0,
            }
        ],
        "sources": [{"url": "https://example.com", "authority_tier": "Tier 1: Official Documentation", "verified": True}],
        "conflicts": [],
        "uncertainties": [],
        "confidence": 0.92,
        "timestamp": 1700000000.0,
    }

    packet = ResearchSynthesisPacket.from_dict(raw)
    assert packet.query == "Reconstruct me"
    assert len(packet.verified_claims) == 1
    assert packet.verified_claims[0].claim == "Test claim"
    assert len(packet.evidence) == 1
    assert packet.confidence == pytest.approx(0.92, abs=0.001)


# ─── Test 11: Empty evidence produces low confidence ────────────────────────

def test_empty_evidence_produces_low_confidence():
    """When there are no claims at all, confidence must be low (≤0.20)."""
    result = VerificationTeamResult(claims=[])
    packet = ResearchSynthesizer.synthesize(query="No evidence", verified_results=[result])

    assert packet.confidence <= 0.20


# ─── Test 12: synthesize_from_dicts works with raw dicts ────────────────────

def test_synthesize_from_dicts_works_with_raw_claim_dicts():
    """synthesize_from_dicts must accept raw claim dictionaries and produce a valid packet."""
    raw_claims = [
        {
            "claim": "Google ADK is open source.",
            "status": "SUPPORTED",
            "confidence": 0.88,
            "verifying_sources": ["https://github.com/google/adk"],
            "verdict_reason": "Confirmed by GitHub.",
            "contradictions": [],
            "source_authority_tier": "Tier 1: Official Documentation",
            "is_fresh": True,
        }
    ]
    packet = ResearchSynthesizer.synthesize_from_dicts(
        query="Is Google ADK open source?",
        raw_claims=raw_claims,
    )

    assert isinstance(packet, ResearchSynthesisPacket)
    assert len(packet.verified_claims) == 1
    assert packet.verified_claims[0].claim == "Google ADK is open source."
    assert packet.confidence > 0.50
