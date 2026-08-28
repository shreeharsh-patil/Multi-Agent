"""Core InternetSDK facade for search, document scraping, and claim verification."""

import time
from typing import Optional
from src.internet.config import InternetConfig
from src.internet.models import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    SourceDocument,
    EvidenceChunk,
    VerifiedClaim,
    ResearchRequest,
    ResearchResult,
    ResearchMode,
    FreshnessFilter,
    VerificationStatus,
    SourceTier,
)
from src.internet.router import InternetQueryRouter
from src.internet.exceptions import (
    InternetError,
    SearchProviderError,
    SourceVerificationError,
    DocumentExtractionError,
    InvalidResearchRequestError,
)
from src.utils.logger import logger


class InternetSDK:
    """Production interface for real-time web research, content extraction, and claim verification."""

    def __init__(self, config: Optional[InternetConfig] = None):
        self.config = config or InternetConfig()
        self.router = InternetQueryRouter()
        logger.info(
            "InternetSDK initialized with timeout=%ss, max_sources=%s",
            self.config.request_timeout,
            self.config.max_sources,
        )

    async def search(
        self,
        query: str | SearchQuery,
        *,
        max_results: Optional[int] = None,
        freshness: Optional[FreshnessFilter] = None,
        preferred_domains: Optional[list[str]] = None,
        excluded_domains: Optional[list[str]] = None,
    ) -> SearchResponse:
        """Execute a grounded search across internet search providers.

        Phase 1: Returns a typed SearchResponse. Complete multi-engine orchestration is scheduled for Phase 2.
        """
        started_at = time.perf_counter()
        if isinstance(query, str):
            if not query.strip():
                raise InvalidResearchRequestError("Search query cannot be empty.")
            norm_query = SearchQuery(
                query=query.strip(),
                freshness=freshness or FreshnessFilter.ANYTIME,
                max_results=max_results or self.config.default_max_sources,
                preferred_domains=preferred_domains or [],
                excluded_domains=excluded_domains or [],
            )
        else:
            norm_query = query

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return SearchResponse(
            query=norm_query.query,
            results=[],
            total_found=0,
            provider="auto",
            latency_ms=latency_ms,
            from_cache=False,
        )

    async def read_url(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
    ) -> SourceDocument:
        """Extract and clean full-text markdown content from a target URL.

        Phase 1: Returns a typed SourceDocument placeholder.
        """
        clean_url = (url or "").strip()
        if not clean_url or not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            raise DocumentExtractionError(f"Invalid URL format: '{url}'")

        return SourceDocument(
            url=clean_url,
            title="",
            content="",
            markdown_content="",
            tier=SourceTier.TIER_2_SECONDARY,
            status_code=200,
            word_count=0,
        )

    async def research(
        self,
        request: str | ResearchRequest,
        *,
        mode: Optional[ResearchMode] = None,
        max_sources: Optional[int] = None,
        user_id: str = "default",
        conversation_id: str = "default",
    ) -> ResearchResult:
        """Execute structured, iterative multi-source web research.

        Phase 1: Returns a typed ResearchResult placeholder.
        """
        started_at = time.perf_counter()
        if isinstance(request, str):
            if not request.strip():
                raise InvalidResearchRequestError("Research query cannot be empty.")
            norm_mode = self.router.determine_mode(request, mode)
            norm_request = ResearchRequest(
                query=request.strip(),
                mode=norm_mode,
                max_sources=min(max_sources or self.config.default_max_sources, self.config.max_sources),
                user_id=user_id,
                conversation_id=conversation_id,
            )
        else:
            norm_request = request

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return ResearchResult(
            query=norm_request.query,
            summary_context="",
            sources=[],
            evidence=[],
            claims=[],
            searches_performed=[norm_request.query],
            provider="auto",
            latency_ms=latency_ms,
            success=True,
            warnings=[],
        )

    async def verify(
        self,
        claim: str,
        source_urls: list[str],
        *,
        context: Optional[str] = None,
    ) -> VerifiedClaim:
        """Verify a factual assertion against a list of source documents.

        Phase 1: Returns a typed VerifiedClaim placeholder.
        """
        clean_claim = (claim or "").strip()
        if not clean_claim:
            raise SourceVerificationError("Claim text cannot be empty.")

        return VerifiedClaim(
            claim=clean_claim,
            status=VerificationStatus.SUPPORTED if source_urls else VerificationStatus.UNSUPPORTED,
            confidence=1.0 if source_urls else 0.0,
            supporting_sources=source_urls,
            contradicting_sources=[],
            explanation="Phase 1 verification stub" if source_urls else "No source URLs provided.",
        )
