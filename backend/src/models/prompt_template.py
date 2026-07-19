from datetime import datetime, timezone

from beanie import Document as BeanieDocument
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PromptTemplateVersion(BaseModel):
    version: int
    content: str
    variables: list[str] = Field(default_factory=list)
    change_note: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class PromptTemplate(BeanieDocument):
    user_id: str
    name: str
    description: str = ""
    category: str = "General"
    tags: list[str] = Field(default_factory=list)
    current_version: int = 1
    versions: list[PromptTemplateVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "prompt_templates"
        use_state_management = True

