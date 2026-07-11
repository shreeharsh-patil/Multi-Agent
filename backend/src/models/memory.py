from datetime import datetime
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class MemoryItem(BeanieDocument):
    user_id: str
    type: Literal["conversation", "preference", "fact", "semantic"]
    key: str
    content: str
    value: Optional[dict] = None
    embedding: Optional[list[float]] = None
    score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "memory_items"
        use_state_management = True
