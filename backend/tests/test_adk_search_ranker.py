"""Unit tests for Phase 6: ADK Search Result Ranker Agent, Primary-Source Authority, Diversity, and Schema Validation."""

import json
import pytest
from google.adk.agents import LlmAgent

from src.adk.search_ranker import (
    SearchResultRanker,
    SearchResultRanking,
    RankedSource,
    RejectedSource,
)
from src.adk.tools import rank_search_results, rank_search_results_tool
from src.adk.agents import create_search_result_ranker_agent


def test_search_result_ranker_agent_instantiation_and_tools():
    """Verify search_result_ranker is an LlmAgent equipped with rank_search_results_tool."""
    agent = create_search_result_ranker_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "search_result_ranker"
    assert len(agent.tools) == 1
    assert agent.tools[0] is rank_search_results_tool
    assert "RANKING CRITERIA" in agent.instruction
    assert "AUTHORITY PRIORITY ORDER" in agent.instruction
    assert "selected_sources" in agent.instruction


def test_nextjs_security_fix_example_ranking():
    """Verify example query 'Latest Next.js security fix' prioritizes official/CVE sources over blogs/SEO aggregators."""
    query = "Latest Next.js security fix"
    raw_results = [
        {
            "url": "https://nextjs.org/blog/security-update-2026",
            "title": "Next.js Security Update Advisory - Official Next.js Blog",
            "snippet": "Official patch notes and critical security fix for Next.js SSR vulnerability.",
            "published_date": "2026-08-20",
        },
        {
            "url": "https://github.com/vercel/next.js/security/advisories/GHSA-1234",
            "title": "GitHub Advisory: Next.js SSR Remote Code Execution",
            "snippet": "Official GitHub advisory and patch release information for CVE-2026-9999.",
            "published_date": "2026-08-20",
        },
        {
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
            "title": "CVE-2026-9999 Detail - National Vulnerability Database",
            "snippet": "NVD official CVE score and vulnerability assessment for Next.js package.",
            "published_date": "2026-08-21",
        },
        {
            "url": "https://geeksforgeeks.org/what-is-nextjs-security-tutorial",
            "title": "Next.js Security Best Practices - GeeksforGeeks",
            "snippet": "Learn basic Next.js security concepts and web tutorial overview.",
            "published_date": "2023-01-01",
        },
        {
            "url": "https://medium.com/@randomuser/my-thoughts-on-nextjs-bug",
            "title": "Why I dislike this Next.js bug - Personal Blog",
            "snippet": "Opinion piece on JavaScript frameworks.",
            "published_date": "2026-08-22",
        },
        {
            "url": "https://w3schools.com/nextjs/security_intro",
            "title": "W3Schools Next.js Tutorial",
            "snippet": "Generic tutorial overview.",
            "published_date": "2022-05-10",
        },
    ]

    ranking = SearchResultRanker.rank_sources(query=query, results=raw_results, max_selected=3)

    assert isinstance(ranking, SearchResultRanking)
    selected_urls = [s["url"] for s in ranking.selected_sources]
    rejected_urls = [r["url"] for r in ranking.rejected_sources]

    # Verify official/CVE sources are selected
    assert "https://nextjs.org/blog/security-update-2026" in selected_urls
    assert "https://github.com/vercel/next.js/security/advisories/GHSA-1234" in selected_urls
    assert "https://nvd.nist.gov/vuln/detail/CVE-2026-9999" in selected_urls

    # Verify SEO aggregators and opinion blogs are rejected
    assert "https://geeksforgeeks.org/what-is-nextjs-security-tutorial" in rejected_urls
    assert "https://medium.com/@randomuser/my-thoughts-on-nextjs-bug" in rejected_urls
    assert "https://w3schools.com/nextjs/security_intro" in rejected_urls


def test_exact_structured_output_schema():
    """Verify ranker outputs exact JSON schema with selected_sources, rejected_sources, and reasoning_summary."""
    query = "Python 3.14 release notes"
    raw_results = [
        {"url": "https://docs.python.org/3.14/whatsnew/3.14.html", "title": "What's New in Python 3.14", "snippet": "Official release notes"},
        {"url": "https://geeksforgeeks.org/python-314-features", "title": "Python 3.14 Overview", "snippet": "Tutorial"},
    ]

    ranking_json = rank_search_results(query, raw_results, max_selected=2)
    parsed = json.loads(ranking_json)

    assert "selected_sources" in parsed
    assert "rejected_sources" in parsed
    assert "reasoning_summary" in parsed

    assert isinstance(parsed["selected_sources"], list)
    assert isinstance(parsed["rejected_sources"], list)
    assert isinstance(parsed["reasoning_summary"], list)

    for item in parsed["selected_sources"]:
        assert "url" in item
        assert "title" in item
        assert "tier" in item
        assert "score" in item
        assert "rank_reason" in item

    for item in parsed["rejected_sources"]:
        assert "url" in item
        assert "title" in item
        assert "rejection_reason" in item


def test_diversity_cap_prevents_single_domain_domination():
    """Verify maximum of 2 links per domain are selected to preserve diversity."""
    query = "Google DeepMind Gemini updates"
    raw_results = [
        {"url": "https://blog.google/technology/ai/gemini-update-1", "title": "Gemini Update 1", "snippet": "News 1"},
        {"url": "https://blog.google/technology/ai/gemini-update-2", "title": "Gemini Update 2", "snippet": "News 2"},
        {"url": "https://blog.google/technology/ai/gemini-update-3", "title": "Gemini Update 3", "snippet": "News 3"},
        {"url": "https://ai.google.dev/docs/gemini_api", "title": "Gemini API Official Docs", "snippet": "API Docs"},
        {"url": "https://techcrunch.com/2026/08/gemini-announcement", "title": "TechCrunch Gemini Review", "snippet": "Tech News"},
    ]

    ranking = SearchResultRanker.rank_sources(query=query, results=raw_results, max_selected=5)

    domain_counts = {}
    for s in ranking.selected_sources:
        d = s["url"].split("/")[2].replace("www.", "")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    # Verify no domain exceeds the diversity cap of 2
    for d, count in domain_counts.items():
        assert count <= 2

    # Verify excess blog.google result was rejected for diversity
    assert any("diversity cap" in r["rejection_reason"].lower() for r in ranking.rejected_sources)
