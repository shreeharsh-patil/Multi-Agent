"""Task-scoped shared memory.

Separation of concerns (never dump the whole conversation into every agent):
* user context   — the original request, memory context, attachments summary
* subtask results — keyed by subtask id (chained agent-to-agent handoffs)
* tool results   — scoped per subtask
* planning state — objective, constraints, domains

``TaskMemory.relevant_context(subtask)`` returns only the results of that
subtask's declared dependencies plus a compact global summary — enough for a
handoff, without drowning agents in the full transcript.
"""

from __future__ import annotations

MAX_HELPER_CHARS = 6000


class TaskMemory:
    def __init__(self, task_id: str, user_context: dict | None = None):
        self.task_id = task_id
        self.user_context: dict = dict(user_context or {})
        self._results: dict[str, dict] = {}      # subtask_id -> result payload
        self._tool_results: dict[str, list[str]] = {}  # subtask_id -> evidence blocks
        self.objective: str = ""
        self.constraints: list[str] = []
        self.domains: list[str] = []

    # --- writers ----------------------------------------------------------

    def store_result(self, subtask_id: str, result_payload: dict) -> None:
        self._results[subtask_id] = result_payload

    def store_tool_evidence(self, subtask_id: str, block: str) -> None:
        captured = block or ""
        if captured:
            self._tool_results.setdefault(subtask_id, []).append(captured[:4000])

    def has_result(self, subtask_id: str) -> bool:
        payload = self._results.get(subtask_id)
        return bool(payload and (payload.get("result") or "").strip())

    # --- readers ----------------------------------------------------------

    def result_for(self, subtask_id: str) -> dict | None:
        return self._results.get(subtask_id)

    def previous_results(self, subtask_id: str, dependencies: list[str]) -> list[dict]:
        out = []
        for dep in dependencies or []:
            payload = self._results.get(dep)
            if payload and (payload.get("result") or "").strip():
                out.append({
                    "agent": payload.get("agent", dep),
                    "source": dep,
                    "result": (payload.get("result") or "")[:MAX_HELPER_CHARS],
                    "confidence": payload.get("confidence"),
                })
        return out

    def summary(self, max_chars: int = 3000) -> str:
        """Compact human/machine-readable snapshot of the shared task state."""
        lines = []
        if self.objective:
            lines.append(f"Objective: {self.objective}")
        if self.domains:
            lines.append("Domains: " + ", ".join(self.domains))
        # Include the latest successful sub-results (agent-to-agent handoffs)
        entries = [(sid, p) for sid, p in self._results.items() if (p.get("result") or "").strip()]
        if entries:
            lines.append("Completed sub-deliverables:")
            for sid, p in entries[-8:]:
                preview = (p.get("result") or "")[:600].replace("\n", " ")
                lines.append(f"- [{sid}] {p.get('agent', sid)}: {preview}")
        return "\n".join(lines)[:max_chars]

    def relevant_context(self, subtask_id: str, dependencies: list[str]) -> dict:
        """Build the scoped context dict delivered to one worker."""
        return {
            "summary": self.summary(),
            "previous_results": self.previous_results(subtask_id, dependencies),
            "tool_evidence": self._tool_results.get(subtask_id, [])[-6:][::-1],
        }

    def export(self) -> dict:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "constraints": self.constraints,
            "domains": self.domains,
            "user_context_keys": sorted(self.user_context.keys()),
            "results": {k: {"agent": v.get("agent"), "snippet": (v.get("result") or "")[:200]} for k, v in self._results.items()},
        }