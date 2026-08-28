"""Unit tests for Phase 7: Content Extractor, Passage Ranker, Provenance Retention, and Context Economy."""

import json
import pytest
from google.adk.agents import LlmAgent

from src.adk.passage_extractor import (
    PassageChunk,
    ExtractedPassagesPacket,
    ContentExtractorEngine,
    PassageRankerEngine,
)
from src.adk.tools import (
    split_page_into_passages,
    split_page_into_passages_tool,
    rank_and_select_passages,
    rank_and_select_passages_tool,
)
from src.adk.agents import create_content_extractor_agent, create_passage_ranker_agent


def test_content_extractor_and_passage_ranker_agent_instantiation():
    """Verify content_extractor and passage_ranker are genuine LlmAgents with dedicated tools."""
    extractor = create_content_extractor_agent()
    assert isinstance(extractor, LlmAgent)
    assert extractor.name == "content_extractor"
    assert len(extractor.tools) == 1
    assert extractor.tools[0] is split_page_into_passages_tool
    assert "source_id" in extractor.instruction
    assert "retrieval_timestamp" in extractor.instruction

    ranker = create_passage_ranker_agent()
    assert isinstance(ranker, LlmAgent)
    assert ranker.name == "passage_ranker"
    assert len(ranker.tools) == 1
    assert ranker.tools[0] is rank_and_select_passages_tool
    assert "top K" in ranker.instruction
    assert "citation provenance" in ranker.instruction


def test_large_page_section_splitting_and_provenance_retention():
    """Verify a large document (50 sections) is cleanly split into 50 chunks retaining complete provenance."""
    sections = []
    for i in range(1, 51):
        sections.append(
            f"## Section {i}: Architectural Deep Dive on Feature {i}\n"
            f"Detailed technical specifications, operational constraints, and implementation details for module {i}. "
            f"This passage contains verifiable facts regarding system component {i}."
        )
    large_doc = "\n\n".join(sections)

    url = "https://ai.google.dev/adk/large-specification-guide"
    title = "Google ADK Large Architecture Guide"
    page_num = 14

    chunks = ContentExtractorEngine.split_into_sections(
        text=large_doc,
        url=url,
        title=title,
        page=page_num,
    )

    # Verify 50 chunks were extracted
    assert len(chunks) == 50

    # Verify every chunk retains full citation provenance
    for idx, c in enumerate(chunks, start=1):
        assert isinstance(c, PassageChunk)
        assert c.source_id.startswith("src_")
        assert c.url == url
        assert c.title == title
        assert f"Section {idx}" in c.heading
        assert f"module {idx}" in c.text
        assert c.page == 14
        assert c.retrieval_timestamp != ""


def test_passage_ranking_selects_top_relevant_chunks_without_losing_provenance():
    """Verify 50 chunks are ranked against a specific query and filtered down to top 5 relevant passages."""
    chunks = []
    url = "https://ai.google.dev/adk/specs"
    title = "ADK Complete Specifications"

    for i in range(1, 51):
        if i == 7:
            text = "Google ADK provides native ParallelAgent for concurrent independent search specialist execution."
            heading = "ParallelAgent Concurrency Model"
        elif i == 23:
            text = "Google ADK integrates with GoogleSearchTool for native web grounding and search isolation."
            heading = "Google Search Grounding"
        elif i == 41:
            text = "ParallelAgent handles bounded concurrency using semaphores and graceful 429 exponential backoff."
            heading = "Parallel Execution and Rate Limits"
        else:
            text = f"General background information about subsystem component {i} with unrelated technical details."
            heading = f"General Subsystem Component {i}"

        chunks.append(PassageChunk(
            source_id=f"src_test_{i}",
            url=url,
            title=title,
            heading=heading,
            text=text,
            page=i,
        ))

    query = "How does Google ADK ParallelAgent handle concurrency and search?"
    packet = PassageRankerEngine.rank_and_select(query=query, passages=chunks, top_k=5)

    assert isinstance(packet, ExtractedPassagesPacket)
    assert packet.total_chunks_extracted == 50
    assert len(packet.selected_passages) == 5

    # Top passages should include the matching sections (7, 41, 23)
    top_headings = [p.heading for p in packet.selected_passages]
    assert "ParallelAgent Concurrency Model" in top_headings
    assert "Parallel Execution and Rate Limits" in top_headings

    # Verify provenance is completely intact in selected passages
    for p in packet.selected_passages:
        assert p.url == url
        assert p.title == title
        assert p.source_id.startswith("src_test_")
        assert p.retrieval_timestamp != ""
        assert p.relevance_score >= 0.0

    assert packet.selected_passages[0].relevance_score > 0.5
    assert packet.selected_passages[1].relevance_score > 0.5


def test_tool_invocations_and_json_serialization():
    """Verify split_page_into_passages and rank_and_select_passages return valid JSON schemas."""
    sample_text = (
        "# Overview\n"
        "Introduction to Gemini models.\n\n"
        "## Performance\n"
        "Gemini 2.5 Flash achieves state-of-the-art efficiency."
    )

    passages_json = split_page_into_passages(
        text=sample_text,
        url="https://ai.google.dev/gemini",
        title="Gemini Overview",
    )
    parsed_passages = json.loads(passages_json)
    assert isinstance(parsed_passages, list)
    assert len(parsed_passages) == 2
    assert parsed_passages[0]["heading"] == "Overview"
    assert parsed_passages[1]["heading"] == "Performance"

    ranked_json = rank_and_select_passages(
        query="Gemini 2.5 Flash performance",
        passages_json=passages_json,
        top_k=1,
    )
    parsed_ranked = json.loads(ranked_json)
    assert "selected_passages" in parsed_ranked
    assert len(parsed_ranked["selected_passages"]) == 1
    assert parsed_ranked["selected_passages"][0]["heading"] == "Performance"
    assert "source_id" in parsed_ranked["selected_passages"][0]
    assert "retrieval_timestamp" in parsed_ranked["selected_passages"][0]
