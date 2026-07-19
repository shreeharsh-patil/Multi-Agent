from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal


ReviewRating = Literal["again", "hard", "good", "easy"]


@dataclass
class ScheduleResult:
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    due_at: datetime


def schedule_review(card, rating: ReviewRating, now: datetime | None = None) -> ScheduleResult:
    """Apply a compact SM-2-style schedule with Anki-like rating choices."""
    now = now or datetime.now(timezone.utc)
    ease = card.ease_factor
    interval = card.interval_days
    repetitions = card.repetitions
    lapses = card.lapses

    if rating == "again":
        ease = max(1.3, ease - 0.2)
        interval = 0
        repetitions = 0
        lapses += 1
        due_at = now + timedelta(minutes=10)
    elif rating == "hard":
        ease = max(1.3, ease - 0.15)
        interval = max(1, round(interval * 1.2))
        repetitions += 1
        due_at = now + timedelta(days=interval)
    elif rating == "good":
        interval = 1 if repetitions == 0 else 6 if repetitions == 1 else max(1, round(interval * ease))
        repetitions += 1
        due_at = now + timedelta(days=interval)
    else:
        ease = min(3.0, ease + 0.15)
        interval = 4 if repetitions == 0 else max(2, round(max(interval, 1) * ease * 1.3))
        repetitions += 1
        due_at = now + timedelta(days=interval)

    return ScheduleResult(ease, interval, repetitions, lapses, due_at)

