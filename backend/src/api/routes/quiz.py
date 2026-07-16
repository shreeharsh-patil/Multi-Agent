"""Quiz generation, answer checking, and history API routes."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.models.quiz import QuizSession, QuizQuestion, QuestionOption, UserAnswer
from src.adk.runner import process_message
from src.utils.logger import logger

router = APIRouter(prefix="/api/quiz", tags=["Quiz"])


# ── Request / Response Models ──────────────────────────────────────────


class GenerateRequest(BaseModel):
    topic: str
    difficulty: str = "intermediate"
    question_count: int = 5
    user_id: str = "default"


class GenerateResponse(BaseModel):
    quiz_id: str
    topic: str
    difficulty: str
    questions: list[dict]


class CheckAnswerRequest(BaseModel):
    quiz_id: str
    question_index: int
    selected_answer: str


class SubmitRequest(BaseModel):
    quiz_id: str


class QuizSummary(BaseModel):
    id: str
    topic: str
    difficulty: str
    score: Optional[int] = None
    total_questions: int
    completed: bool
    created_at: str


# ── Prompt templates ───────────────────────────────────────────────────


def _build_generation_prompt(topic: str, difficulty: str, count: int) -> str:
    return (
        f"Generate exactly {count} multiple-choice questions about '{topic}' "
        f"at a {difficulty} difficulty level.\n\n"
        "For each question, provide:\n"
        "- The question text\n"
        "- 4 options labeled A, B, C, D\n"
        "- The correct answer letter\n"
        "- A brief explanation of why it's correct\n\n"
        f"Return the response as valid JSON ONLY with this exact structure (no markdown, no code fences):\n"
        '{{\n'
        '  "questions": [\n'
        '    {{\n'
        '      "question": "...",\n'
        '      "options": [\n'
        '        {{"label": "A", "text": "..."}},\n'
        '        {{"label": "B", "text": "..."}},\n'
        '        {{"label": "C", "text": "..."}},\n'
        '        {{"label": "D", "text": "..."}}\n'
        '      ],\n'
        '      "correct_answer": "A",\n'
        '      "explanation": "..."\n'
        '    }}\n'
        '  ]\n'
        '}}\n\n'
        f"Ensure all {count} questions are unique and test different aspects of the topic."
    )


def _build_check_prompt(
    topic: str,
    question: str,
    options: list[dict],
    correct_answer: str,
    explanation: str,
    selected_answer: str,
) -> str:
    return (
        f"Topic: {topic}\n\n"
        f"Question: {question}\n\n"
        f"Options:\n"
        + "\n".join(f"{o['label']}. {o['text']}" for o in options) +
        f"\n\nCorrect answer: {correct_answer}\n"
        f"Explanation: {explanation}\n"
        f"User selected: {selected_answer}\n\n"
        "Is the user's answer correct? Provide a brief response confirming if they got it right "
        "or wrong, and explain why in 1-2 sentences."
    )


# ── Helper: parse JSON from LLM output ────────────────────────────────


def _extract_json(text: str) -> Optional[dict]:
    """Extract a JSON object from LLM text response, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        # Find the first { after ```
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= 0:
            text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse quiz JSON from LLM output: {text[:200]}")
        return None


# ── Routes ─────────────────────────────────────────────────────────────


@router.post("/generate", response_model=GenerateResponse)
async def generate_quiz(body: GenerateRequest, http_request: Request) -> GenerateResponse:
    """Generate multiple-choice questions on a topic using the LLM.

    Creates a QuizSession to track the generated questions and
    later answers.
    """
    if body.question_count < 1 or body.question_count > 20:
        raise HTTPException(400, "question_count must be between 1 and 20")

    # Use authenticated user from JWT if available
    auth_user = getattr(http_request.state, "user", None)
    user_id = (auth_user.get("sub") if auth_user else None) or body.user_id

    prompt = _build_generation_prompt(body.topic, body.difficulty, body.question_count)
    conv_id = str(uuid.uuid4())

    try:
        result = await process_message(
            message=prompt,
            user_id=user_id,
            conversation_id=conv_id,
        )
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(500, f"Failed to generate quiz: {str(e)}")

    output = result.get("output", "")
    parsed = _extract_json(output)

    if not parsed or "questions" not in parsed:
        logger.warning(f"LLM returned unparseable quiz output. Raw: {output[:300]}")
        raise HTTPException(500, "Failed to generate valid quiz questions. Please try again.")

    questions_data = parsed["questions"]
    if not questions_data:
        raise HTTPException(500, "No questions generated. Please try again.")

    # Build domain model objects
    questions: list[QuizQuestion] = []
    for q in questions_data:
        options = [QuestionOption(label=o["label"], text=o["text"]) for o in q.get("options", [])]
        questions.append(
            QuizQuestion(
                question=q["question"],
                options=options,
                correct_answer=q.get("correct_answer", "A"),
                explanation=q.get("explanation", ""),
            )
        )

    # Persist to MongoDB
    session = QuizSession(
        user_id=user_id,
        topic=body.topic,
        difficulty=body.difficulty,
        question_count=body.question_count,
        questions=questions,
        total_questions=len(questions),
        source_conversation_id=conv_id,
    )
    await session.insert()

    # Return serializable dicts (hide correct_answer / explanation until submission)
    serialized = [
        {
            "question": q.question,
            "options": [{"label": o.label, "text": o.text} for o in q.options],
        }
        for q in questions
    ]

    return GenerateResponse(
        quiz_id=str(session.id),
        topic=body.topic,
        difficulty=body.difficulty,
        questions=serialized,
    )


@router.post("/check")
async def check_answer(body: CheckAnswerRequest, http_request: Request) -> dict:
    """Check whether the user's answer is correct, and return a brief explanation.

    Also records the answer in the QuizSession so it can be graded later.
    """
    session = await QuizSession.get(body.quiz_id)
    if not session:
        raise HTTPException(404, "Quiz session not found")

    if body.question_index < 0 or body.question_index >= len(session.questions):
        raise HTTPException(400, "Invalid question index")

    question = session.questions[body.question_index]
    is_correct = body.selected_answer.upper() == question.correct_answer.upper()

    # Check if user already answered this question — update rather than append
    existing = [a for a in session.answers if a.question_index == body.question_index]
    if existing:
        existing[0].selected_answer = body.selected_answer
        existing[0].is_correct = is_correct
    else:
        session.answers.append(
            UserAnswer(
                question_index=body.question_index,
                selected_answer=body.selected_answer,
                is_correct=is_correct,
            )
        )
    session.updated_at = datetime.now(timezone.utc)
    await session.save()

    return {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }


@router.post("/submit")
async def submit_quiz(body: SubmitRequest, http_request: Request) -> dict:
    """Finalize a quiz session, calculating the score and marking it complete."""
    session = await QuizSession.get(body.quiz_id)
    if not session:
        raise HTTPException(404, "Quiz session not found")

    score = sum(1 for a in session.answers if a.is_correct)
    session.score = score
    session.completed = True
    session.updated_at = datetime.now(timezone.utc)
    await session.save()

    # Return full results with correct answers and explanations
    results = []
    for i, q in enumerate(session.questions):
        user_answer = next((a for a in session.answers if a.question_index == i), None)
        results.append({
            "question_index": i,
            "question": q.question,
            "options": [{"label": o.label, "text": o.text} for o in q.options],
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "user_answer": user_answer.selected_answer if user_answer else None,
            "is_correct": user_answer.is_correct if user_answer else None,
        })

    return {
        "quiz_id": str(session.id),
        "topic": session.topic,
        "score": score,
        "total_questions": session.total_questions,
        "percentage": round((score / session.total_questions) * 100, 1) if session.total_questions else 0,
        "completed": True,
        "results": results,
    }


@router.get("/history")
async def list_quiz_history(http_request: Request, user_id: str = "default") -> list[QuizSummary]:
    """List all quiz sessions for a user, newest first."""
    from src.api.middleware import resolve_user_id
    resolved = resolve_user_id(http_request, user_id)
    sessions = await QuizSession.find(
        QuizSession.user_id == resolved
    ).sort(-QuizSession.created_at).to_list()

    return [
        QuizSummary(
            id=str(s.id),
            topic=s.topic,
            difficulty=s.difficulty,
            score=s.score,
            total_questions=s.total_questions,
            completed=s.completed,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str) -> dict:
    """Get a single quiz session with its results."""
    session = await QuizSession.get(quiz_id)
    if not session:
        raise HTTPException(404, "Quiz session not found")

    return {
        "id": str(session.id),
        "topic": session.topic,
        "difficulty": session.difficulty,
        "question_count": session.question_count,
        "score": session.score,
        "total_questions": session.total_questions,
        "completed": session.completed,
        "created_at": session.created_at.isoformat(),
        "questions": [
            {
                "question": q.question,
                "options": [{"label": o.label, "text": o.text} for o in q.options],
                "correct_answer": q.correct_answer if session.completed else None,
                "explanation": q.explanation if session.completed else None,
            }
            for q in session.questions
        ],
        "answers": [
            {
                "question_index": a.question_index,
                "selected_answer": a.selected_answer,
                "is_correct": a.is_correct,
            }
            for a in session.answers
        ],
    }


@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str) -> dict:
    """Delete a quiz session."""
    session = await QuizSession.get(quiz_id)
    if not session:
        raise HTTPException(404, "Quiz session not found")
    await session.delete()
    return {"success": True}
