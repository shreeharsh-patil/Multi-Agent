from datetime import datetime, timezone
from typing import Optional

from beanie import Document as BeanieDocument
from pydantic import Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FlashcardDeck(BeanieDocument):
    user_id: str
    name: str
    description: str = ""
    workspace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "flashcard_decks"
        use_state_management = True


class Flashcard(BeanieDocument):
    user_id: str
    deck_id: str
    front: str
    back: str
    tags: list[str] = Field(default_factory=list)
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    lapses: int = 0
    due_at: datetime = Field(default_factory=utc_now)
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "flashcards"
        use_state_management = True


class FlashcardReview(BeanieDocument):
    user_id: str
    card_id: str
    deck_id: str
    rating: str
    previous_interval_days: int
    next_interval_days: int
    reviewed_at: datetime = Field(default_factory=utc_now)
    next_due_at: datetime

    class Settings:
        name = "flashcard_reviews"

