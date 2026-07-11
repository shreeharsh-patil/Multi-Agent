from datetime import datetime
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class Note(BeanieDocument):
    user_id: str
    title: str
    content: str
    format: str = "markdown"
    tags: list[str] = Field(default_factory=list)
    source_document_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "notes"
        use_state_management = True
