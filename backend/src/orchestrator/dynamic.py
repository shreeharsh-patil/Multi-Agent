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
    return any(term in text for term in terms)


def plan_dynamic(prompt: str, has_attachments: bool = False, has_workspace: bool = False) -> dict[str, Any]:
    text = prompt.casefold()
    steps: list[dict[str, str]] = []

    def add(agent_id: str, label: str, reason: str, role: str) -> None:
        if agent_id not in {step["agent_id"] for step in steps}:
            steps.append({"agent_id": agent_id, "label": label, "reason": reason, "role": role})

    is_research = _has(
        text,
        "research", "sources", "cite", "citation", "current", "latest", "compare",
        "news", "today", "yesterday", "now", "recent", "trending", "price",
        "update", "version", "event", "who is", "what is the current", "when did",
        "2025", "2026", "score", "winner", "weather",
    )
    is_notes = _has(text, "notes", "revision", "study guide", "exam notes", "summarize", "summary")
    is_quiz = _has(text, "quiz", "mcq", "exam", "practice questions", "flashcards")
    is_code = _has(text, "code", "program", "function", "debug", "bug", "react", "python", "javascript", "api")
    is_security = _has(text, "security", "authentication", "authorization", "password", "encrypt", "vulnerability", "owasp")
    is_document = has_attachments or _has(text, "pdf", "paper", "document", "file", "image", "picture")
    is_visual = _has(text, "diagram", "flowchart", "mind map", "visual", "illustrate", "show me")
    is_math = _has(text, "calculate", "solve", "equation", "formula", "math")
    is_medical = _has(text, "symptom", "disease", "medicine", "drug", "dose", "medical", "health")
    is_finance = _has(text, "finance", "financial", "stock", "invest", "valuation", "accounting", "tax")
    is_planning = _has(text, "plan", "schedule", "roadmap", "deadline", "milestone", "tasks")

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
    elif _has(text, "operating system", "binary tree", "algorithm", "data structure", "computer science"):
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

    # Keep a team focused. A prompt may match many words, but four specialists
    # is enough to cover it without making the user wait for redundant work.
    steps = steps[:4]
    domain = "general"
    for key, value in (("code", "software"), ("research", "research"), ("exam", "study"), ("medical", "medical"), ("finance", "finance")):
        if key in text:
            domain = value
            break
    return {
        "complexity": "complex" if len(steps) >= 3 else ("moderate" if len(steps) == 2 else "simple"),
        "domain": domain,
        "steps": steps,
        "learned_preferences": dict(_routing_history.get(domain, {})),
    }


def record_routing(domain: str, agent_ids: list[str]) -> None:
    for agent_id in agent_ids:
        _routing_history[domain][agent_id] += 1

