"""Unit tests for Phase 1 InternetSDK core architecture, typed models, router, config, and exceptions."""

import pytest
from src.internet import (
    INTERNET_DEFAULT_MAX_SOURCES,
    INTERNET_MAX_SOURCES,
    INTERNET_REQUEST_TIMEOUT,
    INTERNET_RESEARCH_MAX_ITERATIONS,
    INTERNET_MAX_CONCURRENCY,
    InternetConfig,
    InternetError,
    SearchProviderError,
    SourceVerificationError,
    DocumentExtractionError,
    InvalidResearchRequestError,
    ResearchMode,
    FreshnessFilter,
    VerificationStatus,
    SourceTier,
    SearchProviderType,
    SearchQuery,
    SearchResult,
    SearchResponse,
    SourceDocument,
    EvidenceChunk,
    VerifiedClaim,
    ResearchRequest,
    ResearchResult,
    InternetQueryRouter,
    InternetSDK,
)


def test_internet_config_constants_and_defaults():
    """Validate that InternetSDK configuration constants are present and match settings."""
    assert INTERNET_DEFAULT_MAX_SOURCES >= 1
    assert INTERNET_MAX_SOURCES >= INTERNET_DEFAULT_MAX_SOURCES
    assert INTERNET_REQUEST_TIMEOUT > 0
    assert INTERNET_RESEARCH_MAX_ITERATIONS >= 1
    assert INTERNET_MAX_CONCURRENCY >= 1

    config = InternetConfig()
    assert config.default_max_sources == INTERNET_DEFAULT_MAX_SOURCES
    assert config.max_sources == INTERNET_MAX_SOURCES
    assert config.request_timeout == INTERNET_REQUEST_TIMEOUT
    assert config.enable_cache is True


def test_typed_models_instantiation():
    """Verify that all core typed domain models initialize cleanly."""
    query = SearchQuery(query="quantum computing benchmarks", max_results=8)
    assert query.query == "quantum computing benchmarks"
    assert query.max_results == 8
    assert query.freshness == FreshnessFilter.ANYTIME

    result = SearchResult(
        title="Benchmark Report 2026",
        url="https://example.com/benchmark",
        snippet="Summary of quantum benchmark results.",
        tier=SourceTier.TIER_1_PRIMARY,
    )
    assert result.tier == SourceTier.TIER_1_PRIMARY

    resp = SearchResponse(
        query=query.query,
        results=[result],
        total_found=1,
        provider="google_grounded",
        latency_ms=120.5,
    )
    assert resp.total_found == 1
    assert resp.results[0].title == "Benchmark Report 2026"

    doc = SourceDocument(
        url="https://example.com/doc",
        title="Official Doc",
        content="Full text document.",
        tier=SourceTier.TIER_1_PRIMARY,
    )
    assert doc.url == "https://example.com/doc"
    assert doc.tier == SourceTier.TIER_1_PRIMARY

    chunk = EvidenceChunk(
        chunk_id="chunk-001",
        source_url=doc.url,
        title=doc.title,
        text="Target evidence snippet.",
    )
    assert chunk.chunk_id == "chunk-001"

    claim = VerifiedClaim(
        claim="Quantum volume surpassed 1000",
        status=VerificationStatus.SUPPORTED,
        supporting_sources=["https://example.com/benchmark"],
    )
    assert claim.status == VerificationStatus.SUPPORTED
    assert len(claim.supporting_sources) == 1

    req = ResearchRequest(
        query="Deep research query",
        mode=ResearchMode.DEEP,
        freshness=FreshnessFilter.MONTH,
        max_sources=10,
    )
    assert req.mode == ResearchMode.DEEP
    assert req.max_sources == 10

    res = ResearchResult(
        query=req.query,
        summary_context="Contextual synthesis.",
        sources=[result],
        evidence=[chunk],
        claims=[claim],
        success=True,
    )
    assert res.success is True
    assert len(res.sources) == 1
    assert len(res.evidence) == 1
    assert len(res.claims) == 1


def test_exceptions_hierarchy():
    """Verify that all typed exceptions correctly subclass InternetError."""
    assert issubclass(SearchProviderError, InternetError)
    assert issubclass(SourceVerificationError, InternetError)
    assert issubclass(DocumentExtractionError, InternetError)
    assert issubclass(InvalidResearchRequestError, InternetError)

    err = InternetError("Something went wrong", {"code": 500})
    assert str(err) == "Something went wrong"
    assert err.details == {"code": 500}


def test_query_router_classification():
    """Test router heuristics for modes, freshness, and provider routing."""
    router = InternetQueryRouter()

    # Mode determination
    assert router.determine_mode("What is python") == ResearchMode.QUICK
    assert router.determine_mode("Conduct a comprehensive in-depth analysis of AI safety") == ResearchMode.DEEP
    assert router.determine_mode("General question with some reasonable length", explicit_mode=ResearchMode.CRITICAL) == ResearchMode.CRITICAL

    # Freshness determination
    assert router.determine_freshness("What happened today in tech") == FreshnessFilter.REALTIME
    assert router.determine_freshness("Latest releases this week") == FreshnessFilter.WEEK
    assert router.determine_freshness("History of computing") == FreshnessFilter.ANYTIME

    # Provider selection
    assert router.select_provider("Breaking news today") == SearchProviderType.GOOGLE_GROUNDED
    assert router.select_provider("FastAPI API documentation and SDK") == SearchProviderType.DUCKDUCKGO
    assert router.select_provider("General search", preferred_provider=SearchProviderType.SEARXNG) == SearchProviderType.SEARXNG


@pytest.mark.asyncio
async def test_internet_sdk_operations():
    """Test InternetSDK async methods and validation behaviors."""
    sdk = InternetSDK()

    # Search method
    search_resp = await sdk.search("latest news")
    assert isinstance(search_resp, SearchResponse)
    assert search_resp.query == "latest news"

    with pytest.raises(InvalidResearchRequestError):
        await sdk.search("   ")

    # Read URL method
    doc = await sdk.read_url("https://example.com/article")
    assert isinstance(doc, SourceDocument)
    assert doc.url == "https://example.com/article"

    with pytest.raises(DocumentExtractionError):
        await sdk.read_url("not_a_valid_url")

    # Research method
    research_res = await sdk.research("Research quantum algorithms", mode=ResearchMode.DEEP)
    assert isinstance(research_res, ResearchResult)
    assert research_res.query == "Research quantum algorithms"
    assert research_res.success is True

    with pytest.raises(InvalidResearchRequestError):
        await sdk.research("")

    # Verify method
    claim_res = await sdk.verify("Model X is faster than Model Y", ["https://example.com/source1"])
    assert isinstance(claim_res, VerifiedClaim)
    assert claim_res.status == VerificationStatus.SUPPORTED

    with pytest.raises(SourceVerificationError):
        await sdk.verify("", ["https://example.com/source1"])
