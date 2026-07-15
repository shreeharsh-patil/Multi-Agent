from datetime import datetime, timezone
from beanie import Document as BeanieDocument
from pydantic import Field


class SearchHistory(BeanieDocument):
    user_id: str
    query: str
    answer: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "search_history"
