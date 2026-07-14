from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class Workspace(BeanieDocument):
    user_id: str
    name: str
    description: Optional[str] = None
    color: str = "#7c3aed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workspaces"
