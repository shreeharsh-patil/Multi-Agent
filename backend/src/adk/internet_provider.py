"""Internet Provider Abstraction & Intelligence Infrastructure for Google ADK.

Provides:
1. URLCanonicalizer - Normalizes URLs, strips tracking/UTM parameters, deduplicates sources.
2. SearchCache - Short-lived in-memory cache with categorization TTLs (0s for realtime/breaking).
3. InternetProviderRegistry - Capability-based registry resolving search, news, scraping, and code queries with intelligent fallback.
4. EvidenceItem & EvidencePacket - Standardized structured evidence models retaining citations throughout execution.
"""

from __future__ import annotations

import asyncio
import inspect
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


class ResearchScopeMode(str, Enum):
    """Research depth and execution modes."""
    QUICK = "QUICK"               # 1-2 focused searches
    STANDARD = "STANDARD"         # 3-5 searches
    DEEP = "DEEP"                 # 5-12 multi-angle searches
    CRITICAL = "CRITICAL"         # Independent source verification & contradiction checks
    MASSIVE = "MASSIVE"           # Large distributed research team execution


class CitationAuditVerdict(str, Enum):
    """Citation audit verification states."""
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    INACCESSIBLE = "INACCESSIBLE"


@dataclass
class ContradictionItem:
    """Represents a detected contradiction or conflict across sources."""
    claim: str
    source_a: str
    source_b: str
    conflict: str
    likely_resolution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "conflict": self.conflict,
            "likely_resolution": self.likely_resolution,
        }


@dataclass
class EvidenceQualityScore:
    """Multi-dimensional evidence quality scoring."""
    authority: float = 0.9
    freshness: float = 0.9
    directness: float = 0.9
    independence: float = 0.9
    specificity: float = 0.9
    consistency: float = 0.9
    overall_confidence: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority": round(self.authority, 2),
            "freshness": round(self.freshness, 2),
            "directness": round(self.directness, 2),
            "independence": round(self.independence, 2),
            "specificity": round(self.specificity, 2),
            "consistency": round(self.consistency, 2),
            "overall_confidence": round(self.overall_confidence, 2),
        }


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


def sanitize_api_keys(text: str) -> str:
    """Mask API keys, authorization tokens, and credentials from logs and telemetry."""
    if not text or not isinstance(text, str):
        return ""
    # Mask key patterns like AIza..., sk-..., Bearer ..., key=...
    sanitized = re.sub(r"(?i)(key|token|auth|bearer|secret|password)[\s:=]+([A-Za-z0-9_\-\.]{8,})", r"\1=[REDACTED]", text)
    sanitized = re.sub(r"\bAIza[0-9A-Za-z\-_]{35}\b", "[REDACTED_GEMINI_KEY]", sanitized)
    sanitized = re.sub(r"\bsk-[0-9A-Za-z]{20,}\b", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"\bfc-[0-9A-Za-z]{20,}\b", "[REDACTED_FIRECRAWL_KEY]", sanitized)
    return sanitized


@dataclass
class SearchFailoverResult:
    """Standardized search execution result with failover and provenance tracking."""
    query: str
    provider: str                         # "native_google_search", "custom_web_search", or "none"
    fallback_used: bool = False
    failure_reason: Optional[str] = None
    latency_ms: float = 0.0
    source_count: int = 0
    items: list[dict[str, Any]] = field(default_factory=list)
    formatted_output: str = ""
    status: str = "success"                # "success", "fallback", or "no_live_search"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            "failure_reason": self.failure_reason,
            "latency_ms": round(self.latency_ms, 2),
            "source_count": self.source_count,
            "status": self.status,
            "items_count": len(self.items),
        }


class InternetProviderRegistry:
    """Capability-based internet provider resolver with intelligent fallback (Phase 16)."""

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
        failure_reason: Optional[str] = None,
        cache_hit: bool = False,
    ) -> None:
        """Record sanitized telemetry trace for search executions."""
        record = {
            "query": sanitize_api_keys(query[:120]),
            "provider": provider,
            "agent": agent,
            "latency_ms": round(latency_ms, 2),
            "source_count": source_count,
            "success": success,
            "fallback_used": fallback_used,
            "failure_reason": sanitize_api_keys(failure_reason) if failure_reason else None,
            "cache_hit": cache_hit,
            "timestamp": time.time(),
        }
        self._telemetry.append(record)
        if len(self._telemetry) > 200:
            self._telemetry.pop(0)

    def get_recent_telemetry(self) -> list[dict[str, Any]]:
        return list(self._telemetry)

    async def execute_search_with_failover(
        self,
        query: str,
        native_fn: Optional[Callable] = None,
        fallback_fn: Optional[Callable] = None,
        agent_name: str = "google_search_general",
    ) -> SearchFailoverResult:
        """Phase 16 Hierarchy:
        1. Attempt native google_search
        2. On failure -> Attempt custom web_search_tool
        3. On failure -> Return controlled no-live-search state (Do NOT fabricate data).
        """
        start_time = time.time()
        clean_query = sanitize_api_keys(query.strip())
        failure_reason: Optional[str] = None

        # 1. Attempt Native Google Search
        if native_fn is not None:
            try:
                if asyncio.iscoroutinefunction(native_fn):
                    native_res = await native_fn(query)
                else:
                    native_res = native_fn(query)
                    if asyncio.iscoroutine(native_res):
                        native_res = await native_res

                if native_res:
                    items = native_res if isinstance(native_res, list) else [{"title": "Search Result", "snippet": str(native_res), "url": ""}]
                    latency = (time.time() - start_time) * 1000.0
                    self.log_telemetry(
                        query=clean_query,
                        provider="native_google_search",
                        agent=agent_name,
                        latency_ms=latency,
                        source_count=len(items),
                        success=True,
                        fallback_used=False,
                    )
                    return SearchFailoverResult(
                        query=clean_query,
                        provider="native_google_search",
                        fallback_used=False,
                        failure_reason=None,
                        latency_ms=latency,
                        source_count=len(items),
                        items=items,
                        formatted_output=str(native_res),
                        status="success",
                    )
                else:
                    failure_reason = "Native Google Search returned empty result set"
            except Exception as e:
                failure_reason = f"Native Google Search error: {sanitize_api_keys(str(e))}"
                logger.warning(f"Native search failed for '{clean_query}': {failure_reason}. Attempting fallback...")
        else:
            failure_reason = "Native Google Search provider not directly available in current runtime"

        # 2. Attempt Custom Web Search Fallback
        if fallback_fn is not None:
            try:
                fallback_start = time.time()
                if asyncio.iscoroutinefunction(fallback_fn):
                    fallback_res = await fallback_fn(query)
                else:
                    fallback_res = fallback_fn(query)
                    if asyncio.iscoroutine(fallback_res):
                        fallback_res = await fallback_res
                latency = (time.time() - start_time) * 1000.0
                if fallback_res and "No live search results found" not in str(fallback_res):
                    items = fallback_res if isinstance(fallback_res, list) else [{"title": "Fallback Result", "snippet": str(fallback_res), "url": ""}]
                    self.log_telemetry(
                        query=clean_query,
                        provider="custom_web_search",
                        agent=agent_name,
                        latency_ms=latency,
                        source_count=len(items),
                        success=True,
                        fallback_used=True,
                        failure_reason=failure_reason,
                    )
                    return SearchFailoverResult(
                        query=clean_query,
                        provider="custom_web_search",
                        fallback_used=True,
                        failure_reason=failure_reason,
                        latency_ms=latency,
                        source_count=len(items),
                        items=items,
                        formatted_output=str(fallback_res),
                        status="fallback",
                    )
                else:
                    fallback_error = f"{failure_reason}; Custom web search returned no results"
            except Exception as fb_err:
                fallback_error = f"{failure_reason}; Custom web search failed: {sanitize_api_keys(str(fb_err))}"
                logger.error(f"Fallback search failed for '{clean_query}': {fallback_error}")
        else:
            fallback_error = f"{failure_reason}; No fallback search function provided"

        # 3. Controlled No-Live-Search State (No fabrication)
        total_latency = (time.time() - start_time) * 1000.0
        self.log_telemetry(
            query=clean_query,
            provider="none",
            agent=agent_name,
            latency_ms=total_latency,
            source_count=0,
            success=False,
            fallback_used=True,
            failure_reason=fallback_error,
        )
        return SearchFailoverResult(
            query=clean_query,
            provider="none",
            fallback_used=True,
            failure_reason=fallback_error,
            latency_ms=total_latency,
            source_count=0,
            items=[],
            formatted_output="Live internet search is currently unavailable. Baseline knowledge will be used without fabricating real-time data.",
            status="no_live_search",
        )


# Singleton instance
INTERNET_PROVIDER_REGISTRY = InternetProviderRegistry()

