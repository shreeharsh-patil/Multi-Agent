"""Intent-driven team planning for automatic chat orchestration.

The planner is deliberately lightweight and deterministic. It chooses a
different set of specialist roles for each prompt, while the specialist
agents themselves remain responsible for using tools and producing evidence.
"""

from collections import defaultdict
import re
from typing import Any


_routing_history: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


def _has(text: str, *terms: str) -> bool:
    """Match intent terms as phrases/tokens instead of arbitrary substrings.

    Raw ``term in text`` caused severe routing collisions: ``plan`` matched
    *explanation*, ``exam`` matched *example*, ``now`` matched *know*, ``api``
    matched *capital*, and ``file`` matched *profile*. Those false positives
    made ordinary chat fan out to unrelated specialist teams.
    """
    for term in terms:
        normalized = term.casefold().strip()
        if not normalized:
            continue
        escaped = re.escape(normalized).replace(r"\ ", r"\s+")
        left = r"(?<!\w)" if normalized[0].isalnum() else ""
        right = r"(?!\w)" if normalized[-1].isalnum() else ""
        if re.search(left + escaped + right, text):
            return True
    return False


def _looks_like_external_entity_question(prompt: str) -> bool:
    return bool(
        re.search(r"(?i)\b(?:what\s+is|who\s+is|tell\s+me\s+about|information\s+about|details\s+about|where\s+is|where's)\b", prompt)
        and (
            re.search(r"\b[A-Z][A-Z0-9&.-]{2,}\b", prompt)
            or re.search(r"(?i)\b(?:college|university|institute|company|organisation|organization|campus|hospital|school)\b", prompt)
        )
    )


def plan_dynamic(prompt: str, has_attachments: bool = False, has_workspace: bool = False) -> dict[str, Any]:
    text = prompt.casefold()
    steps: list[dict[str, str]] = []

    def add(agent_id: str, label: str, reason: str, role: str) -> None:
        if agent_id not in {step["agent_id"] for step in steps}:
            steps.append({"agent_id": agent_id, "label": label, "reason": reason, "role": role})

    is_shopping = _has(
        text,
        "mouse", "mice", "keyboard", "keyboards", "laptop", "laptops", "headphones", "earphones",
        "monitor", "monitors", "ssd", "ssds", "phone", "phones", "mobile", "mobiles", "buy",
        "purchase", "price", "prices", "cheapest", "best under", "deals", "discounts",
        "under ₹", "under rs", "under 500", "under 1000", "under 2000", "under 5000", "under 60000",
    )
    is_scraping = _has(
        text,
        "scrape", "scrapes", "scraped", "scraping", "crawler", "crawlers", "extract text",
        "scrape url", "http://", "https://",
    )

    # Research should be reserved for explicitly requested sourcing or facts
    # whose freshness materially matters. A timeless "compare X and Y" should
    # not automatically invoke the full internet-intelligence hierarchy.
    is_research = _has(
        text,
        "research", "sources", "source", "cite", "citation", "citations",
        "current", "currently", "latest", "newest", "news", "today", "yesterday", "now",
        "recent", "recently", "trending", "price", "prices", "update", "updates", "version",
        "versions", "current events", "breaking", "who is", "what is the current", "2025", "2026",
        "score", "scores", "winner", "weather", "forecast",
    ) or is_shopping or _looks_like_external_entity_question(prompt)
    is_notes = _has(
        text, "note", "notes", "revision", "study guide", "study guides", "exam notes",
        "summarize", "summarise", "summary", "summaries",
    )
    is_quiz = _has(
        text, "quiz", "quizzes", "mcq", "mcqs", "exam", "exams", "practice question",
        "practice questions", "flashcard", "flashcards",
    )
    is_code = _has(
        text, "code", "coding", "program", "programs", "programming", "function", "functions",
        "debug", "debugging", "bug", "bugs", "react", "python", "javascript", "typescript",
        "api", "apis",
    )
    is_security = _has(
        text, "security", "authentication", "authorization", "password", "passwords", "encrypt",
        "encryption", "vulnerability", "vulnerabilities", "owasp",
    )
    is_document = has_attachments or _has(
        text, "pdf", "pdfs", "paper", "papers", "document", "documents", "file", "files",
        "image", "images", "picture", "pictures",
    )
    is_visual = _has(
        text, "diagram", "diagrams", "flowchart", "flowcharts", "mind map", "mind maps",
        "visual", "visualize", "visualise", "illustrate", "show me",
    )
    is_math = _has(text, "calculate", "calculation", "calculations", "solve", "equation", "equations", "formula", "formulas", "math", "mathematics")
    is_medical = _has(
        text, "symptom", "symptoms", "disease", "diseases", "medicine", "medicines", "drug", "drugs",
        "dose", "doses", "medical", "health",
    )
    is_finance = _has(
        text, "finance", "financial", "stock", "stocks", "invest", "investing", "investment",
        "investments", "valuation", "valuations", "accounting", "tax", "taxes",
    )
    is_planning = _has(
        text, "plan", "plans", "planning", "schedule", "schedules", "scheduling", "roadmap", "roadmaps",
        "deadline", "deadlines", "milestone", "milestones", "task", "tasks",
    )

    if is_shopping:
        add("product-researcher", "Product Researcher", "Retrieving live product listings, prices in INR, and verified purchase URLs", "real-time product search and hard budget verification")
        add("price-verification-agent", "Price Verification", "Verifying prices and hard budget constraints", "price and variant verification")
    if is_scraping:
        add("scraping-specialist", "Scraping Specialist", "Extracting HTML body, tables, and structured data from target web page", "web scraping and HTML extraction")
    if is_document:
        add("knowledge", "Knowledge Agent", "Extracting information from the uploaded or referenced material", "knowledge extraction and source grounding")
    if is_research:
        add("research", "Research Agent", "Finding relevant sources and current evidence", "web research and source comparison")
    if is_code:
        add("coding", "Coding Agent", "Working through the implementation or debugging task", "software implementation and code generation")
    if is_security:
        add("hacker", "Security Agent", "Checking security implications and safer patterns", "security review and threat analysis")
    if is_medical:
        add("doctor", "Medical Agent", "Explaining the health topic with appropriate caution", "medical education and clinical context")
    elif is_finance:
        add("finance", "Finance Agent", "Applying the relevant financial reasoning", "finance and valuation analysis")
    elif is_math:
        add("tool", "Reasoning Agent", "Checking calculations and structured reasoning", "calculation and reasoning")
    elif _has(text, "physics", "torque", "force", "energy", "motion", "mechanics"):
        add("engineer", "Physics Expert", "Explaining the physical principles and relationships", "physics and engineering fundamentals")
    elif _has(text, "operating system", "operating systems", "binary tree", "binary trees", "algorithm", "algorithms", "data structure", "data structures", "computer science"):
        add("coding", "CS Expert", "Explaining the computer-science concept precisely", "computer science concepts and examples")

    if is_notes:
        add("notes", "Notes Agent", "Structuring the result into useful study material", "structured notes and revision material")
    if is_quiz:
        add("quiz", "Exam Agent", "Turning the material into active-recall practice", "exam questions and answer explanations")
    if is_planning:
        add("planner", "Planning Agent", "Converting the request into actionable steps", "planning, priorities, and milestones")
    if is_visual:
        # The current registry's engineer agent can produce Mermaid/ASCII
        # diagrams reliably; the role label keeps this visible to the UI.
        add("engineer", "Diagram Agent", "Creating a visual representation of the result", "diagram and visual explanation generation")

    if has_workspace and "knowledge" not in {step["agent_id"] for step in steps}:
        add("knowledge", "Knowledge Agent", "Using the selected workspace as grounded context", "workspace retrieval and citations")

    if not steps:
        if _has(text, "how", "why", "what", "explain", "define", "difference"):
            add("knowledge", "Reasoning Agent", "Building a clear explanation from first principles", "reasoning and educational explanation")
        else:
            add("knowledge", "Answer Agent", "Understanding the request and preparing a direct answer", "general answer generation")

    # Keep a team focused. A prompt may match many terms, but four specialists
    # is enough to cover it without making the user wait for redundant work.
    steps = steps[:4]
    domain = "general"
    if is_code:
        domain = "software"
    elif is_research:
        domain = "research"
    elif is_notes or is_quiz:
        domain = "study"
    elif is_medical:
        domain = "medical"
    elif is_finance:
        domain = "finance"
    return {
        "complexity": "complex" if len(steps) >= 3 else ("moderate" if len(steps) == 2 else "simple"),
        "domain": domain,
        "steps": steps,
        "learned_preferences": dict(_routing_history.get(domain, {})),
    }


def record_routing(domain: str, agent_ids: list[str]) -> None:
    for agent_id in agent_ids:
        _routing_history[domain][agent_id] += 1
