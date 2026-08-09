from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class AgenticTask(Document):
    """Persistent snapshot of a Boss-agentic run (observability + history)."""

    task_id: str = Field(..., index=True)
    user_id: str = Field(default="default", index=True)
    request: str = ""
    objective: str = ""
    complexity: str = "medium"
    state: str = "PENDING"
    department_counts: dict = Field(default_factory=dict)
    selected_agents: list[dict] = Field(default_factory=list)
    subtask_count: int = 0
    waves: list = Field(default_factory=list)
    final_output: str = ""
    agent_calls: int = 0
    replan_count: int = 0
    events: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: int = 0

    class Settings:
        name = "agentic_tasks"
        use_state_management = True