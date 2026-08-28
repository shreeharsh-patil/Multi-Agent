"""Phase 11: Research Synthesizer — Compact, Grounded Evidence Packet for BossAgent.

Contract:
    BossAgent MUST NOT receive:
    - Complete webpages or raw HTML
    - Full Google Search result dumps
    - Raw unfiltered output from worker agents

BossAgent receives exactly:
    {
        "verified_claims": [...],
        "evidence": [...],
        "sources": [...],
        "conflicts": [...],
        "uncertainties": [...],
        "confidence": 0.95
    }

Rules:
    - Deduplicate repeated claims (semantic and exact).
    - Deduplicate canonical URLs.
    - Preserve full citation provenance.
    - If evidence conflicts, EXPLICITLY include it — do NOT hide conflicts.
    - Boss uses the packet to write the final user response.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.adk.internet_provider import URLCanonicalizer
from src.adk.verification import ClaimStatus, VerifiedClaim, VerificationTeamResult
from src.utils.logger import logger


@dataclass
class SynthesizedClaimRecord:
    """A deduplicated, grounded claim with its canonical citation chain."""
    claim: str
    status: str                     # ClaimStatus value
    confidence: float
    sources: list[str]              # Canonical citation URLs
    authority_tier: str
    is_fresh: bool
    verdict_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "sources": self.sources,
            "authority_tier": self.authority_tier,
            "is_fresh": self.is_fresh,
            "verdict_reason": self.verdict_reason,
        }


@dataclass
class SynthesizedEvidenceItem:
    """A single grounded evidence passage with full provenance."""
    text: str
    url: str
    title: str
    heading: str = ""
    retrieval_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "url": self.url,
            "title": self.title,
            "heading": self.heading,
            "retrieval_timestamp": self.retrieval_timestamp,
        }


@dataclass
class SynthesizedSourceRecord:
    """A deduplicated canonical source with authority metadata."""
    url: str
    authority_tier: str
    verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "authority_tier": self.authority_tier,
            "verified": self.verified,
        }


@dataclass
class ConflictRecord:
    """An explicit conflict between sources — never hidden from BossAgent."""
    claim: str
    conflict_description: str
    conflicting_sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "conflict_description": self.conflict_description,
            "conflicting_sources": self.conflicting_sources,
        }


@dataclass
class UncertaintyRecord:
    """An unverified or ambiguous factual assertion flagged for BossAgent awareness."""
    claim: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "reason": self.reason,
        }


@dataclass
class ResearchSynthesisPacket:
    """The final compact packet delivered exclusively to BossAgent.

    Contains ONLY:
    - verified_claims: supported/partially_supported findings with sources
    - evidence: selected grounded passages with provenance
    - sources: deduplicated canonical URLs with authority tier
    - conflicts: explicit claim conflicts (never hidden)
    - uncertainties: unverified/outdated/false claims flagged
    - confidence: overall calibrated confidence score
    """
    query: str
    verified_claims: list[SynthesizedClaimRecord] = field(default_factory=list)
    evidence: list[SynthesizedEvidenceItem] = field(default_factory=list)
    sources: list[SynthesizedSourceRecord] = field(default_factory=list)
    conflicts: list[ConflictRecord] = field(default_factory=list)
    uncertainties: list[UncertaintyRecord] = field(default_factory=list)
    confidence: float = 0.95
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "verified_claims": [c.to_dict() for c in self.verified_claims],
            "evidence": [e.to_dict() for e in self.evidence],
            "sources": [s.to_dict() for s in self.sources],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "uncertainties": [u.to_dict() for u in self.uncertainties],
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchSynthesisPacket:
        return cls(
            query=data.get("query", ""),
            verified_claims=[
                SynthesizedClaimRecord(**{
                    k: v for k, v in c.items()
                    if k in ("claim", "status", "confidence", "sources", "authority_tier", "is_fresh", "verdict_reason")
                })
                for c in data.get("verified_claims", [])
            ],
            evidence=[
                SynthesizedEvidenceItem(**{
                    k: v for k, v in e.items()
                    if k in ("text", "url", "title", "heading", "retrieval_timestamp")
                })
                for e in data.get("evidence", [])
            ],
            sources=[
                SynthesizedSourceRecord(**s)
                for s in data.get("sources", [])
            ],
            conflicts=[
                ConflictRecord(**c)
                for c in data.get("conflicts", [])
            ],
            uncertainties=[
                UncertaintyRecord(**u)
                for u in data.get("uncertainties", [])
            ],
            confidence=data.get("confidence", 0.95),
            timestamp=data.get("timestamp", time.time()),
        )


class ResearchSynthesizer:
    """Synthesizes all verified worker outputs into a compact, grounded ResearchSynthesisPacket.

    Rules enforced:
    1. No raw HTML, no complete pages, no full Google Search dumps — NEVER.
    2. Deduplicate claims semantically (exact + token-level overlap).
    3. Deduplicate canonical source URLs.
    4. Conflicts are EXPLICIT — never hidden from BossAgent.
    5. Unverified / Outdated / False claims become uncertainties.
    6. BossAgent writes the final user response from this packet.
    """

    @classmethod
    def _normalize_claim_text(cls, claim: str) -> str:
        """Normalize a claim string for deduplication comparison."""
        return re.sub(r"\s+", " ", claim.lower().strip().rstrip("."))

    @classmethod
    def _claims_are_duplicate(cls, a: str, b: str, threshold: float = 0.80) -> bool:
        """Return True if two claims share >= threshold token overlap."""
        tokens_a = set(re.findall(r"\w+", a.lower()))
        tokens_b = set(re.findall(r"\w+", b.lower()))
        if not tokens_a or not tokens_b:
            return False
        overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
        return overlap >= threshold

    @classmethod
    def _deduplicate_claims(cls, claims: list[VerifiedClaim]) -> list[VerifiedClaim]:
        """Remove near-duplicate claims, keeping the highest-confidence version."""
        unique: list[VerifiedClaim] = []
        for candidate in claims:
            is_dup = False
            for existing in unique:
                if cls._claims_are_duplicate(candidate.claim, existing.claim):
                    is_dup = True
                    # Prefer higher confidence
                    if candidate.confidence > existing.confidence:
                        unique.remove(existing)
                        unique.append(candidate)
                    break
            if not is_dup:
                unique.append(candidate)
        return unique

    @classmethod
    def _deduplicate_sources(cls, source_records: list[SynthesizedSourceRecord]) -> list[SynthesizedSourceRecord]:
        """Deduplicate by canonical URL."""
        seen: set[str] = set()
        result: list[SynthesizedSourceRecord] = []
        for src in source_records:
            canonical = URLCanonicalizer.canonicalize(src.url) or src.url
            if canonical not in seen:
                seen.add(canonical)
                result.append(SynthesizedSourceRecord(
                    url=canonical,
                    authority_tier=src.authority_tier,
                    verified=src.verified,
                ))
        return result

    @classmethod
    def synthesize(
        cls,
        query: str,
        verified_results: list[VerificationTeamResult],
        passage_evidence: Optional[list[dict[str, Any]]] = None,
    ) -> ResearchSynthesisPacket:
        """Synthesize multiple VerificationTeamResults into a compact ResearchSynthesisPacket.

        Args:
            query: The user's original research question.
            verified_results: One or more VerificationTeamResult objects from verification pipeline stages.
            passage_evidence: Optional list of selected passage dicts with 'text', 'url', 'title', 'heading'.

        Returns:
            ResearchSynthesisPacket ready for BossAgent delivery.
        """
        all_claims: list[VerifiedClaim] = []
        for vr in verified_results:
            all_claims.extend(vr.claims)

        # 1. Deduplicate claims
        unique_claims = cls._deduplicate_claims(all_claims)
        logger.info(f"Synthesizer: {len(all_claims)} raw claims deduplicated to {len(unique_claims)} unique claims")

        # 2. Separate into verified, conflicts, uncertainties
        verified_claim_records: list[SynthesizedClaimRecord] = []
        conflict_records: list[ConflictRecord] = []
        uncertainty_records: list[UncertaintyRecord] = []
        source_records: list[SynthesizedSourceRecord] = []
        seen_source_urls: set[str] = set()

        for vc in unique_claims:
            # Collect sources
            for url in vc.verifying_sources:
                canonical = URLCanonicalizer.canonicalize(url) or url
                if canonical and canonical not in seen_source_urls:
                    seen_source_urls.add(canonical)
                    source_records.append(SynthesizedSourceRecord(
                        url=canonical,
                        authority_tier=vc.source_authority_tier or "Unknown",
                        verified=(vc.status == ClaimStatus.SUPPORTED),
                    ))

            if vc.status in (ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED):
                verified_claim_records.append(SynthesizedClaimRecord(
                    claim=vc.claim,
                    status=vc.status.value,
                    confidence=vc.confidence,
                    sources=list(vc.verifying_sources),
                    authority_tier=vc.source_authority_tier or "Unknown",
                    is_fresh=vc.is_fresh,
                    verdict_reason=vc.verdict_reason,
                ))

            elif vc.status == ClaimStatus.CONFLICTING:
                # EXPLICITLY surface conflicts — never hide them
                conflict_records.append(ConflictRecord(
                    claim=vc.claim,
                    conflict_description="; ".join(vc.contradictions) if vc.contradictions else "Sources contradict each other",
                    conflicting_sources=list(vc.verifying_sources),
                ))

            else:
                # UNVERIFIED, FALSE, OUTDATED → flag as uncertainty
                reason_map = {
                    ClaimStatus.UNVERIFIED: "No authoritative evidence found to support this claim.",
                    ClaimStatus.FALSE: "Authoritative evidence directly refutes this claim.",
                    ClaimStatus.OUTDATED: "Evidence is stale or superseded for this time-sensitive question.",
                }
                uncertainty_records.append(UncertaintyRecord(
                    claim=vc.claim,
                    reason=reason_map.get(vc.status, vc.verdict_reason),
                ))

        # 3. Build evidence items from passage evidence (no raw HTML, no full pages)
        evidence_items: list[SynthesizedEvidenceItem] = []
        for passage in (passage_evidence or []):
            ts_val = passage.get("retrieval_timestamp", time.time())
            try:
                ts_float = float(ts_val)
            except (ValueError, TypeError):
                ts_float = time.time()
            evidence_items.append(SynthesizedEvidenceItem(
                text=str(passage.get("text", ""))[:2000],   # Hard cap at 2000 chars per passage
                url=URLCanonicalizer.canonicalize(str(passage.get("url", ""))) or passage.get("url", ""),
                title=str(passage.get("title", "")),
                heading=str(passage.get("heading", "")),
                retrieval_timestamp=ts_float,
            ))

        # 4. Deduplicate sources
        deduped_sources = cls._deduplicate_sources(source_records)

        # 5. Calibrate overall confidence
        if not unique_claims:
            overall_confidence = 0.10
        else:
            supported = [c for c in unique_claims if c.status in (ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED)]
            conflicting = [c for c in unique_claims if c.status == ClaimStatus.CONFLICTING]
            penalty = len(conflicting) * 0.05 + len(uncertainty_records) * 0.03
            base = sum(c.confidence for c in supported) / len(unique_claims) if unique_claims else 0.0
            overall_confidence = max(0.10, min(0.99, base - penalty))

        packet = ResearchSynthesisPacket(
            query=query,
            verified_claims=verified_claim_records,
            evidence=evidence_items,
            sources=deduped_sources,
            conflicts=conflict_records,
            uncertainties=uncertainty_records,
            confidence=overall_confidence,
        )

        logger.info(
            f"Synthesizer: packet for '{query[:60]}' → "
            f"{len(verified_claim_records)} verified claims, "
            f"{len(conflict_records)} conflicts, "
            f"{len(uncertainty_records)} uncertainties, "
            f"{len(deduped_sources)} sources, "
            f"confidence={overall_confidence:.2f}"
        )
        return packet

    @classmethod
    def synthesize_from_dicts(
        cls,
        query: str,
        raw_claims: list[dict[str, Any]],
        passage_evidence: Optional[list[dict[str, Any]]] = None,
    ) -> ResearchSynthesisPacket:
        """Synthesize from raw claim dictionaries (for tool-based invocation)."""
        from src.adk.verification import VerifiedClaim, VerificationTeamResult
        claims = [VerifiedClaim.from_dict(c) for c in raw_claims]
        fake_result = VerificationTeamResult(claims=claims)
        return cls.synthesize(
            query=query,
            verified_results=[fake_result],
            passage_evidence=passage_evidence,
        )
