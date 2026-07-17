from datetime import datetime, timezone
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class Note(BeanieDocument):
    user_id: str
    workspace_id: Optional[str] = None
    title: str
    content: str
    format: str = "markdown"
    tags: list[str] = Field(default_factory=list)
    source_document_id: Optional[str] = None
    yjs_updates: list[bytes] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notes"
        use_state_management = True

