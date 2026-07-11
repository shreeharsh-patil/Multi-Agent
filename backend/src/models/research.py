from datetime import datetime
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class ResearchReport(BeanieDocument):
    user_id: str = "default"
    query: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "research_reports"
        use_state_management = True
