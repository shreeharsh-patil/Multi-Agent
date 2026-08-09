"""Core data structures and lifecycle state for the agentic engine.

These are deliberately plain dataclasses: the engine must work without a
database (tests, cold starts). Persistence is layered on top (see models.py).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Lifecycle enums
# ---------------------------------------------------------------------------

class TaskState:
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


# Official execution statuses shared with the UI / API.
TASK_STATUSES = [
    TaskState.PENDING, TaskState.QUEUED, TaskState.RUNNING, TaskState.WAITING,
    TaskState.COMPLETED, TaskState.FAILED, TaskState.RETRYING,
    TaskState.BLOCKED, TaskState.CANCELLED,
]


@dataclass
class ExecutionResult:
    """Normalized output contract returned by every worker agent."""

    status: str = TaskState.COMPLETED
    result: str = ""
    reasoning_summary: str = ""
    confidence: float = 0.5
    sources: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    unresolved_issues: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    error: str = ""

    @property
    def success(self) -> bool:
        return self.status == TaskState.COMPLETED and bool(self.result and self.result.strip())

    def to_dict(self, agent: str = "", task_id: str = "") -> dict:
        return {
            "taskId": task_id,
            "agent": agent,
            "status": self.status,
            "result": (self.result or "")[:20000],
            "reasoningSummary": self.reasoning_summary,
            "confidence": round(float(self.confidence or 0), 3),
            "sources": self.sources or [],
            "assumptions": self.assumptions or [],
            "warnings": self.warnings or [],
            "unresolvedIssues": self.unresolved_issues or [],
            "recommendations": self.recommendations or [],
            "toolCalls": self.tool_calls or [],
            "error": self.error,
        }


@dataclass
class TaskEvent:
    """Structured observability event emitted throughout a task run."""

    task_id: str = ""
    type: str = ""            # e.g. task_start, plan, wave_start, agent_start ...
    data: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def serialize(self) -> dict:
        return {"type": self.type, "data": self.data, "ts": self.ts, "task_id": self.task_id}


@dataclass
class Subtask:
    """One node in the dynamic task graph."""

    id: str
    title: str
    description: str = ""
    required_capabilities: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)   # subtask ids that must finish first
    parallel: bool = True
    agent_slug: str = ""            # resolved specialist
    status: str = TaskState.QUEUED
    result: ExecutionResult = field(default_factory=ExecutionResult)
    attempts: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "dependencies": self.dependencies,
            "parallel": self.parallel,
            "agentSlug": self.agent_slug,
            "status": self.status,
        }


@dataclass
class TaskRecord:
    """Full in-memory lifecycle record for one Boss task."""

    id: str
    user_id: str = "default"
    request: str = ""
    objective: str = ""
    complexity: str = "medium"
    intent_type: str = "general"
    domains: list = field(default_factory=list)
    subtasks: list = field(default_factory=list)          # list[Subtask]
    selected_agents: list = field(default_factory=list)   # list[dict] brief manifest
    waves: list = field(default_factory=list)             # list[list[str]] subtask ids per wave
    events: list = field(default_factory=list)            # list[TaskEvent]
    final_output: str = ""
    state: str = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    agent_calls: int = 0
    replan_count: int = 0
    error: str = ""

    def emit(self, etype: str, data: dict) -> None:
        self.events.append(TaskEvent(task_id=self.id, type=etype, data=data))

    def summary(self) -> dict:
        return {
            "taskId": self.id,
            "state": self.state,
            "request": self.request,
            "objective": self.objective,
            "complexity": self.complexity,
            "domains": self.domains,
            "selectedAgentCount": len(self.selected_agents),
            "subtaskCount": len(self.subtasks),
            "agentCalls": self.agent_calls,
            "replanCount": self.replan_count,
            "output": self.final_output,
            "latencyMs": round((self.completed_at - self.started_at) * 1000, 2) if self.completed_at >= self.started_at else None,
            "createdAt": self.created_at,
        }


def new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"