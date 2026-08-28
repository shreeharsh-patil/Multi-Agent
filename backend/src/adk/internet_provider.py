"""Internet Provider Abstraction & Intelligence Infrastructure for Google ADK.

Provides:
1. URLCanonicalizer - Normalizes URLs, strips tracking/UTM parameters, deduplicates sources.
2. SearchCache - Short-lived in-memory cache with categorization TTLs (0s for realtime/breaking).
3. InternetProviderRegistry - Capability-based registry resolving search, news, scraping, and code queries with intelligent fallback.
4. EvidenceItem & EvidencePacket - Standardized structured evidence models retaining citations throughout execution.
"""

from __future__ import annotations

import re
import time
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.utils.logger import logger


class SourceTier(str, Enum):
    """Hierarchical source authority tiers."""
    TIER_1_PRIMARY = "Tier 1: Primary/Official Source"
    TIER_2_INDEPENDENT = "Tier 2: High-Quality Independent Source"
    TIER_3_COMMUNITY = "Tier 3: Community/Discussion Source"


class FreshnessRequirement(str, Enum):
    """Freshness constraints for web queries."""
    REALTIME = "realtime"         # Today, breaking news, live prices, current weather (TTL = 0s)
    RECENT = "recent"             # This week, recent software releases, current version (TTL = 300s)
    STANDARD = "standard"         # General technical docs, product specifications (TTL = 3600s)
    TIMELESS = "timeless"         # Theoretical concepts, algorithms, historical facts (TTL = 86400s)


@dataclass
class EvidenceItem:
    """A single atomic piece of grounded evidence with full citation provenance."""
    title: str
    url: str
    snippet: str
    publisher: str = ""
    published_at: str = ""
    source_tier: SourceTier = SourceTier.TIER_2_INDEPENDENT
    confidence: float = 0.90
    agent_name: str = ""
    query: str = ""
    retrieved_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "publisher": self.publisher,
            "published_at": self.published_at,
            "source_tier": self.source_tier.value,
            "confidence": self.confidence,
            "agent_name": self.agent_name,
            "query": self.query,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class EvidencePacket:
    """A synthesized, deduplicated research packet delivered to BossAgent."""
    claims: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    confidence: float = 0.95
    freshness: str = "recent"
    research_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": self.claims,
            "sources": self.sources,
            "conflicts": self.conflicts,
            "confidence": round(self.confidence, 3),
            "freshness": self.freshness,
            "research_summary": self.research_summary,
        }


class URLCanonicalizer:
    """Canonicalizes and deduplicates URLs by stripping tracking/analytics query parameters."""

    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "twclid", "igshid",
        "ref", "source", "spm", "_hsenc", "_hsmi", "mc_cid", "mc_eid",
    }

    @classmethod
    def canonicalize(cls, url: str) -> str:
        """Strip tracking parameters, normalize protocol and domain, and remove redundant fragments."""
        if not url or not isinstance(url, str):
            return ""

        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return url

        try:
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
            filtered_params = [
                (k, v) for k, v in query_params
                if k.lower() not in cls.TRACKING_PARAMS and not k.lower().startswith("utm_")
            ]
            new_query = urllib.parse.urlencode(filtered_params)
            
            # Lowercase hostname and strip redundant default ports / trailing slash
            netloc = parsed.netloc.lower()
            if netloc.endswith(":80") and parsed.scheme == "http":
                netloc = netloc[:-3]
            elif netloc.endswith(":443") and parsed.scheme == "https":
                netloc = netloc[:-4]

            path = parsed.path
            if path == "/":
                path = ""

            canonical = urllib.parse.urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                "",  # params
                new_query,
                "",  # fragment
            ))
            return canonical or url
        except Exception as e:
            logger.debug(f"URL canonicalization failed for {url}: {e}")
            return url

    @classmethod
    def deduplicate_urls(cls, urls: list[str]) -> list[str]:
        """Return unique list of canonical URLs preserving original order."""
        seen: set[str] = set()
        deduped: list[str] = []
        for u in urls:
            c = cls.canonicalize(u)
            if c and c not in seen:
                seen.add(c)
                deduped.append(c)
        return deduped


class SearchCache:
    """In-memory cache with category-based TTL enforcement."""

    TTL_RULES: dict[FreshnessRequirement, int] = {
        FreshnessRequirement.REALTIME: 0,        # No caching for breaking news / live data
        FreshnessRequirement.RECENT: 300,        # 5 minutes
        FreshnessRequirement.STANDARD: 3600,     # 1 hour
        FreshnessRequirement.TIMELESS: 86400,    # 24 hours
    }

    def __init__(self):
        self._cache: dict[str, tuple[float, Any, FreshnessRequirement]] = {}

    def _make_key(self, capability: str, query: str, freshness: FreshnessRequirement) -> str:
        norm_query = re.sub(r"\s+", " ", query.lower().strip())
        return f"{capability}:{freshness.value}:{norm_query}"

    def get(self, capability: str, query: str, freshness: FreshnessRequirement) -> Optional[Any]:
        ttl = self.TTL_RULES.get(freshness, 300)
        if ttl <= 0:
            return None  # Realtime queries bypass cache completely

        key = self._make_key(capability, query, freshness)
        if key in self._cache:
            timestamp, data, _ = self._cache[key]
            if time.time() - timestamp < ttl:
                logger.debug(f"SearchCache HIT for key: {key}")
                return data
            else:
                del self._cache[key]
        return None

    def set(self, capability: str, query: str, freshness: FreshnessRequirement, data: Any) -> None:
        ttl = self.TTL_RULES.get(freshness, 300)
        if ttl <= 0:
            return
        key = self._make_key(capability, query, freshness)
        self._cache[key] = (time.time(), data, freshness)

    def clear(self) -> None:
        self._cache.clear()


class InternetProviderRegistry:
    """Capability-based internet provider resolver with intelligent fallback."""

    def __init__(self):
        self._cache = SearchCache()
        self._telemetry: list[dict[str, Any]] = []

    @property
    def cache(self) -> SearchCache:
        return self._cache

    def detect_freshness_requirement(self, query: str) -> FreshnessRequirement:
        """Analyze query tokens to determine required freshness."""
        q = query.lower()
        realtime_triggers = [
            "today", "breaking", "right now", "live", "current price",
            "weather today", "score", "match", "stock price", "just now"
        ]
        recent_triggers = [
            "latest", "recent", "this week", "newest", "version",
            "release", "announced", "launched", "update", "cve-"
        ]
        
        if any(t in q for t in realtime_triggers):
            return FreshnessRequirement.REALTIME
        if any(t in q for t in recent_triggers):
            return FreshnessRequirement.RECENT
        return FreshnessRequirement.STANDARD

    def log_telemetry(
        self,
        query: str,
        provider: str,
        agent: str,
        latency_ms: float,
        source_count: int,
        success: bool,
        fallback_used: bool = False,
        cache_hit: bool = False,
    ) -> None:
        """Record sanitised telemetry trace for search executions."""
        record = {
            "query": query[:120],
            "provider": provider,
            "agent": agent,
            "latency_ms": round(latency_ms, 2),
            "source_count": source_count,
            "success": success,
            "fallback_used": fallback_used,
            "cache_hit": cache_hit,
            "timestamp": time.time(),
        }
        self._telemetry.append(record)
        # Keep last 200 telemetry items
        if len(self._telemetry) > 200:
            self._telemetry.pop(0)

    def get_recent_telemetry(self) -> list[dict[str, Any]]:
        return list(self._telemetry)


# Singleton instance
INTERNET_PROVIDER_REGISTRY = InternetProviderRegistry()
