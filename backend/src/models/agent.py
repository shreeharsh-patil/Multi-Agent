from datetime import datetime, timezone
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class AgentConfig(BeanieDocument):
    user_id: str = "system"
    agent_id: str
    name: str
    description: str
    icon: str = "Bot"
    system_instruction: str = "You are a helpful AI assistant."
    tools: list[str] = Field(default_factory=list)
    custom: bool = True
    enabled: bool = True
    version: str = "0.1.0"
    capabilities: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "agent_configs"
        use_state_management = True


class AgentTask(BeanieDocument):
    agent_id: str
    user_id: str
    input: str
    output: Optional[str] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "agent_tasks"
        use_state_management = True


class ActivityLog(BeanieDocument):
    user_id: str
    type: str
    description: str
    agent_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "activity_logs"
        use_state_management = True
