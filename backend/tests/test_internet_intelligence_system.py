import pytest
from collections import Counter
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from src.agents.metadata import AgentDepartment, AgentMetadata
from src.agents.registry import AgentRegistry
from src.adk.agents import (
    create_boss_agent,
    get_boss_agent,
    get_adk_hierarchy_summary,
    build_all_adk_specialists,
    safe_adk_name,
    adk_name_to_registry_id,
    registry_id_to_adk_name,
    reset_adk_agent_tree,
    SPECIALIST_FACTORIES,
    ADK_TOOL_MAP,
    INTERNET_INTELLIGENCE_SPECIALIST_NAMES,
)
from src.adk.tools import scrape_page_tool, web_search_tool
from src.adk.internet_provider import (
    URLCanonicalizer,
    SearchCache,
    FreshnessRequirement,
    SourceTier,
    EvidenceItem,
    EvidencePacket,
    InternetProviderRegistry,
    INTERNET_PROVIDER_REGISTRY,
)
from src.adk.runner import (
    get_adk_status,
    _format_agent_trace,
)


@pytest.fixture(autouse=True)
def setup_adk_environment():
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()
    yield
    reset_adk_agent_tree()


EXPECTED_INTERNET_SPECIALISTS = [
    # Planning & Intent
    "web-intent-agent",
    "freshness-agent",
    "search-planner",
    "google-search-general",
    "google-news-researcher",
    "deep-web-researcher",
    "url-reader",
    "google-search-fact-checker",
    "source-verifier",
    "freshness-checker",
    "official-docs-researcher",
    "google-search-technology",
    "github-researcher",
    "google-search-academic",
    "cybersecurity-researcher",
    "google-search-market",
    "google-search-products",
    "google-search-local",
    "google-search-travel",
    "community-researcher",
    "evidence-synthesizer",
    # 27 Advanced Research Layer
    "query-optimizer",
    "multi-query-generator",
    "research-scope-controller",
    "search-result-ranker",
    "primary-source-hunter",
    "citation-auditor",
    "contradiction-detector",
    "bias-detector",
    "evidence-quality-judge",
    "timeline-researcher",
    "entity-researcher",
    "company-intelligence-agent",
    "startup-researcher",
    "public-osint-researcher",
    "documentation-reader",
    "api-documentation-researcher",
    "release-notes-agent",
    "benchmark-researcher",
    "dataset-researcher",
    "standards-researcher",
    "paper-comparison-agent",
    "methodology-reviewer",
    "patent-researcher",
    "regulation-researcher",
    "price-monitor-researcher",
    "availability-checker",
    "internet-evidence-judge",
]


def test_native_google_search_grounding_available():
    """Test 1: Native google_search is importable and distinct from custom web search."""
    assert google_search is not None
    assert "GoogleSearchTool" in type(google_search).__name__
    assert google_search is not web_search_tool


def test_custom_tools_remain_distinct_and_intact():
    """Test 2 & 3: Existing custom web_search_tool and scrape_page_tool remain intact."""
    assert web_search_tool is not None
    assert scrape_page_tool is not None
    assert web_search_tool.name == "web_search"
    assert scrape_page_tool.name == "scrape_page"


def test_all_46_internet_specialists_are_real_llm_agents():
    """Test 4: All Internet Intelligence specialists are instantiated as real LlmAgents."""
    specialists = build_all_adk_specialists()
    assert len(EXPECTED_INTERNET_SPECIALISTS) == 48
    for agent_id in EXPECTED_INTERNET_SPECIALISTS:
        assert agent_id in specialists, f"Missing specialist {agent_id}"
        agent = specialists[agent_id]
        assert isinstance(agent, LlmAgent)
        assert agent.name == safe_adk_name(agent_id)


def test_url_reader_and_docs_reader_use_scrape_page_tool():
    """Test 5: URL Reader and Documentation Reader are equipped with scrape_page_tool."""
    specialists = build_all_adk_specialists()
    for reader_id in ["url-reader", "documentation-reader"]:
        reader = specialists[reader_id]
        assert len(reader.tools) == 1
        assert reader.tools[0] == scrape_page_tool


def test_native_search_specialists_isolate_google_search():
    """Test 6: Native Google Search agents isolate google_search tool."""
    specialists = build_all_adk_specialists()
    pure_search_agents = [
        "google-search-general",
        "google-news-researcher",
        "deep-web-researcher",
        "google-search-fact-checker",
        "source-verifier",
        "official-docs-researcher",
        "google-search-technology",
        "github-researcher",
        "google-search-academic",
        "cybersecurity-researcher",
        "google-search-market",
        "google-search-products",
        "google-search-local",
        "google-search-travel",
        "community-researcher",
        "primary-source-hunter",
        "timeline-researcher",
        "entity-researcher",
        "company-intelligence-agent",
        "startup-researcher",
        "public-osint-researcher",
        "api-documentation-researcher",
        "release-notes-agent",
        "benchmark-researcher",
        "dataset-researcher",
        "standards-researcher",
        "paper-comparison-agent",
        "patent-researcher",
        "regulation-researcher",
        "price-monitor-researcher",
        "availability-checker",
    ]
    for agent_id in pure_search_agents:
        agent = specialists[agent_id]
        assert len(agent.tools) == 1, f"{agent_id} expected exactly 1 tool"
        assert agent.tools[0] is google_search


def test_internet_intelligence_manager_orchestrates_all_46_specialists():
    """Test 7: InternetIntelligenceManager orchestrates all specialists."""
    boss = get_boss_agent()
    research_mgr = next(m for m in boss.sub_agents if m.name == "research_manager")
    assert research_mgr is not None

    intel_mgr = next(s for s in research_mgr.sub_agents if s.name == "internet_intelligence_manager")
    assert intel_mgr is not None
    assert len(intel_mgr.sub_agents) == len(EXPECTED_INTERNET_SPECIALISTS)

    sub_names = {s.name for s in intel_mgr.sub_agents}
    expected_names = {safe_adk_name(aid) for aid in EXPECTED_INTERNET_SPECIALISTS}
    assert sub_names == expected_names


def test_url_canonicalizer_strips_tracking_and_deduplicates():
    """Test 11 & 32: URL Canonicalizer strips tracking parameters and deduplicates URLs."""
    raw_url1 = "https://NextJS.org/docs/app?utm_source=twitter&utm_medium=social&fbclid=123#installation"
    raw_url2 = "https://nextjs.org/docs/app?gclid=xyz"
    raw_url3 = "https://react.dev/reference/react/useState?utm_campaign=launch"

    canon1 = URLCanonicalizer.canonicalize(raw_url1)
    canon2 = URLCanonicalizer.canonicalize(raw_url2)
    assert canon1 == "https://nextjs.org/docs/app"
    assert canon2 == "https://nextjs.org/docs/app"

    deduped = URLCanonicalizer.deduplicate_urls([raw_url1, raw_url2, raw_url3])
    assert len(deduped) == 2
    assert "https://nextjs.org/docs/app" in deduped
    assert "https://react.dev/reference/react/useState" in deduped


def test_search_cache_ttl_and_realtime_bypass():
    """Test 12 & 30: SearchCache bypasses realtime/breaking news queries and caches standard queries."""
    cache = SearchCache()

    # Realtime queries must bypass cache (TTL = 0)
    cache.set("search_news", "breaking news today", FreshnessRequirement.REALTIME, {"results": ["news1"]})
    assert cache.get("search_news", "breaking news today", FreshnessRequirement.REALTIME) is None

    # Standard technical docs queries get cached
    cache.set("search_web", "React 19 hooks reference", FreshnessRequirement.STANDARD, {"results": ["doc1"]})
    cached_val = cache.get("search_web", "React 19 hooks reference", FreshnessRequirement.STANDARD)
    assert cached_val is not None
    assert cached_val["results"] == ["doc1"]


def test_evidence_synthesizer_packet_structure():
    """Test 21 & 33: EvidenceSynthesizer builds structured EvidencePacket retaining citations."""
    packet = EvidencePacket(
        claims=[{"claim": "Next.js 15 supports React 19", "status": "SUPPORTED"}],
        sources=[{
            "title": "Next.js 15 Release Notes",
            "url": "https://nextjs.org/blog/next-15",
            "tier": SourceTier.TIER_1_PRIMARY.value,
        }],
        confidence=0.98,
        freshness="recent",
        research_summary="Next.js 15 introduces React 19 support and async request APIs.",
    )
    d = packet.to_dict()
    assert d["confidence"] == 0.98
    assert len(d["sources"]) == 1
    assert d["sources"][0]["tier"] == SourceTier.TIER_1_PRIMARY.value


def test_all_adk_names_are_globally_unique():
    """Test 14: All ADK agent names across the entire platform are strictly unique."""
    specialists = build_all_adk_specialists()
    names = [s.name for s in specialists.values()]
    names.append("boss_agent")
    names.append("internet_intelligence_manager")
    names.extend([
        "command_planning_manager",
        "coding_manager",
        "research_manager",
        "content_manager",
        "visual_manager",
        "data_manager",
        "product_department_manager",
        "ai_ml_manager",
        "automation_manager",
        "business_quality_manager",
    ])
    counts = Counter(names)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    assert not duplicates, f"Duplicate ADK node names detected: {duplicates}"


def test_adk_hierarchy_telemetry_counts():
    """Test 15 & 37: Status summary telemetry reflects 100+ agents and division hierarchy dynamically."""
    summary = get_adk_hierarchy_summary()
    assert summary["registry_agents"] >= 140
    assert summary["adk_specialists"] == summary["registry_agents"]
    assert summary["internet_intelligence_agents"] == 48
    assert summary["department_managers"] == 10
    assert summary["division_managers"] == 1
    assert summary["root_agents"] == 1
    assert summary["total_adk_nodes"] == summary["adk_specialists"] + 12


def test_weather_news_agent_tools_and_factory():
    """Test weather_news specialist is equipped with weather_tool and google_search."""
    specialists = build_all_adk_specialists()
    assert "weather_news" in specialists or "weather-news" in specialists
    weather_agent = specialists.get("weather_news") or specialists.get("weather-news")
    assert weather_agent is not None
    assert len(weather_agent.tools) == 2
    tool_names = [getattr(t, "name", str(t)) for t in weather_agent.tools]
    assert any("fetch_live_weather" in n or "weather" in n for n in tool_names)
