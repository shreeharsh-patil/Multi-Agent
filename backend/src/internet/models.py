"""Typed domain models for InternetSDK search, scraping, ranking, and evidence verification."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ResearchMode(str, Enum):
    """Execution depth and intensity for web research workflows."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    CRITICAL = "critical"
    MASSIVE = "massive"


class FreshnessFilter(str, Enum):
    """Temporal constraints for search grounding and retrieval."""
    ANYTIME = "anytime"
    REALTIME = "realtime"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class VerificationStatus(str, Enum):
    """Audit status of a claim against retrieved web evidence."""
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    INACCESSIBLE = "inaccessible"
    CONTRADICTORY = "contradictory"


class SourceTier(str, Enum):
    """Authority and credibility grading for internet sources."""
    TIER_1_PRIMARY = "tier_1_primary"       # Official docs, peer-reviewed, gov, primary RFCs
    TIER_2_SECONDARY = "tier_2_secondary"   # Reputable news, verified benchmarks, industry reports
    TIER_3_COMMUNITY = "tier_3_community"   # Forums, blog posts, community Q&A
    TIER_4_LOW = "tier_4_low"               # Aggregators, unverified user content


class SearchProviderType(str, Enum):
    """Underlying search engine or grounding provider."""
    GOOGLE_GROUNDED = "google_grounded"
    DUCKDUCKGO = "duckduckgo"
    JINA = "jina"
    SEARXNG = "searxng"
    WIKIPEDIA = "wikipedia"
    FIRECRAWL = "firecrawl"
    AUTO = "auto"


class SearchQuery(BaseModel):
    """Normalized input query for search operations."""
    query: str
    purpose: str = "general"
    freshness: FreshnessFilter = FreshnessFilter.ANYTIME
    preferred_domains: list[str] = Field(default_factory=list)
    excluded_domains: list[str] = Field(default_factory=list)
    max_results: int = 5


class SearchResult(BaseModel):
    """Single item retrieved from search index or grounding service."""
    title: str
    url: str
    snippet: str
    source: str = ""
    score: float = 1.0
    published_date: Optional[str] = None
    domain: str = ""
    tier: SourceTier = SourceTier.TIER_2_SECONDARY


class SearchResponse(BaseModel):
    """Structured response from a search operation."""
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total_found: int = 0
    provider: str = "auto"
    latency_ms: float = 0.0
    from_cache: bool = False


class SourceDocument(BaseModel):
    """Full-text document scraped or extracted from a URL."""
    url: str
    title: str = ""
    content: str = ""
    markdown_content: str = ""
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tier: SourceTier = SourceTier.TIER_2_SECONDARY
    status_code: int = 200
    word_count: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class EvidenceChunk(BaseModel):
    """Granular piece of text evidence extracted from a source document."""
    chunk_id: str
    source_url: str
    title: str
    text: str
    relevance_score: float = 1.0
    tier: SourceTier = SourceTier.TIER_2_SECONDARY
    context: str = ""


class VerifiedClaim(BaseModel):
    """Fact or assertion evaluated against extracted evidence."""
    claim: str
    status: VerificationStatus = VerificationStatus.SUPPORTED
    confidence: float = 1.0
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_sources: list[str] = Field(default_factory=list)
    explanation: str = ""


class ResearchRequest(BaseModel):
    """High-level specification for deep internet research."""
    query: str
    mode: ResearchMode = ResearchMode.STANDARD
    freshness: FreshnessFilter = FreshnessFilter.ANYTIME
    max_sources: int = 5
    preferred_domains: list[str] = Field(default_factory=list)
    excluded_domains: list[str] = Field(default_factory=list)
    user_id: str = "default"
    conversation_id: str = "default"
    require_verification: bool = True


class ResearchResult(BaseModel):
    """Comprehensive output of an internet research session."""
    query: str
    summary_context: str = ""
    sources: list[SearchResult] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)
    claims: list[VerifiedClaim] = Field(default_factory=list)
    searches_performed: list[str] = Field(default_factory=list)
    provider: str = "auto"
    latency_ms: float = 0.0
    success: bool = True
    warnings: list[str] = Field(default_factory=list)
