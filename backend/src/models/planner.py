from datetime import datetime
from typing import Optional, Literal
from beanie import Document as BeanieDocument
from pydantic import Field


class PlannerPlan(BeanieDocument):
    user_id: str = "default"
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "planner_plans"
        use_state_management = True
