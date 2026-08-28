"""Internet Intelligence System Evaluation Dataset & Verification Suite.

Tests 10 real-world benchmark query types against the Internet Intelligence System:
1. Timeless explanation queries (e.g. 'What is a linked list?') -> Can skip live search
2. Current events & breaking news -> Live search via google_news_researcher
3. Technical framework versions & releases -> official_docs_researcher + google_search_technology
4. Fact-checking assertions -> google_search_fact_checker + source_verifier
5. Academic literature & preprints -> google_search_academic
6. URL inspection & scraping -> url_reader
7. GitHub open-source repositories -> github_researcher
8. Defensive cybersecurity vulnerabilities -> cybersecurity_researcher
9. Multi-source comparative market research -> multi-agent parallel synthesis
10. Fallback and citation integrity verification
"""

import pytest
from src.agents.registry import AgentRegistry
from src.adk.agents import get_boss_agent, build_all_adk_specialists, reset_adk_agent_tree
from src.adk.internet_provider import (
    INTERNET_PROVIDER_REGISTRY,
    FreshnessRequirement,
    URLCanonicalizer,
    EvidencePacket,
    SourceTier,
)


EVALUATION_DATASET = [
    {
        "id": "eval_01_timeless_concept",
        "category": "timeless_concept",
        "query": "What is a linked list and how does pointer traversal work?",
        "requires_live_search": False,
        "expected_primary_specialist": "coding_manager",
    },
    {
        "id": "eval_02_current_events",
        "category": "current_events",
        "query": "What's new in Google ADK this week and what releases were announced?",
        "requires_live_search": True,
        "expected_primary_specialist": "google_news_researcher",
    },
    {
        "id": "eval_03_technical_version",
        "category": "technical_version",
        "query": "What are the latest features and breaking changes in the Next.js 15 release?",
        "requires_live_search": True,
        "expected_primary_specialist": "official_docs_researcher",
    },
    {
        "id": "eval_04_fact_check",
        "category": "fact_check",
        "query": "Verify whether Python 4.0 was officially released last month.",
        "requires_live_search": True,
        "expected_primary_specialist": "google_search_fact_checker",
    },
    {
        "id": "eval_05_academic_literature",
        "category": "academic_literature",
        "query": "Find recent research papers and benchmark metrics on mixture-of-experts architectures.",
        "requires_live_search": True,
        "expected_primary_specialist": "google_search_academic",
    },
    {
        "id": "eval_06_url_reading",
        "category": "url_reading",
        "query": "Read and inspect this documentation page: https://react.dev/reference/react/useActionState",
        "requires_live_search": True,
        "expected_primary_specialist": "url_reader",
    },
    {
        "id": "eval_07_github_repository",
        "category": "github_repository",
        "query": "Find the best active GitHub open source repositories for local RAG pipelines.",
        "requires_live_search": True,
        "expected_primary_specialist": "github_researcher",
    },
    {
        "id": "eval_08_cybersecurity_vulnerabilities",
        "category": "cybersecurity",
        "query": "What high-severity CVE vulnerabilities and vendor security advisories were reported recently for Next.js?",
        "requires_live_search": True,
        "expected_primary_specialist": "cybersecurity_researcher",
    },
    {
        "id": "eval_09_multi_source_comparison",
        "category": "multi_source_comparison",
        "query": "Compare current AI coding assistants: Cursor, Windsurf, and GitHub Copilot features, pricing in INR, and IDE support.",
        "requires_live_search": True,
        "expected_primary_specialist": "search_planner",
    },
    {
        "id": "eval_10_query_optimizer",
        "category": "query_optimization",
        "query": "best ai thing for coding",
        "requires_live_search": True,
        "expected_primary_specialist": "query_optimizer",
    },
    {
        "id": "eval_11_contradiction_detection",
        "category": "contradiction_detection",
        "query": "Resolve conflicting reports about GPU benchmark FLOPS between vendor whitepaper and independent lab test.",
        "requires_live_search": True,
        "expected_primary_specialist": "contradiction_detector",
    },
    {
        "id": "eval_12_primary_source_hunter",
        "category": "primary_source",
        "query": "Find the official CVE security bulletin and original vendor patch announcement for CVE-2024-34351.",
        "requires_live_search": True,
        "expected_primary_specialist": "primary_source_hunter",
    },
    {
        "id": "eval_13_pricing_monitor",
        "category": "pricing_monitor",
        "query": "What is the current monthly subscription price for Cursor Pro in Indian Rupees?",
        "requires_live_search": True,
        "expected_primary_specialist": "price_monitor_researcher",
    },
    {
        "id": "eval_14_standards_research",
        "category": "standards_research",
        "query": "What does the official RFC 9110 HTTP Semantics specification state regarding idempotent methods?",
        "requires_live_search": True,
        "expected_primary_specialist": "standards_researcher",
    },
]


@pytest.fixture(autouse=True)
def setup_env():
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()
    yield
    reset_adk_agent_tree()


def test_evaluation_dataset_completeness():
    """Verify evaluation dataset contains all required query archetypes."""
    categories = {item["category"] for item in EVALUATION_DATASET}
    assert "timeless_concept" in categories
    assert "current_events" in categories
    assert "technical_version" in categories
    assert "fact_check" in categories
    assert "academic_literature" in categories
    assert "url_reading" in categories
    assert "github_repository" in categories
    assert "cybersecurity" in categories
    assert "multi_source_comparison" in categories
    assert "query_optimization" in categories
    assert "contradiction_detection" in categories
    assert "primary_source" in categories
    assert "pricing_monitor" in categories
    assert "standards_research" in categories


@pytest.mark.parametrize("eval_case", EVALUATION_DATASET, ids=[e["id"] for e in EVALUATION_DATASET])
def test_evaluation_freshness_detection_accuracy(eval_case):
    """Verify freshness requirement classification for all evaluation queries."""
    query = eval_case["query"]
    freshness = INTERNET_PROVIDER_REGISTRY.detect_freshness_requirement(query)

    if eval_case["requires_live_search"]:
        assert freshness in {FreshnessRequirement.REALTIME, FreshnessRequirement.RECENT, FreshnessRequirement.STANDARD}
    else:
        # Timeless questions should not require realtime freshness
        assert freshness != FreshnessRequirement.REALTIME


def test_evaluation_manager_routing_matrix():
    """Verify InternetIntelligenceManager has clear routing rules for every evaluation specialist."""
    boss = get_boss_agent()
    research_mgr = next(m for m in boss.sub_agents if m.name == "research_manager")
    intel_mgr = next(s for s in research_mgr.sub_agents if s.name == "internet_intelligence_manager")
    instruction = intel_mgr.instruction

    for eval_case in EVALUATION_DATASET:
        specialist = eval_case["expected_primary_specialist"]
        if specialist != "coding_manager":
            assert specialist in instruction, f"Specialist {specialist} missing in manager routing rules"


def test_query_optimizer_and_multi_query_generator_agents():
    """Verify Query Optimizer and Multi Query Generator specialist definitions."""
    specialists = build_all_adk_specialists()
    q_opt = specialists["query-optimizer"]
    m_gen = specialists["multi-query-generator"]

    assert q_opt is not None
    assert "Transform ambiguous" in q_opt.instruction or "Query Optimizer" in q_opt.instruction
    assert m_gen is not None
    assert "Broad query" in m_gen.instruction
    assert "Primary-source query" in m_gen.instruction


def test_research_scope_controller_modes():
    """Verify Research Scope Controller defines QUICK, STANDARD, DEEP, CRITICAL, MASSIVE modes."""
    specialists = build_all_adk_specialists()
    scope_ctrl = specialists["research-scope-controller"]
    assert "QUICK" in scope_ctrl.instruction
    assert "STANDARD" in scope_ctrl.instruction
    assert "DEEP" in scope_ctrl.instruction
    assert "CRITICAL" in scope_ctrl.instruction
    assert "MASSIVE" in scope_ctrl.instruction


def test_citation_auditor_and_contradiction_detector():
    """Verify Citation Auditor and Contradiction Detector instructions."""
    specialists = build_all_adk_specialists()
    auditor = specialists["citation-auditor"]
    detector = specialists["contradiction-detector"]

    assert "SUPPORTED" in auditor.instruction
    assert "PARTIAL" in auditor.instruction
    assert "UNSUPPORTED" in auditor.instruction

    assert "conflict" in detector.instruction
    assert "likely_resolution" in detector.instruction


def test_internet_evidence_judge_gatekeeper():
    """Verify Internet Evidence Judge gatekeeper instructions."""
    specialists = build_all_adk_specialists()
    judge = specialists["internet-evidence-judge"]
    assert "final quality gatekeeper" in judge.instruction.lower()
    assert "primary claims supported" in judge.instruction.lower()
