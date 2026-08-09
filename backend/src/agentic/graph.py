"""Dynamic task graph: build waves (parallel buckets) from dependencies.

Algorithms are pure functions so they are trivially testable without the LLM.
"""

from __future__ import annotations

from collections import deque


def detect_cycles(subtasks) -> str | None:
    """Return the offending subtask id on a dependency cycle, else None."""
    edges: dict[str, list[str]] = {}
    for s in subtasks:
        edges[s["id"]] = list(s.get("dependencies") or [])
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {sid: WHITE for sid in edges}

    def visit(node: str) -> str | None:
        color[node] = GRAY
        for dep in edges.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                return dep
            if color[dep] == WHITE:
                found = visit(dep)
                if found:
                    return found
        color[node] = BLACK
        return None

    for node in edges:
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def normalize_dependencies(subtasks) -> list[dict]:
    """Validate subtask ids, drop unknown/self dependency references.

    A dependency on a nonexistent subtask is a correctness bug: it would make
    the graph wait forever. We drop such references instead of fabricating a
    node. Self-references are also removed.
    """
    ids = {s["id"] for s in subtasks}
    normalized = []
    for s in subtasks:
        deps = []
        for d in s.get("dependencies") or []:
            if d in ids and d != s["id"] and d not in deps:
                deps.append(d)
        normalized.append({**s, "dependencies": deps})
    return normalized


def build_waves(subtasks) -> list[list[str]]:
    """Topologically order subtasks into parallel waves.

    A wave is a set of subtasks with no unmet dependencies once all previous
    waves finished. Subtasks with no dependencies land in wave 0. If a cycle
    exists, dependency edges are ignored for the remaining nodes so execution
    can still proceed (cycle is already reported by detect_cycles).
    """
    subtasks = list(subtasks)
    ids = {s["id"] for s in subtasks}
    ready_of: dict[str, set[str]] = {}
    dependents: dict[str, list[str]] = {}
    for s in subtasks:
        deps = [d for d in (s.get("dependencies") or []) if d in ids and d != s["id"]]
        ready_of[s["id"]] = set(deps)
        for d in deps:
            dependents.setdefault(d, []).append(s["id"])

    rev = {s["id"]: s for s in subtasks}
    waves: list[list[str]] = []
    remaining = set(ids)
    # Break cycles deterministically by prioritizing earlier subtasks.
    order_by_index = {s["id"]: i for i, s in enumerate(subtasks)}

    while remaining:
        wave = sorted(
            (sid for sid in remaining if not ready_of[sid] & remaining),
            key=lambda sid: (order_by_index[sid]),
        )
        if not wave:
            # Cycle: drop the dependency of the earliest remaining node.
            victim = min(remaining, key=lambda sid: order_by_index[sid])
            # Finding a suitable edge to cut: clear that node's blockers.
            ready_of[victim] = set()
            continue
        waves.append(wave)
        remaining -= set(wave)

    return waves


def is_blocked(subtask_status: str) -> bool:
    return subtask_status in {"BLOCKED", "CANCELLED"}


def max_depth(subtasks) -> int:
    """Longest dependency chain length (for infinite-loop/run-depth guards)."""
    longest: dict[str, int] = {}
    for s in subtasks:
        longest.setdefault(s["id"], len(s.get("dependencies") or []))
    # simple upper bound: number of nodes is the natural ceiling
    return max(len(longest), 1)


def validate_graph(subtasks) -> dict:
    """Run all structural validations; returns {valid, cycle, waves, max_depth}."""
    cycle = detect_cycles(subtasks)
    try:
        waves = build_waves(subtasks)
        valid = cycle is None
    except RecursionError:
        waves = []
        valid = False
        cycle = cycle or "recursion-depth"
    return {
        "valid": valid,
        "cycle": cycle,
        "waves": waves,
        "max_depth": max_depth(subtasks),
        "node_count": len(subtasks),
    }