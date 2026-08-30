from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument, Indexed
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    theme: str = "system"
    default_model: str = "gemini-3.6-flash"
    notifications: bool = True
    language: str = "en"
    use_opendocuments_rag: bool = False
    memory_enabled: bool = True
    memory_auto_extract: bool = True


class User(BeanieDocument):
    email: Indexed(str, unique=True)
    name: str
    avatar: Optional[str] = None
    google_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        use_state_management = True
