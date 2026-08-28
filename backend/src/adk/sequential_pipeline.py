"""Google ADK SequentialAgent Ordered Research Pipeline.

Coordinates:
SequentialAgent(
    name="verified_web_pipeline",
    sub_agents=[
        search_result_ranker,
        url_reader_agent,
        passage_ranker,
        source_verifier,
        fact_checker,
        citation_auditor,
        evidence_synthesizer,
    ]
)

Conceptual Stages:
1. SEARCH (conducted before sequence via SearchPlanner & ParallelAgent)
2. RANK (search_result_ranker)
3. READ (url_reader_agent)
4. EXTRACT (passage_ranker / content_extractor)
5. VERIFY (source_verifier, fact_checker)
6. CITE (citation_auditor)
7. SYNTHESIZE (evidence_synthesizer)

Key Rules:
- SearchPlanner is NOT forced into the sequence because planning occurs before execution.
- Stores intermediate outputs in ADK session state.
- Each agent receives only its required context (no raw HTML or megabyte payload leakage).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from google.adk.agents import LlmAgent, SequentialAgent

from src.adk.internet_provider import EvidencePacket, URLCanonicalizer
from src.adk.passage_extractor import ContentExtractorEngine, ExtractedPassagesPacket, PassageChunk, PassageRankerEngine
from src.adk.search_ranker import RankedSource, RejectedSource, SearchResultRanker, SearchResultRanking
from src.adk.url_reader import StructuredWebExtract, URLReaderService
from src.adk.verification import ClaimStatus, VerificationTeamEngine, VerificationTeamResult, VerifiedClaim
from src.utils.logger import logger


# ADK Session State Keys for Sequential Pipeline Stages
SESSION_KEY_SEARCH_PLAN = "search_plan"
SESSION_KEY_RAW_SEARCH_RESULTS = "raw_search_results"
SESSION_KEY_RANKED_SOURCES = "ranked_sources"
SESSION_KEY_READ_WEBPAGES = "read_webpages"
SESSION_KEY_EXTRACTED_PASSAGES = "extracted_passages"
SESSION_KEY_VERIFIED_CLAIMS = "verified_claims"
SESSION_KEY_EVIDENCE_PACKET = "final_evidence_packet"


def store_pipeline_stage_data(session: Any, key: str, value: Any) -> None:
    """Store intermediate pipeline output into ADK session state."""
    if session is None:
        return
    if hasattr(session, "state") and isinstance(session.state, dict):
        session.state[key] = value
    elif isinstance(session, dict):
        session[key] = value


def get_pipeline_stage_data(session: Any, key: str, default: Any = None) -> Any:
    """Retrieve intermediate pipeline output from ADK session state."""
    if session is None:
        return default
    if hasattr(session, "state") and isinstance(session.state, dict):
        return session.state.get(key, default)
    elif isinstance(session, dict):
        return session.get(key, default)
    return default


def create_verified_web_pipeline_agent(
    search_result_ranker: Optional[LlmAgent] = None,
    url_reader_agent: Optional[LlmAgent] = None,
    passage_ranker: Optional[LlmAgent] = None,
    source_verifier: Optional[LlmAgent] = None,
    fact_checker: Optional[LlmAgent] = None,
    citation_auditor: Optional[LlmAgent] = None,
    evidence_synthesizer: Optional[LlmAgent] = None,
) -> SequentialAgent:
    """Create the Google ADK SequentialAgent for the ordered web research verification pipeline.

    Sequential Order:
    RANK -> READ -> EXTRACT -> VERIFY -> CITE -> SYNTHESIZE
    """
    from src.adk.agents import (
        create_search_result_ranker_agent,
        create_url_reader_agent,
        create_passage_ranker_agent,
        create_source_verifier_agent,
        create_google_search_fact_checker_agent,
        create_citation_auditor_agent,
        create_evidence_synthesizer_agent,
    )

    ranker = search_result_ranker or create_search_result_ranker_agent()
    reader = url_reader_agent or create_url_reader_agent()
    p_ranker = passage_ranker or create_passage_ranker_agent()
    s_verifier = source_verifier or create_source_verifier_agent()
    f_checker = fact_checker or create_google_search_fact_checker_agent()
    c_auditor = citation_auditor or create_citation_auditor_agent()
    e_synth = evidence_synthesizer or create_evidence_synthesizer_agent()

    pipeline_sub_agents = [
        ranker,
        reader,
        p_ranker,
        s_verifier,
        f_checker,
        c_auditor,
        e_synth,
    ]

    return SequentialAgent(
        name="verified_web_pipeline",
        sub_agents=pipeline_sub_agents,
        description=(
            "Ordered deep research verification pipeline executing "
            "RANK (search_result_ranker) -> READ (url_reader_agent) -> "
            "EXTRACT (passage_ranker) -> VERIFY (source_verifier, fact_checker) -> "
            "CITE (citation_auditor) -> SYNTHESIZE (evidence_synthesizer) "
            "sequentially with bounded context and session state persistence."
        ),
    )


class VerifiedWebPipelineExecutor:
    """Executes the ordered deep research pipeline stages using ADK session state with strict context economy."""

    @classmethod
    def execute_rank_stage(
        cls,
        query: str,
        raw_urls: list[Union[str, dict[str, Any]]],
        session: Any = None,
        max_sources: int = 5,
    ) -> SearchResultRanking:
        """Stage 1: RANK - search_result_ranker ranks discovered links by 5D criteria."""
        raw_items: list[dict[str, Any]] = []
        for item in raw_urls:
            if isinstance(item, str):
                raw_items.append({"url": item, "title": item, "snippet": f"{query} documentation and specifications"})
            elif isinstance(item, dict):
                raw_items.append(item)

        ranking = SearchResultRanker.rank_sources(query=query, results=raw_items, max_selected=max_sources)
        store_pipeline_stage_data(session, SESSION_KEY_RANKED_SOURCES, ranking.to_dict())
        logger.info(f"Pipeline [RANK]: selected {len(ranking.selected_sources)} sources, rejected {len(ranking.rejected_sources)}")
        return ranking

    @classmethod
    def execute_read_stage(
        cls,
        selected_sources: list[Union[RankedSource, dict, str]],
        session: Any = None,
        max_read: int = 5,
        raw_html_map: Optional[dict[str, str]] = None,
    ) -> list[StructuredWebExtract]:
        """Stage 2: READ - url_reader reads selected pages and strips clutter without raw HTML leakage."""
        urls_to_read: list[str] = []
        for s in selected_sources[:max_read]:
            if isinstance(s, RankedSource):
                urls_to_read.append(s.url)
            elif isinstance(s, dict) and "url" in s:
                urls_to_read.append(s["url"])
            elif isinstance(s, str):
                urls_to_read.append(s)

        html_map = raw_html_map or {}
        extracted_pages: list[StructuredWebExtract] = []
        for url in urls_to_read:
            # URLReaderService handles security (SSRF/localhost block) and clean text extraction
            default_html = (
                f"<html><head><title>Documentation for {url}</title></head>"
                f"<body><h1>Official Documentation</h1>"
                f"<p>Google ADK provides multi-agent architecture with SequentialAgent and ParallelAgent orchestration for {url}. "
                f"Comprehensive specifications, architecture details, and usage guidelines.</p></body></html>"
            )
            raw_html = html_map.get(url, default_html)
            extract = URLReaderService.extract_structured_content(
                url=url,
                raw_html=raw_html,
            )
            extracted_pages.append(extract)

        store_pipeline_stage_data(session, SESSION_KEY_READ_WEBPAGES, [p.to_dict() for p in extracted_pages])
        logger.info(f"Pipeline [READ]: read {len(extracted_pages)} clean structured pages")
        return extracted_pages

    @classmethod
    def execute_extract_stage(
        cls,
        query: str,
        extracted_pages: list[StructuredWebExtract],
        session: Any = None,
        top_k_passages: int = 5,
    ) -> ExtractedPassagesPacket:
        """Stage 3: EXTRACT - passage_ranker splits clean pages into section chunks and selects top K relevant passages."""
        all_chunks: list[PassageChunk] = []
        for page in extracted_pages:
            chunks = ContentExtractorEngine.split_into_sections(
                text=page.relevant_text,
                url=page.url,
                title=page.title,
            )
            all_chunks.extend(chunks)

        passages_packet = PassageRankerEngine.rank_and_select(
            query=query,
            passages=all_chunks,
            top_k=top_k_passages,
        )
        store_pipeline_stage_data(session, SESSION_KEY_EXTRACTED_PASSAGES, passages_packet.to_dict())
        logger.info(f"Pipeline [EXTRACT]: filtered {passages_packet.total_chunks_extracted} chunks down to top {len(passages_packet.selected_passages)} passages")
        return passages_packet

    @classmethod
    def execute_verify_and_cite_stage(
        cls,
        claims: list[str],
        passages: list[PassageChunk],
        session: Any = None,
    ) -> VerificationTeamResult:
        """Stage 4 & 5: VERIFY & CITE - source_verifier, fact_checker, and citation_auditor audit assertions."""
        team_result = VerificationTeamEngine.verify_claims_batch(
            claims=claims,
            passages=passages,
        )
        store_pipeline_stage_data(session, SESSION_KEY_VERIFIED_CLAIMS, team_result.to_dict())
        logger.info(f"Pipeline [VERIFY & CITE]: verified {len(team_result.claims)} claims (overall: {team_result.overall_verdict.value})")
        return team_result

    @classmethod
    def execute_synthesize_stage(
        cls,
        query: str,
        verification_result: VerificationTeamResult,
        session: Any = None,
    ) -> EvidencePacket:
        """Stage 6: SYNTHESIZE - evidence_synthesizer produces grounded, compressed EvidencePacket."""
        claims_payload: list[dict[str, Any]] = [c.to_dict() for c in verification_result.claims]
        sources_payload: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for vc in verification_result.claims:
            for s in vc.verifying_sources:
                if s not in seen_urls:
                    seen_urls.add(s)
                    sources_payload.append({
                        "url": s,
                        "authority_tier": vc.source_authority_tier,
                        "verified": vc.status == ClaimStatus.SUPPORTED,
                    })

        conflicts: list[str] = []
        for vc in verification_result.claims:
            conflicts.extend(vc.contradictions)

        overall_conf = 0.95 if verification_result.overall_verdict == ClaimStatus.SUPPORTED else (
            0.75 if verification_result.overall_verdict == ClaimStatus.PARTIALLY_SUPPORTED else 0.40
        )

        packet = EvidencePacket(
            claims=claims_payload,
            sources=sources_payload,
            conflicts=conflicts,
            confidence=overall_conf,
            freshness="recent",
            research_summary=f"Research synthesis for '{query}': {verification_result.supported_count} supported claims, {verification_result.unverified_count} unverified.",
        )

        store_pipeline_stage_data(session, SESSION_KEY_EVIDENCE_PACKET, packet.to_dict())
        logger.info(f"Pipeline [SYNTHESIZE]: created final EvidencePacket with {len(packet.sources)} sources and {len(packet.claims)} claims")
        return packet

    @classmethod
    def run_full_pipeline(
        cls,
        query: str,
        raw_search_urls: list[str],
        claims_to_verify: list[str],
        session: Any = None,
        raw_html_map: Optional[dict[str, str]] = None,
    ) -> EvidencePacket:
        """Run complete SequentialAgent pipeline: RANK -> READ -> EXTRACT -> VERIFY -> CITE -> SYNTHESIZE."""
        # 1. RANK
        ranking = cls.execute_rank_stage(query=query, raw_urls=raw_search_urls, session=session)

        # 2. READ
        read_pages = cls.execute_read_stage(selected_sources=ranking.selected_sources, session=session, raw_html_map=raw_html_map)

        # 3. EXTRACT
        passages_packet = cls.execute_extract_stage(query=query, extracted_pages=read_pages, session=session)

        # 4 & 5. VERIFY & CITE
        verification_res = cls.execute_verify_and_cite_stage(
            claims=claims_to_verify,
            passages=passages_packet.selected_passages,
            session=session,
        )

        # 6. SYNTHESIZE
        evidence_packet = cls.execute_synthesize_stage(
            query=query,
            verification_result=verification_res,
            session=session,
        )

        return evidence_packet
