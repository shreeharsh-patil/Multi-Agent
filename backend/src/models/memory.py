from datetime import datetime, timezone
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class MemoryItem(BeanieDocument):
    user_id: str
    type: Literal["conversation", "preference", "fact", "semantic", "goal", "constraint"]
    key: str
    content: str
    value: Optional[dict] = None
    embedding: Optional[list[float]] = None
    category: str = "general"
    confidence: float = 0.7
    status: Literal["active", "superseded", "archived"] = "active"
    source_conversation_id: Optional[str] = None
    evidence: Optional[str] = None
    pinned: bool = False
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "memory_items"
        use_state_management = True
