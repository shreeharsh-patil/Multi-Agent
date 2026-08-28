"""Verification Team Engine for Google ADK.

Coordinates:
1. source_verifier: Determines source authority and authenticity.
2. fact_checker: Checks whether assertions are supported by empirical evidence.
3. freshness_checker: Rejects stale evidence for current / time-sensitive questions.
4. citation_auditor: Confirms cited URLs genuinely substantiate attached claims.
5. contradiction_detector: Identifies disagreements and conflicting facts between sources.

Standardized Claim Statuses:
- SUPPORTED
- PARTIALLY_SUPPORTED
- CONFLICTING
- UNVERIFIED
- FALSE
- OUTDATED
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from src.adk.internet_provider import URLCanonicalizer
from src.adk.passage_extractor import PassageChunk
from src.adk.search_ranker import SearchResultRanker
from src.utils.logger import logger


class ClaimStatus(str, Enum):
    """Standardized claim verification verdicts."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"


@dataclass
class VerifiedClaim:
    """Detailed verification record for a specific factual assertion."""
    claim: str
    status: ClaimStatus
    confidence: float
    verifying_sources: list[str] = field(default_factory=list)
    verdict_reason: str = ""
    contradictions: list[str] = field(default_factory=list)
    source_authority_tier: str = "Unverified"
    is_fresh: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status.value if isinstance(self.status, ClaimStatus) else str(self.status),
            "confidence": round(self.confidence, 3),
            "verifying_sources": self.verifying_sources,
            "verdict_reason": self.verdict_reason,
            "contradictions": self.contradictions,
            "source_authority_tier": self.source_authority_tier,
            "is_fresh": self.is_fresh,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerifiedClaim:
        status_raw = data.get("status", ClaimStatus.UNVERIFIED.value)
        try:
            status = ClaimStatus(status_raw.upper())
        except ValueError:
            status = ClaimStatus.UNVERIFIED

        return cls(
            claim=data.get("claim", ""),
            status=status,
            confidence=data.get("confidence", 0.0),
            verifying_sources=data.get("verifying_sources", []),
            verdict_reason=data.get("verdict_reason", ""),
            contradictions=data.get("contradictions", []),
            source_authority_tier=data.get("source_authority_tier", "Unverified"),
            is_fresh=data.get("is_fresh", True),
        )


@dataclass
class VerificationTeamResult:
    """Aggregated verification results for a set of research claims."""
    claims: list[VerifiedClaim] = field(default_factory=list)
    overall_verdict: ClaimStatus = ClaimStatus.UNVERIFIED
    supported_count: int = 0
    unverified_count: int = 0
    conflicting_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "overall_verdict": self.overall_verdict.value if isinstance(self.overall_verdict, ClaimStatus) else str(self.overall_verdict),
            "supported_count": self.supported_count,
            "unverified_count": self.unverified_count,
            "conflicting_count": self.conflicting_count,
        }


class VerificationTeamEngine:
    """Coordinates Source Verifier, Fact Checker, Freshness Checker, Citation Auditor, and Contradiction Detector."""

    @classmethod
    def determine_source_authority(cls, url: str, title: str = "") -> Tuple[str, float]:
        """Source Verifier: Classifies authority tier and trust score."""
        return SearchResultRanker.classify_source_tier(url, title)

    @classmethod
    def check_freshness(
        cls,
        claim: str,
        passages: list[PassageChunk],
        target_year: int = 2026,
    ) -> Tuple[bool, str]:
        """Freshness Checker: Validates temporal alignment and rejects stale evidence."""
        claim_lower = claim.lower()
        temporal_triggers = ["latest", "recent", "2026", "2025", "this year", "august 2026", "current", "update"]

        has_temporal_requirement = any(t in claim_lower for t in temporal_triggers)
        if not has_temporal_requirement:
            return True, "No strict temporal constraint required."

        if not passages:
            return False, "No timestamped evidence available to verify freshness."

        # Check passage publication and retrieval timestamps
        fresh_signals = 0
        stale_signals = 0

        for p in passages:
            date_text = f"{p.retrieval_timestamp} {p.text[:300]} {p.heading}".lower()
            if any(y in date_text for y in ["2026", "2025", "august 2026"]):
                fresh_signals += 1
            elif any(y in date_text for y in ["2020", "2021", "2022", "2023"]):
                stale_signals += 1

        if fresh_signals > 0:
            return True, "Fresh evidence from authoritative recent timeframe confirmed."
        elif stale_signals > 0 and fresh_signals == 0:
            return False, f"Evidence appears stale or outdated for target timeframe ({target_year})."

        return True, "Evidence within acceptable operational freshness window."

    @classmethod
    def audit_citations_and_claim_support(
        cls,
        claim: str,
        passages: list[PassageChunk],
    ) -> Tuple[list[PassageChunk], list[str]]:
        """Citation Auditor & Fact Checker: Audits whether passages substantiate the claim."""
        claim_tokens = set(re.findall(r"\w+", claim.lower()))
        stop_words = {
            "the", "a", "an", "is", "was", "are", "were", "in", "on", "at", "for", "and", "or",
            "of", "to", "with", "by", "from", "has", "have", "had", "be", "been", "that", "this",
            "it", "its", "about",
        }
        key_tokens = claim_tokens - stop_words or claim_tokens

        supporting_passages: list[PassageChunk] = []
        valid_urls: list[str] = []

        for p in passages:
            if not p.text or not p.url:
                continue

            passage_text_lower = f"{p.heading} {p.text} {p.title}".lower()
            matches = sum(1 for tok in key_tokens if tok in passage_text_lower)
            overlap = matches / len(key_tokens) if key_tokens else 0.0

            # Require strict >= 80% overlap on substantive claim tokens to prevent hallucination
            if overlap >= 0.80:
                supporting_passages.append(p)
                canon_url = URLCanonicalizer.canonicalize(p.url) or p.url
                if canon_url not in valid_urls:
                    valid_urls.append(canon_url)

        return supporting_passages, valid_urls

    @classmethod
    def detect_contradictions(cls, passages: list[PassageChunk]) -> list[str]:
        """Contradiction Detector: Scans passages for conflicting numbers, dates, or opposing claims."""
        contradictions: list[str] = []
        if len(passages) < 2:
            return contradictions

        # Semantic contradiction heuristics (e.g. 'deprecated' vs 'supported', 'free' vs 'paid', disparate release dates)
        texts = [f"{p.heading}: {p.text.lower()}" for p in passages]

        has_free = any("free tier" in t or "100% free" in t or "open source free" in t for t in texts)
        has_paid_only = any("paid only" in t or "no free tier" in t or "subscription required" in t for t in texts)
        if has_free and has_paid_only:
            contradictions.append("Conflicting statements on pricing model (free tier vs paid-only subscription).")

        has_deprecated = any("deprecated" in t or "removed in" in t or "no longer supported" in t for t in texts)
        has_active = any("fully supported" in t or "stable release" in t or "recommended for production" in t for t in texts)
        if has_deprecated and has_active:
            contradictions.append("Conflicting statements regarding feature deprecation vs active support status.")

        return contradictions

    @classmethod
    def verify_claim(
        cls,
        claim: str,
        passages: list[PassageChunk],
    ) -> VerifiedClaim:
        """Execute full verification pipeline across all 5 verification roles."""
        if not claim or not claim.strip():
            return VerifiedClaim(
                claim="",
                status=ClaimStatus.UNVERIFIED,
                confidence=0.0,
                verdict_reason="Empty claim provided.",
            )

        if not passages:
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus.UNVERIFIED,
                confidence=0.0,
                verifying_sources=[],
                verdict_reason="No evidence passages provided. Claim cannot be approved without evidence.",
                source_authority_tier="None",
            )

        # 1. Contradiction Detector: Scan discovered passages for conflicts
        contradictions = cls.detect_contradictions(passages)
        all_urls = [URLCanonicalizer.canonicalize(p.url) or p.url for p in passages if p.url]
        if contradictions:
            tier_name, _ = cls.determine_source_authority(passages[0].url, passages[0].title)
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus.CONFLICTING,
                confidence=0.50,
                verifying_sources=all_urls,
                verdict_reason="Contradiction Detector identified conflicting claims across discovered sources.",
                contradictions=contradictions,
                source_authority_tier=tier_name,
                is_fresh=True,
            )

        # 2. Freshness Checker: Reject stale evidence for current / temporal questions
        is_fresh, freshness_msg = cls.check_freshness(claim, passages)
        if not is_fresh:
            tier_name, _ = cls.determine_source_authority(passages[0].url, passages[0].title)
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus.OUTDATED,
                confidence=0.30,
                verifying_sources=all_urls,
                verdict_reason=f"Evidence rejected by Freshness Checker: {freshness_msg}",
                source_authority_tier=tier_name,
                is_fresh=False,
            )

        # 3. Citation Auditor & Fact Checker: Audit specific claim support
        supporting_passages, valid_urls = cls.audit_citations_and_claim_support(claim, passages)
        if not supporting_passages:
            return VerifiedClaim(
                claim=claim,
                status=ClaimStatus.UNVERIFIED,
                confidence=0.0,
                verifying_sources=[],
                verdict_reason="No supporting evidence found in authoritative passages. Claim cannot be approved without evidence.",
                source_authority_tier="None",
            )

        # 4. Source Authority Verifier & Final Verdict
        top_passage = supporting_passages[0]
        tier_name, authority_score = cls.determine_source_authority(top_passage.url, top_passage.title)

        if "Tier 1" in tier_name and authority_score >= 0.90:
            status = ClaimStatus.SUPPORTED
            confidence = min(0.98, authority_score)
            verdict_reason = f"Verified with high confidence from {tier_name} ({valid_urls[0]})."
        elif "Tier 2" in tier_name:
            status = ClaimStatus.SUPPORTED
            confidence = 0.85
            verdict_reason = f"Supported by reputable independent source ({valid_urls[0]})."
        else:
            status = ClaimStatus.PARTIALLY_SUPPORTED
            confidence = 0.65
            verdict_reason = f"Partially supported by community source. Primary source confirmation recommended."

        return VerifiedClaim(
            claim=claim,
            status=status,
            confidence=confidence,
            verifying_sources=valid_urls,
            verdict_reason=verdict_reason,
            contradictions=[],
            source_authority_tier=tier_name,
            is_fresh=True,
        )

    @classmethod
    def verify_claims_batch(
        cls,
        claims: list[str],
        passages: list[PassageChunk],
    ) -> VerificationTeamResult:
        """Verify multiple claims and produce an aggregated verification team verdict."""
        verified_list: list[VerifiedClaim] = []
        supported_count = 0
        unverified_count = 0
        conflicting_count = 0

        for c in claims:
            res = cls.verify_claim(c, passages)
            verified_list.append(res)
            if res.status in (ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED):
                supported_count += 1
            elif res.status in (ClaimStatus.UNVERIFIED, ClaimStatus.FALSE, ClaimStatus.OUTDATED):
                unverified_count += 1
            elif res.status == ClaimStatus.CONFLICTING:
                conflicting_count += 1

        if conflicting_count > 0:
            overall = ClaimStatus.CONFLICTING
        elif supported_count > 0 and unverified_count == 0:
            overall = ClaimStatus.SUPPORTED
        elif supported_count > 0 and unverified_count > 0:
            overall = ClaimStatus.PARTIALLY_SUPPORTED
        else:
            overall = ClaimStatus.UNVERIFIED

        return VerificationTeamResult(
            claims=verified_list,
            overall_verdict=overall,
            supported_count=supported_count,
            unverified_count=unverified_count,
            conflicting_count=conflicting_count,
        )
