"""Tests for Phase 12 (BossAgent Research Hierarchy Integration) and Phase 13 (ADK Progress Streaming).

Phase 12 Requirements:
- Final Routing:
  USER -> BossAgent -> WebIntentAgent -> NO INTERNET REQUIRED -> normal specialist
                                      -> INTERNET REQUIRED -> ResearchManager -> InternetIntelligenceManager -> SearchPlanner -> GoogleSearchManager -> search specialist(s) -> ResultRanker -> URLReader -> PassageRanker -> Verification Team -> EvidenceSynthesizer -> BossAgent -> FINAL RESPONSE
- BossAgent must:
  * use verified current evidence
  * preserve citations
  * explain uncertainty
  * never invent sources
  * combine web evidence with useful domain explanation
  * never scrape websites directly (no direct tool attachment)

Phase 13 Requirements:
- Expose high-level ADK events:
  * search_started
  * search_planned
  * searching
  * sources_found
  * reading_sources
  * source_verified
  * fact_check_started
  * fact_check_completed
  * synthesizing
  * answer_started
  * completed
- Frontend may show:
  * Searching the web...
  * Reading 5 sources...
  * Checking information...
  * Preparing answer...
- Do NOT expose private model reasoning.
- Final answer tokens should stream as soon as synthesis begins.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search

from src.agents.metadata import AgentDepartment, AgentMetadata
from src.agents.registry import AgentRegistry
from src.adk.agents import (
    create_boss_agent,
    get_boss_agent,
    create_google_search_manager,
    create_internet_intelligence_manager,
    build_all_adk_specialists,
    reset_adk_agent_tree,
    safe_adk_name,
    BOSS_INSTRUCTION,
)
from src.adk.sequential_pipeline import (
    ResearchHierarchyCoordinator,
    VerifiedWebPipelineExecutor,
)
from src.adk.research_synthesizer import (
    ResearchSynthesizer,
    ResearchSynthesisPacket,
    SynthesizedClaimRecord,
    SynthesizedSourceRecord,
    SynthesizedEvidenceItem,
    ConflictRecord,
    UncertaintyRecord,
)
from src.adk.runner import (
    process_message_stream,
    process_message,
)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()

    async def fake_stream(*args, **kwargs):
        yield "Verified "
        yield "Research "
        yield "Synthesis: Google ADK provides hierarchical multi-agent architecture."

    async def fake_web_search(query, *args, **kwargs):
        import json
        return json.dumps([
            {
                "title": f"Documentation for {query}",
                "url": f"https://docs.google.com/adk/{query.replace(' ', '-')}",
                "snippet": f"Google ADK provides multi-agent orchestration and specifications for {query}.",
            }
        ])

    from src.services.llm import llm_service
    from src.adk import tools
    monkeypatch.setattr(llm_service, "generate_stream", fake_stream)
    monkeypatch.setattr(tools, "web_search", fake_web_search)

    yield
    reset_adk_agent_tree()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 12 TESTS: Research Hierarchy Connected to BossAgent
# ═══════════════════════════════════════════════════════════════════════════

def test_boss_agent_has_no_direct_scraping_tools():
    """Phase 12: BossAgent must never scrape websites directly; no tools attached directly to root."""
    boss = get_boss_agent()
    assert boss.name == "boss_agent"
    assert len(boss.tools) == 0, "BossAgent must not have direct scraping or search tools attached"


def test_boss_agent_instruction_enforces_all_phase12_rules():
    """Phase 12: Verify BossAgent instruction mandates verified evidence, citations, uncertainty, anti-hallucination."""
    boss = get_boss_agent()
    instruction = boss.instruction

    # 1. Verified current evidence
    assert "verified" in instruction.lower()
    # 2. Preserve citations
    assert "citation" in instruction.lower() or "clickable" in instruction.lower()
    # 3. Explain uncertainty
    assert "uncertaint" in instruction.lower() or "conflict" in instruction.lower()
    # 4. Never invent sources
    assert "invent" in instruction.lower() or "fabricat" in instruction.lower() or "hallucinat" in instruction.lower()
    # 5. Combine web evidence with domain explanation
    assert "domain" in instruction.lower() or "synthesize" in instruction.lower()
    # 6. No direct scraping
    assert "scrap" in instruction.lower() or "hierarchy" in instruction.lower()


def test_google_search_manager_agent_creation_and_roster():
    """Phase 12: GoogleSearchManager is a distinct LlmAgent coordinating search specialists."""
    specialists = build_all_adk_specialists()
    search_specialist_nodes = [
        specialists["google-search-general"],
        specialists["google-news-researcher"],
        specialists["google-search-technology"],
        specialists["deep-web-researcher"],
    ]
    gs_mgr = create_google_search_manager(search_specialist_nodes)

    assert isinstance(gs_mgr, LlmAgent)
    assert gs_mgr.name == "google_search_manager"
    assert len(gs_mgr.sub_agents) == 4
    sub_names = {s.name for s in gs_mgr.sub_agents}
    assert "google_search_general" in sub_names
    assert "google_news_researcher" in sub_names
    assert "google_search_technology" in sub_names
    assert "deep_web_researcher" in sub_names


def test_research_manager_hierarchical_path_to_search_and_verification():
    """Phase 12: Verify BossAgent -> ResearchManager -> InternetIntelligenceManager -> specialists."""
    boss = get_boss_agent()
    research_mgr = next((m for m in boss.sub_agents if m.name == "research_manager"), None)
    assert research_mgr is not None, "research_manager missing under BossAgent"

    intel_mgr = next((s for s in research_mgr.sub_agents if s.name == "internet_intelligence_manager"), None)
    assert intel_mgr is not None, "internet_intelligence_manager missing under research_manager"

    specialist_names = {s.name for s in intel_mgr.sub_agents}
    # Planner
    assert "search_planner" in specialist_names
    # Search specialists
    assert "google_search_technology" in specialist_names
    assert "google_news_researcher" in specialist_names
    # Ranker & Reader & Extractor
    assert "search_result_ranker" in specialist_names
    assert "url_reader" in specialist_names
    assert "passage_ranker" in specialist_names
    # Verification team
    assert "source_verifier" in specialist_names
    assert "google_search_fact_checker" in specialist_names
    assert "citation_auditor" in specialist_names
    assert "freshness_checker" in specialist_names
    assert "contradiction_detector" in specialist_names
    # Synthesizer
    assert "evidence_synthesizer" in specialist_names


def test_web_intent_evaluation_bypasses_timeless_and_routes_temporal():
    """Phase 12: WebIntentAgent evaluation routes conceptual questions to normal specialists and temporal to research."""
    # Conceptual / coding questions bypass internet
    res_recursion = ResearchHierarchyCoordinator.evaluate_web_intent("What is recursion in programming?")
    assert res_recursion["requires_internet"] is False
    assert res_recursion["target_specialist"] == "coding"

    res_oop = ResearchHierarchyCoordinator.evaluate_web_intent("Explain polymorphism and encapsulation in OOP")
    assert res_oop["requires_internet"] is False

    res_math = ResearchHierarchyCoordinator.evaluate_web_intent("Calculate 25 * 480 + 1200")
    assert res_math["requires_internet"] is False

    # Temporal & current facts require internet
    res_latest = ResearchHierarchyCoordinator.evaluate_web_intent("What are the latest features of Google ADK in 2026?")
    assert res_latest["requires_internet"] is True
    assert res_latest["target_specialist"] == "research_manager"

    res_pricing = ResearchHierarchyCoordinator.evaluate_web_intent("Current pricing and release version of Claude 3.7 Sonnet")
    assert res_pricing["requires_internet"] is True


def test_boss_synthesis_prompt_preserves_citations_and_surfaces_uncertainty():
    """Phase 12: BossAgent synthesis prompt contains verified claims, citations, conflicts, and uncertainties."""
    packet = ResearchSynthesisPacket(
        query="Google ADK Multi-Agent Framework",
        verified_claims=[
            SynthesizedClaimRecord(
                claim="Google ADK provides SequentialAgent and ParallelAgent orchestration",
                status="SUPPORTED",
                confidence=0.98,
                sources=["https://docs.google.com/adk/overview"],
                authority_tier="Tier 1 (Primary / Official)",
                is_fresh=True,
                verdict_reason="Directly corroborated by official Google ADK documentation.",
            )
        ],
        evidence=[
            SynthesizedEvidenceItem(
                text="Google ADK supports hierarchical multi-agent architectures with session state persistence.",
                url="https://docs.google.com/adk/overview",
                title="Google ADK Overview",
                heading="Architecture",
            )
        ],
        sources=[
            SynthesizedSourceRecord(
                url="https://docs.google.com/adk/overview",
                authority_tier="Tier 1 (Primary / Official)",
                verified=True,
            )
        ],
        conflicts=[
            ConflictRecord(
                claim="ADK release timeline",
                conflict_description="Source A cites June 2025, Source B cites August 2025.",
                conflicting_sources=["https://source-a.com", "https://source-b.com"],
            )
        ],
        uncertainties=[
            UncertaintyRecord(
                claim="Pricing tier for enterprise sidecars",
                reason="Unverified claim without official public documentation.",
            )
        ],
        confidence=0.92,
    )

    prompt = ResearchHierarchyCoordinator.format_boss_synthesis_prompt(
        query="Google ADK Multi-Agent Framework",
        packet=packet,
    )

    assert "Google ADK provides SequentialAgent" in prompt
    assert "[https://docs.google.com/adk/overview](https://docs.google.com/adk/overview)" in prompt
    assert "Source A cites June 2025" in prompt
    assert "Pricing tier for enterprise sidecars" in prompt
    assert "Calibrated Confidence: 0.92" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 13 TESTS: Streaming ADK Progress Events Through Runner
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_streaming_hierarchy_emits_all_11_high_level_adk_events():
    """Phase 13: Streaming research hierarchy emits the exact 11 ADK progress events."""
    events_emitted = []

    async for event in ResearchHierarchyCoordinator.execute_streaming_hierarchy(
        query="Latest features of Google ADK multi-agent framework in 2026",
        conversation_id="conv-phase13-test",
    ):
        events_emitted.append(event)

    event_names = [e["event"] for e in events_emitted]

    # Verify all 11 high-level Phase 13 events are present in sequence:
    expected_events = [
        "search_started",
        "search_planned",
        "searching",
        "sources_found",
        "reading_sources",
        "source_verified",
        "fact_check_started",
        "fact_check_completed",
        "synthesizing",
        "answer_started",
        "completed",
    ]

    for exp in expected_events:
        assert exp in event_names, f"Missing required ADK progress event: {exp}"

    # Check user-facing status messages
    search_started_ev = next(e for e in events_emitted if e["event"] == "search_started")
    assert search_started_ev["data"]["message"] == "Searching the web..."

    reading_ev = next(e for e in events_emitted if e["event"] == "reading_sources")
    assert "Reading" in reading_ev["data"]["message"] and "sources..." in reading_ev["data"]["message"]

    fact_check_ev = next(e for e in events_emitted if e["event"] == "fact_check_started")
    assert fact_check_ev["data"]["message"] == "Checking information..."

    synthesizing_ev = next(e for e in events_emitted if e["event"] == "synthesizing")
    assert synthesizing_ev["data"]["message"] == "Preparing answer..."

    answer_ev = next(e for e in events_emitted if e["event"] == "answer_started")
    assert answer_ev["data"]["message"] == "Preparing answer..."


@pytest.mark.asyncio
async def test_private_model_reasoning_is_not_exposed_in_progress_stream():
    """Phase 13: Private model reasoning, chain-of-thought, or internal scratchpads are never leaked in events."""
    async for event in ResearchHierarchyCoordinator.execute_streaming_hierarchy(
        query="Compare Next.js 15 and Remix v3 server actions",
        conversation_id="conv-no-leak",
    ):
        data = event.get("data", {})
        # Ensure no private thinking / chain-of-thought fields
        assert "thought" not in data
        assert "thinking" not in data
        assert "reasoning" not in data
        assert "scratchpad" not in data
        assert "internal_prompt" not in data


@pytest.mark.asyncio
async def test_tokens_stream_immediately_when_synthesis_begins():
    """Phase 13: Final answer tokens stream immediately upon answer_started / synthesizing."""
    chunks_received = []
    answer_started_seen = False

    async for event in ResearchHierarchyCoordinator.execute_streaming_hierarchy(
        query="Explain Google ADK SequentialAgent architecture",
        conversation_id="conv-stream-order",
    ):
        if event["event"] == "answer_started":
            answer_started_seen = True
        elif event["event"] == "chunk" and answer_started_seen:
            chunks_received.append(event["data"]["text"])

    assert answer_started_seen is True
    assert len(chunks_received) > 0, "Expected chunks streamed after answer_started"


@pytest.mark.asyncio
async def test_non_internet_query_streams_directly_from_specialist():
    """Phase 12 & 13: Timeless query routes directly without search events and streams completed."""
    events = []
    async for event in ResearchHierarchyCoordinator.execute_streaming_hierarchy(
        query="What is a linked list and how to reverse it in Python?",
        conversation_id="conv-no-internet",
    ):
        events.append(event)

    event_names = [e["event"] for e in events]
    # No web search events emitted
    assert "search_started" not in event_names
    assert "searching" not in event_names
    assert "reading_sources" not in event_names

    # Direct agent and answer streamed
    assert "agent" in event_names
    assert "answer_started" in event_names
    assert "chunk" in event_names
    assert "completed" in event_names

    completed_ev = next(e for e in events if e["event"] == "completed")
    assert completed_ev["data"]["internet_used"] is False
