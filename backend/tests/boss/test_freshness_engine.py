import pytest
from src.services.freshness_analyzer import freshness_analyzer, FreshnessLevel
from src.services.evidence_store import EvidenceStore
from src.orchestrator.boss import BossAgent


def test_freshness_analyzer_levels():
    """Verify semantic freshness classification across query types."""
    res_static = freshness_analyzer.analyze("What is TCP?")
    assert res_static["level"] == FreshnessLevel.STATIC
    assert res_static["research_required"] is False

    res_live = freshness_analyzer.analyze("Bitcoin price right now")
    assert res_live["level"] == FreshnessLevel.LIVE
    assert res_live["research_required"] is True

    res_current_mouse = freshness_analyzer.analyze("best mouse under 500")
    assert res_current_mouse["level"] == FreshnessLevel.CURRENT
    assert res_current_mouse["research_required"] is True

    res_current_pcce = freshness_analyzer.analyze("PCCE Goa information")
    assert res_current_pcce["level"] == FreshnessLevel.CURRENT
    assert res_current_pcce["research_required"] is True

    res_recent = freshness_analyzer.analyze("latest tech news this week")
    assert res_recent["level"] in [FreshnessLevel.CURRENT, FreshnessLevel.RECENT]
    assert res_recent["research_required"] is True


def test_evidence_store_claim_mapping():
    """Verify EvidenceStore records claims and verifies sources."""
    store = EvidenceStore("task_123")
    claim = store.add_claim(
        claim="PCCE offers Computer Engineering",
        value=True,
        source_title="PCCE Official Academics",
        source_url="https://pccegoa.org/academics",
        evidence_snippet="PCCE offers B.Tech in Computer Engineering",
        verification="verified",
        confidence=0.98,
    )

    assert claim.claim == "PCCE offers Computer Engineering"
    assert claim.verification == "verified"
    assert len(store.get_verified_claims()) == 1
    assert store.sources[0]["url"] == "https://pccegoa.org/academics"


@pytest.mark.asyncio
async def test_boss_freshness_intent_detection():
    """Verify BossAgent detects requires_live_data=True for real-time queries."""
    boss = BossAgent()

    test_queries = [
        "latest AI models",
        "current price of Bitcoin",
        "best mouse under ₹500",
        "PCCE Goa information",
        "PCCE Goa admission 2026",
        "latest Cloudflare models",
        "current Python version",
        "today's tech news",
        "weather in Goa",
    ]

    for q in test_queries:
        intent = await boss._analyze_intent(q)
        assert intent["requires_live_data"] is True, f"Failed freshness classification for query: '{q}'"
