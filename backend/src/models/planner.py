from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import Field


class PlannerPlan(BeanieDocument):
    user_id: str
    title: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "planner_plans"
        use_state_management = True
