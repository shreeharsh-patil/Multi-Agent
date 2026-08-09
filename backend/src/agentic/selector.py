"""Capability-based agent selection (Specialist Router + Model Selector).

The Boss never hardcodes "if task == coding use coding agents". Instead the
Boss's decomposition produces ``required_capabilities`` per subtask and this
module scores every enabled agent by capability overlap, priority, cost and
parallelism — returning the smallest sufficient team.
"""

from __future__ import annotations

from src.agentic.agents import ExecutiveRegistry


def capability_overlap(required: list[str], available: list[str]) -> tuple[int, float]:
    """Return (overlap_count, coverage_ratio) of required ∩ available."""
    wanted = {c.strip().lower() for c in required if c and str(c).strip()}
    have = {c.strip().lower() for c in available if c and str(c).strip()}
    if not wanted:
        return 0, 0.0
    overlap = len(wanted & have)
    return overlap, overlap / len(wanted)


def select_agent_for_subtask(
    subtask,
    registry: ExecutiveRegistry | None = None,
    exclude: set | None = None,
) -> dict:
    """Pick the single best specialist for a subtask.

    Returns a dict with the chosen agent slug, name, department, the coverage
    score, and every capability of the subtask that no agent covers (gaps).
    """
    registry = registry or ExecutiveRegistry.get()
    required = list(subtask.required_capabilities or [])
    exclude = exclude or set()

    best: tuple[int, float, object] | None = None
    best_agent = None
    uncovered = set(required)
    for agent in registry.all_agents():
        manifest = agent.manifest
        if not manifest.enabled or manifest.id in exclude:
            continue
        overlap, _ = capability_overlap(required, manifest.capabilities)
        uncovered -= {c for c in manifest.capabilities if c in required}
        if overlap <= 0:
            continue
        # Priority + overlap; small cost tie-break, prefer live parallel-safe agents
        score = overlap * 100 + (manifest.priority / 10.0) - manifest.cost_weight
        if not manifest.can_run_in_parallel:
            score -= 5
        candidate = (score, manifest.priority)
        if best is None or candidate > best:
            best = candidate
            best_agent = agent

    if best_agent is None:
        return {
            "found": False,
            "slug": "",
            "name": "",
            "department": "",
            "score": 0.0,
            "capability_gaps": sorted(uncovered),
        }

    overlap, coverage = capability_overlap(required, best_agent.manifest.capabilities)
    return {
        "found": True,
        "slug": best_agent.manifest.id,
        "name": best_agent.manifest.name,
        "department": best_agent.manifest.department,
        "score": round(overlap * 100 + best_agent.manifest.priority / 10.0, 2),
        "coverage": round(coverage, 2),
        "model_tier": best_agent.manifest.model_tier,
        "capability_gaps": [c for c in required if c not in best_agent.manifest.capabilities],
    }


def build_team_plan(subtasks, registry: ExecutiveRegistry | None = None) -> tuple[list[dict], list[str]]:
    """Resolve a specialist for every subtask.

    Returns (assignments, gaps) where assignments is one dict per subtask and
    gaps lists capability tags that no registered agent covers.
    """
    registry = registry or ExecutiveRegistry.get()
    used: set[str] = set()
    assignments: list[dict] = []
    all_gaps: list[str] = []
    for subtask in subtasks:
        chosen = select_agent_for_subtask(subtask, registry=registry, exclude=used)
        if chosen.get("found"):
            used.add(chosen["slug"])
        else:
            # No exclusive match — allow re-use of an agent rather than dropping the subtask.
            chosen = select_agent_for_subtask(subtask, registry=registry)
        assignment = {
            "subtask_id": subtask.id,
            "title": subtask.title,
            **chosen,
            "available_tools": _granted_tools(chosen, subtask),
        }
        assignments.append(assignment)
        all_gaps.extend(chosen.get("capability_gaps", []))

    unique_gaps: list[str] = []
    for g in all_gaps:
        if g not in unique_gaps:
            unique_gaps.append(g)
    return assignments, unique_gaps


def _granted_tools(chosen: dict, subtask) -> list[str]:
    from src.agentic.tools import tools_for_capabilities
    granted = tools_for_capabilities(subtask.required_capabilities)
    if chosen.get("found"):
        agent = ExecutiveRegistry.get().get_agent(chosen["slug"])
        if agent:
            declared = set(agent.manifest.required_tools + agent.manifest.optional_tools)
            granted = [t for t in granted if t in declared]
    return granted


def model_tier_for_complexity(complexity: str) -> str:
    """Cheap routing heuristic: simple classification uses fewer tokens/lighter tier."""
    if complexity == "low":
        return "cheap"
    if complexity in {"high", "critical"}:
        return "strong"
    return "balanced"