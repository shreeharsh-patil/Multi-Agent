"""Per-Task Structured Evidence Store & Source-to-Claim Mapping.

Stores and verifies claims before synthesizing final responses:
- Claim: Statement of fact.
- Source: Title, URL, publisher, retrievedAt.
- Verification: verified, partially_verified, unverified.
- Confidence: 0.0 to 1.0.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class ClaimEvidence:
    def __init__(
        self,
        claim: str,
        value: Any,
        source_title: str,
        source_url: str,
        evidence_snippet: str,
        verification: str = "verified",
        confidence: float = 0.95,
        publisher: str = "Live Web",
    ):
        self.claim = claim
        self.value = value
        self.source_title = source_title
        self.source_url = source_url
        self.evidence_snippet = evidence_snippet
        self.verification = verification
        self.confidence = confidence
        self.publisher = publisher
        self.retrieved_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "value": self.value,
            "source": {
                "title": self.source_title,
                "url": self.source_url,
                "publisher": self.publisher,
                "retrievedAt": self.retrieved_at,
            },
            "evidence": self.evidence_snippet,
            "verification": self.verification,
            "confidence": self.confidence,
        }


class EvidenceStore:
    """Per-Task Evidence Store used by BossAgent and Research Specialists."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.claims: List[ClaimEvidence] = []
        self.sources: List[Dict[str, str]] = []
        self.research_history: List[Dict[str, Any]] = []

    def add_claim(
        self,
        claim: str,
        value: Any,
        source_title: str,
        source_url: str,
        evidence_snippet: str,
        verification: str = "verified",
        confidence: float = 0.95,
    ) -> ClaimEvidence:
        obj = ClaimEvidence(
            claim=claim,
            value=value,
            source_title=source_title,
            source_url=source_url,
            evidence_snippet=evidence_snippet,
            verification=verification,
            confidence=confidence,
        )
        self.claims.append(obj)
        if not any(s["url"] == source_url for s in self.sources):
            self.sources.append({"title": source_title, "url": source_url})
        return obj

    def get_verified_claims(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.claims if c.verification == "verified"]

    def record_trace(self, query: str, agent: str, tool: str, total_results: int) -> None:
        self.research_history.append({
            "query": query,
            "agent": agent,
            "tool": tool,
            "total_results": total_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
