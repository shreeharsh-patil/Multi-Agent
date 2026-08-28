"""Unit tests for Phase 9: Ordered Research Pipeline using Google ADK SequentialAgent."""

import pytest
from google.adk.agents import LlmAgent, SequentialAgent

from src.adk.internet_provider import EvidencePacket
from src.adk.sequential_pipeline import (
    create_verified_web_pipeline_agent,
    VerifiedWebPipelineExecutor,
    store_pipeline_stage_data,
    get_pipeline_stage_data,
    SESSION_KEY_RAW_SEARCH_RESULTS,
    SESSION_KEY_RANKED_SOURCES,
    SESSION_KEY_READ_WEBPAGES,
    SESSION_KEY_EXTRACTED_PASSAGES,
    SESSION_KEY_VERIFIED_CLAIMS,
    SESSION_KEY_EVIDENCE_PACKET,
)


class MockAdkSession:
    """Mock ADK session object providing session.state dictionary."""
    def __init__(self):
        self.state: dict = {}


def test_verified_web_pipeline_is_real_adk_sequential_agent():
    """Verify create_verified_web_pipeline_agent returns a real Google ADK SequentialAgent with exact sub-agent sequence."""
    pipeline = create_verified_web_pipeline_agent()

    assert isinstance(pipeline, SequentialAgent)
    assert pipeline.name == "verified_web_pipeline"
    assert len(pipeline.sub_agents) == 7

    # Verify sub-agents are in the exact required order:
    # RANK -> READ -> EXTRACT -> VERIFY -> CITE -> SYNTHESIZE
    expected_order = [
        "search_result_ranker",
        "url_reader",
        "passage_ranker",
        "source_verifier",
        "google_search_fact_checker",
        "citation_auditor",
        "evidence_synthesizer",
    ]

    actual_order = [s.name for s in pipeline.sub_agents]
    assert actual_order == expected_order

    # Confirm SearchPlanner is NOT in the sequence
    assert "search_planner" not in actual_order


def test_session_state_storage_and_retrieval_across_stages():
    """Verify intermediate outputs are properly saved and retrieved from ADK session state."""
    session = MockAdkSession()

    # Test raw search results storage
    store_pipeline_stage_data(session, SESSION_KEY_RAW_SEARCH_RESULTS, ["https://example.com/1", "https://example.com/2"])
    assert len(get_pipeline_stage_data(session, SESSION_KEY_RAW_SEARCH_RESULTS)) == 2

    # Test ranked sources storage
    store_pipeline_stage_data(session, SESSION_KEY_RANKED_SOURCES, {"selected_sources": [{"url": "https://example.com/1"}]})
    assert "selected_sources" in get_pipeline_stage_data(session, SESSION_KEY_RANKED_SOURCES)

    # Test read webpages storage
    store_pipeline_stage_data(session, SESSION_KEY_READ_WEBPAGES, [{"url": "https://example.com/1", "clean_text": "Clean body"}])
    assert get_pipeline_stage_data(session, SESSION_KEY_READ_WEBPAGES)[0]["clean_text"] == "Clean body"

    # Test extracted passages storage
    store_pipeline_stage_data(session, SESSION_KEY_EXTRACTED_PASSAGES, {"selected_passages": [{"source_id": "src_1", "text": "chunk"}]})
    assert len(get_pipeline_stage_data(session, SESSION_KEY_EXTRACTED_PASSAGES)["selected_passages"]) == 1

    # Test verified claims storage
    store_pipeline_stage_data(session, SESSION_KEY_VERIFIED_CLAIMS, {"claims": [{"claim": "Test claim", "status": "SUPPORTED"}]})
    assert get_pipeline_stage_data(session, SESSION_KEY_VERIFIED_CLAIMS)["claims"][0]["status"] == "SUPPORTED"

    # Test final evidence packet storage
    store_pipeline_stage_data(session, SESSION_KEY_EVIDENCE_PACKET, {"query": "test", "findings": ["Fact 1"]})
    assert get_pipeline_stage_data(session, SESSION_KEY_EVIDENCE_PACKET)["query"] == "test"


def test_context_minimization_without_raw_html_leakage():
    """Verify that each stage receives only required context and strips raw HTML."""
    raw_urls = [
        "https://ai.google.dev/adk/docs",
        "https://github.com/google/adk",
        "https://randomblog.com/seo-farm",
    ]

    session = MockAdkSession()

    # Stage 1: RANK
    ranking = VerifiedWebPipelineExecutor.execute_rank_stage(
        query="Google ADK features",
        raw_urls=raw_urls,
        session=session,
        max_sources=2,
    )
    assert len(ranking.selected_sources) == 2
    assert SESSION_KEY_RANKED_SOURCES in session.state

    # Stage 2: READ (produces clean text, strips HTML clutter)
    read_pages = VerifiedWebPipelineExecutor.execute_read_stage(
        selected_sources=ranking.selected_sources,
        session=session,
        max_read=2,
    )
    assert len(read_pages) == 2
    for page in read_pages:
        assert "<html" not in page.relevant_text.lower()
        assert "<body" not in page.relevant_text.lower()
        assert len(page.relevant_text) > 0
    assert SESSION_KEY_READ_WEBPAGES in session.state

    # Stage 3: EXTRACT (splits into sections, ranks top passages)
    passages = VerifiedWebPipelineExecutor.execute_extract_stage(
        query="Google ADK features",
        extracted_pages=read_pages,
        session=session,
        top_k_passages=3,
    )
    assert len(passages.selected_passages) <= 3
    assert SESSION_KEY_EXTRACTED_PASSAGES in session.state


def test_full_sequential_pipeline_execution():
    """Verify end-to-end execution of VerifiedWebPipelineExecutor.run_full_pipeline()."""
    query = "Google ADK multi-agent architecture"
    raw_urls = [
        "https://ai.google.dev/adk/architecture",
        "https://github.com/google/adk",
    ]
    claims = [
        "Google ADK provides multi-agent architecture with SequentialAgent and ParallelAgent.",
    ]

    session = MockAdkSession()

    packet = VerifiedWebPipelineExecutor.run_full_pipeline(
        query=query,
        raw_search_urls=raw_urls,
        claims_to_verify=claims,
        session=session,
    )

    assert isinstance(packet, EvidencePacket)
    assert len(packet.sources) > 0
    assert len(packet.claims) > 0
    assert packet.research_summary != ""
    assert packet.confidence >= 0.70

    # Verify all intermediate state keys were populated in ADK session state
    assert SESSION_KEY_RANKED_SOURCES in session.state
    assert SESSION_KEY_READ_WEBPAGES in session.state
    assert SESSION_KEY_EXTRACTED_PASSAGES in session.state
    assert SESSION_KEY_VERIFIED_CLAIMS in session.state
    assert SESSION_KEY_EVIDENCE_PACKET in session.state
