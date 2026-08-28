"""Phase 15 Tests: Automatic Web Research for Fresh Information.

Tests automatic routing for:
1. latest
2. today
3. current
4. recent
5. right now
6. this week
7. this month
8. price
9. available
10. availability
11. news
12. release
13. version
14. score
15. weather
16. market
17. stock
18. company status
19. security advisory
20. GitHub activity

Examples tested:
- "What is OOP?" -> no web
- "What's new in Python?" -> web
- "Explain React hooks" -> usually no web
- "What's the latest React version?" -> web
- "Is Python 4 released?" -> fact-check search
- "Find the latest Google ADK changes" -> official docs + GitHub + Google Search
"""

import pytest

from src.services.freshness_analyzer import freshness_analyzer, FreshnessLevel
from src.adk.sequential_pipeline import ResearchHierarchyCoordinator
from src.adk.search_plan import IntelligentSearchPlanner, SearchPlanMode


@pytest.mark.parametrize(
    "query,trigger_name",
    [
        ("What is the latest React version?", "latest"),
        ("Tech news today", "today"),
        ("Current CEO of Microsoft", "current"),
        ("Recent breakthroughs in generative AI", "recent"),
        ("Bitcoin price right now", "right now"),
        ("Major tech announcements this week", "this week"),
        ("AI framework releases this month", "this month"),
        ("What is the iPhone 16 price in India?", "price"),
        ("Is the RTX 5090 available for purchase?", "available"),
        ("Check PS5 Pro stock availability", "availability"),
        ("Breaking space exploration news", "news"),
        ("NextJS 15 official release notes", "release"),
        ("What version of Python is recommended for production?", "version"),
        ("Live match score India vs England", "score"),
        ("What is the weather in Mumbai?", "weather"),
        ("Global semiconductor market growth", "market"),
        ("Tesla stock performance and valuation", "stock"),
        ("Anthropic company status and public funding", "company status"),
        ("OpenSSL critical security advisory CVE-2026", "security advisory"),
        ("Google ADK github activity and latest commits", "github activity"),
    ],
)
def test_all_20_automatic_search_triggers(query: str, trigger_name: str):
    """Phase 15: Verify all 20 required search trigger terms automatically invoke web research."""
    # 1. Test FreshnessAnalyzer semantic analysis
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is True, f"Trigger '{trigger_name}' in query '{query}' must require research"

    # 2. Test ResearchHierarchyCoordinator web intent evaluation
    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is True, f"Intent for '{query}' must have requires_internet=True"


def test_example_what_is_oop_no_web():
    """Phase 15 Example 1: 'What is OOP?' -> no web."""
    query = "What is OOP?"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is False
    assert freshness["level"] == FreshnessLevel.STATIC

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is False
    assert intent["intent_type"] == "timeless_concept"


def test_example_whats_new_in_python_web():
    """Phase 15 Example 2: 'What's new in Python?' -> web."""
    query = "What's new in Python?"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is True

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is True

    plan = IntelligentSearchPlanner.generate_plan(query, mode=SearchPlanMode.STANDARD)
    assert len(plan.queries) >= 1
    assert any("python" in q.query.lower() for q in plan.queries)


def test_example_explain_react_hooks_no_web():
    """Phase 15 Example 3: 'Explain React hooks' -> usually no web."""
    query = "Explain React hooks"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is False
    assert freshness["level"] == FreshnessLevel.STATIC

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is False
    assert intent["intent_type"] == "timeless_concept"


def test_example_whats_the_latest_react_version_web():
    """Phase 15 Example 4: 'What's the latest React version?' -> web."""
    query = "What's the latest React version?"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is True

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is True

    plan = IntelligentSearchPlanner.generate_plan(query, mode=SearchPlanMode.STANDARD)
    assert len(plan.queries) >= 1
    agents_assigned = {q.agent for q in plan.queries}
    assert "release_notes_agent" in agents_assigned or "official_docs_researcher" in agents_assigned or "google_search_technology" in agents_assigned


def test_example_is_python_4_released_fact_check_search():
    """Phase 15 Example 5: 'Is Python 4 released?' -> fact-check search."""
    query = "Is Python 4 released?"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is True

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is True
    assert intent["intent_type"] == "fact_check"

    plan = IntelligentSearchPlanner.generate_plan(query, mode=SearchPlanMode.STANDARD)
    agents_assigned = {q.agent for q in plan.queries}
    # Must route to fact-checking and primary source verification
    assert "google_search_fact_checker" in agents_assigned
    assert "official_docs_researcher" in agents_assigned or "primary_source_hunter" in agents_assigned


def test_example_find_latest_google_adk_changes_multi_source():
    """Phase 15 Example 6: 'Find the latest Google ADK changes' -> official docs + GitHub + Google Search."""
    query = "Find the latest Google ADK changes"
    freshness = freshness_analyzer.analyze(query)
    assert freshness["research_required"] is True

    intent = ResearchHierarchyCoordinator.evaluate_web_intent(query)
    assert intent["requires_internet"] is True
    assert intent["intent_type"] == "multi_source_changes"

    plan = IntelligentSearchPlanner.generate_plan(query, mode=SearchPlanMode.STANDARD)
    agents_assigned = {q.agent for q in plan.queries}
    # Must coordinate official docs + GitHub + Google Search technology specialist
    assert "official_docs_researcher" in agents_assigned
    assert "github_researcher" in agents_assigned
    assert "google_search_technology" in agents_assigned


def test_additional_static_concepts_bypass_web():
    """Phase 15: Verify additional timeless computer science and educational questions bypass web search."""
    static_queries = [
        "What is recursion?",
        "Explain binary search algorithm",
        "How does a linked list work?",
        "What is polymorphism in OOP?",
        "Explain dynamic programming",
        "Calculate 25 * 4 + 10",
    ]
    for q in static_queries:
        freshness = freshness_analyzer.analyze(q)
        assert freshness["research_required"] is False, f"Query '{q}' should be static"
        intent = ResearchHierarchyCoordinator.evaluate_web_intent(q)
        assert intent["requires_internet"] is False, f"Intent for '{q}' should not require internet"
