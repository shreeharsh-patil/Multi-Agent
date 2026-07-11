from datetime import datetime
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class Citation(BeanieDocument):
    file_name: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    text: str
    score: Optional[float] = None


class ToolCall(BeanieDocument):
    id: str
    name: str
    arguments: dict = Field(default_factory=dict)


class ToolResult(BeanieDocument):
    id: str
    name: str
    result: Optional[dict] = None
    error: Optional[str] = None


class Message(BeanieDocument):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    agent_id: Optional[str] = None
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BeanieDocument):
    user_id: str
    title: str = "New Conversation"
    agent_id: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"
        use_state_management = True
