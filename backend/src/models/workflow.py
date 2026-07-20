"""Workflow DAG persistence model."""

from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import BaseModel, Field


class WorkflowNodeModel(BaseModel):
    """One node in the DAG."""
    id: str
    agent_id: str
    label: str
    x: float = 0.0
    y: float = 0.0


class WorkflowEdgeModel(BaseModel):
    """Directed connection between two nodes."""
    id: str
    source: str   # node id
    target: str   # node id


class WorkflowDAG(BeanieDocument):
    """Persisted workflow definition."""
    user_id: str = "default"
    name: str = "Untitled Workflow"
    description: str = ""
    nodes: list[WorkflowNodeModel] = Field(default_factory=list)
    edges: list[WorkflowEdgeModel] = Field(default_factory=list)
    prompt: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workflow_dags"
        use_state_management = True


class WorkflowRun(BeanieDocument):
    """Execution record for a workflow run."""
    workflow_id: str
    user_id: str = "default"
    prompt: str
    status: str = "pending"   # pending | running | complete | error
    node_results: list[dict] = Field(default_factory=list)
    final_output: str = ""
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    class Settings:
        name = "workflow_runs"
        use_state_management = True
