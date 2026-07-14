from datetime import datetime, timezone
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    label: str  # A, B, C, D
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: list[QuestionOption]
    correct_answer: str  # e.g. "A"
    explanation: str


class UserAnswer(BaseModel):
    question_index: int
    selected_answer: str
    is_correct: bool
    answered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuizSession(BeanieDocument):
    user_id: str
    topic: str
    difficulty: str = "intermediate"
    question_count: int = 5
    questions: list[QuizQuestion] = Field(default_factory=list)
    answers: list[UserAnswer] = Field(default_factory=list)
    score: Optional[int] = None
    total_questions: int = 0
    completed: bool = False
    source_conversation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "quiz_sessions"
        use_state_management = True
