"""Search Result Ranker Engine for Google ADK.

Ranks raw search results according to:
1. Relevance to query intent
2. Primary-source authority (Official Docs > Govt/Regulator > Original Research > Official Company > Official GitHub > Reputable Independent > Community)
3. Freshness and recency
4. Source credibility
5. Source diversity (prevents single-domain saturation)

Partitions results into selected_sources and rejected_sources with concise, non-chain-of-thought justifications.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.adk.internet_provider import URLCanonicalizer
from src.utils.logger import logger


@dataclass
class RankedSource:
    """A prioritized, authoritative source selected for deep extraction."""
    url: str
    title: str
    tier: str
    score: float
    rank_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "tier": self.tier,
            "score": round(self.score, 3),
            "rank_reason": self.rank_reason,
        }


@dataclass
class RejectedSource:
    """A low-signal, redundant, or aggregator source filtered out from extraction."""
    url: str
    title: str
    rejection_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class SearchResultRanking:
    """Structured ranking output complying with ADK ranking requirements."""
    selected_sources: list[dict[str, Any]] = field(default_factory=list)
    rejected_sources: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_sources": self.selected_sources,
            "rejected_sources": self.rejected_sources,
            "reasoning_summary": self.reasoning_summary,
        }


class SearchResultRanker:
    """Evaluates and ranks search results against primary-source hierarchy and query relevance."""

    # Low-quality SEO content farms and scrapers to filter out
    AGGREGATOR_DOMAINS: Set[str] = {
        "geeksforgeeks.org", "w3schools.com", "javatpoint.com",
        "tutorialspoint.com", "simplilearn.com", "educative.io",
        "medium.com", "hashnode.dev", "dev.to", "quora.com",
        "pinterest.com", "linkedin.com", "facebook.com",
    }

    # Authoritative primary source domain patterns
    OFFICIAL_DOCS_DOMAINS: Set[str] = {
        "nextjs.org", "react.dev", "python.org", "ai.google.dev",
        "kubernetes.io", "fastapi.tiangolo.com", "kernel.org",
        "rfc-editor.org", "w3.org", "ietf.org", "whatwg.org",
        "nodejs.org", "typescriptlang.org", "rust-lang.org",
        "golang.org", "go.dev", "pytorch.org", "tensorflow.org",
    }

    GOVERNMENT_DOMAINS: Set[str] = {
        "sec.gov", "cisa.gov", "nist.gov", "fda.gov", "who.int",
        "ftc.gov", "europa.eu", "gov.uk", "gov.in",
    }

    SECURITY_ADVISORY_DOMAINS: Set[str] = {
        "nvd.nist.gov", "cve.org", "cve.mitre.org", "arxiv.org",
        "biorxiv.org", "nature.com", "ieee.org", "acm.org",
        "github.com/advisories", "vulncheck.com", "osv.dev",
    }

    OFFICIAL_COMPANY_DOMAINS: Set[str] = {
        "google.com", "apple.com", "microsoft.com", "anthropic.com",
        "openai.com", "meta.com", "cloudflare.com", "vercel.com",
        "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
    }

    REPUTABLE_INDEPENDENT_DOMAINS: Set[str] = {
        "reuters.com", "bloomberg.com", "techcrunch.com", "theverge.com",
        "wired.com", "arstechnica.com", "bbc.com", "zdnet.com",
        "bleepingcomputer.com", "theregister.com", "krebsonsecurity.com",
    }

    COMMUNITY_DOMAINS: Set[str] = {
        "stackoverflow.com", "reddit.com", "news.ycombinator.com",
    }

    @classmethod
    def classify_source_tier(cls, url: str, title: str = "") -> Tuple[str, float]:
        """Classify URL into authority tier and return (tier_name, base_authority_weight)."""
        if not url:
            return "Tier 3: Community", 0.50

        try:
            parsed = urllib.parse.urlparse(url)
            domain = (parsed.hostname or "").lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            return "Tier 3: Community", 0.50

        # Check CVE / Security Advisories
        if any(sec in url.lower() for sec in ["/advisories", "cve-", "nvd.nist.gov", "cve.org", "osv.dev"]):
            return "Tier 1: Security Advisory / CVE", 0.98

        # Check Government / Regulators
        if domain.endswith(".gov") or domain.endswith(".gov.in") or domain.endswith(".gov.uk") or domain in cls.GOVERNMENT_DOMAINS:
            return "Tier 1: Government / Regulator", 0.98

        # Check Official Documentation
        if domain in cls.OFFICIAL_DOCS_DOMAINS or domain.startswith("docs.") or "/docs/" in url.lower():
            return "Tier 1: Official Documentation", 0.96

        # Check Official Company
        if domain in cls.OFFICIAL_COMPANY_DOMAINS:
            return "Tier 1: Official Company", 0.94

        # Check Official GitHub
        if domain == "github.com":
            return "Tier 1: Official GitHub Repository", 0.92

        # Check Reputable Independent News
        if domain in cls.REPUTABLE_INDEPENDENT_DOMAINS:
            return "Tier 2: Reputable Independent Source", 0.85

        # Check Aggregators / Content Farms
        if domain in cls.AGGREGATOR_DOMAINS or "/blog/" in url.lower():
            return "Tier 3: Secondary Aggregator / Blog", 0.40

        # Check Community
        if domain in cls.COMMUNITY_DOMAINS:
            return "Tier 3: Community Source", 0.60

        return "Tier 2: General Web Source", 0.75

    @classmethod
    def compute_relevance(cls, query: str, title: str, snippet: str = "") -> float:
        """Compute keyword and semantic relevance score between query and result."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.5

        # Filter out common stop words for query overlap
        stop_words = {"what", "is", "the", "latest", "recent", "for", "and", "in", "of", "to", "a", "an"}
        meaningful_tokens = q_tokens - stop_words or q_tokens

        text_lower = f"{title.lower()} {snippet.lower()}"
        matches = sum(1 for token in meaningful_tokens if token in text_lower)
        overlap_ratio = matches / len(meaningful_tokens)

        # Boost if query appears as a contiguous phrase
        phrase_boost = 0.2 if query.lower().strip() in text_lower else 0.0
        return min(1.0, (overlap_ratio * 0.8) + phrase_boost)

    @classmethod
    def rank_sources(
        cls,
        query: str,
        results: list[dict[str, Any]],
        max_selected: int = 5,
    ) -> SearchResultRanking:
        """Rank discovered Google Search results by relevance, primary authority, freshness, credibility, and diversity."""
        if not results:
            return SearchResultRanking(
                selected_sources=[],
                rejected_sources=[],
                reasoning_summary=["No search results provided to rank."],
            )

        scored_candidates: list[RankedSource] = []
        rejected: list[RejectedSource] = []
        domain_counts: dict[str, int] = {}
        seen_canonical_urls: set[str] = set()

        for item in results:
            raw_url = item.get("url", "")
            title = item.get("title", "") or "Untitled Source"
            snippet = item.get("snippet", "") or item.get("description", "")
            published_date = item.get("published_date", "")

            if not raw_url:
                continue

            canon_url = URLCanonicalizer.canonicalize(raw_url) or raw_url
            if canon_url in seen_canonical_urls:
                continue
            seen_canonical_urls.add(canon_url)

            domain = urllib.parse.urlparse(canon_url).netloc.lower().replace("www.", "")

            # 1. Authority & Tier
            tier, authority_score = cls.classify_source_tier(canon_url, title)

            # 2. Relevance
            relevance_score = cls.compute_relevance(query, title, snippet)

            # 3. Freshness Signal
            freshness_boost = 0.05 if (published_date or "2026" in title or "2025" in title or "latest" in title.lower()) else 0.0

            # 4. Composite Score: 40% Authority + 40% Relevance + 15% Credibility + 5% Freshness
            composite_score = (authority_score * 0.40) + (relevance_score * 0.40) + (authority_score * 0.15) + freshness_boost

            # 5. Filter Aggregators & Low Relevance
            if relevance_score < 0.20:
                rejected.append(RejectedSource(
                    url=canon_url,
                    title=title,
                    rejection_reason="Low query relevance to user objective",
                ))
                continue

            if domain in cls.AGGREGATOR_DOMAINS and not ("Tier 1" in tier):
                rejected.append(RejectedSource(
                    url=canon_url,
                    title=title,
                    rejection_reason=f"Secondary aggregator / SEO content farm domain ({domain})",
                ))
                continue

            # Diversity enforcement: Max 2 links per domain
            current_count = domain_counts.get(domain, 0)
            if current_count >= 2:
                rejected.append(RejectedSource(
                    url=canon_url,
                    title=title,
                    rejection_reason=f"Domain diversity cap reached for {domain}",
                ))
                continue

            domain_counts[domain] = current_count + 1

            # Generate concise rank reason
            reason_parts = []
            if "Tier 1" in tier:
                reason_parts.append(f"Authoritative {tier.split(':')[-1].strip()}")
            if relevance_score >= 0.70:
                reason_parts.append("high query relevance")
            if freshness_boost > 0:
                reason_parts.append("recent timestamps")
            rank_reason = ", ".join(reason_parts) or "Relevant contextual source"

            scored_candidates.append(RankedSource(
                url=canon_url,
                title=title,
                tier=tier,
                score=composite_score,
                rank_reason=rank_reason,
            ))

        # Sort selected by composite score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)

        selected = scored_candidates[:max_selected]
        # Any candidates beyond max_selected move to rejected
        overflow = scored_candidates[max_selected:]
        for o in overflow:
            rejected.append(RejectedSource(
                url=o.url,
                title=o.title,
                rejection_reason=f"Ranked below selection threshold (score: {o.score:.2f})",
            ))

        # Generate concise summary without internal chain of thought
        reasoning_summary = [
            f"Prioritized {len(selected)} primary/official sources based on authority, relevance, and diversity.",
            f"Filtered {len(rejected)} secondary blogs, aggregators, and redundant domain entries.",
        ]

        logger.info(
            f"SearchResultRanker ranked {len(results)} items -> {len(selected)} selected, {len(rejected)} rejected"
        )

        return SearchResultRanking(
            selected_sources=[s.to_dict() for s in selected],
            rejected_sources=[r.to_dict() for r in rejected],
            reasoning_summary=reasoning_summary,
        )
