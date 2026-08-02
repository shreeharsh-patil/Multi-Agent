"""AI Study Agent API Routes.

Exposes end-to-end endpoints for:
- Study Note Generation (Beginner, Exam, Detailed, Revision, Cheat Sheet)
- Question & Active Learning Generation (Bloom's Taxonomy, MCQs, Numericals, Case Studies)
- Formula Explanation & KaTeX Proof Breakdown
- Knowledge Graph & Concept Map Extraction
- Citation & Cross-Reference Explorer
- Learning Mode Info & Configuration
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from src.services.study_agent import study_agent_service, LEARNING_MODE_PROMPTS, NOTE_STYLE_INSTRUCTIONS
from src.models.note import Note
from src.utils.logger import logger

router = APIRouter(prefix="/api/study", tags=["Study Agent"])


class GenerateNotesRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    style: str = "detailed"  # beginner | exam | detailed | revision | cheatsheet
    workspace_id: Optional[str] = None
    save_as_note: bool = True
    custom_instructions: Optional[str] = None


class GenerateQuizRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    count: int = Field(default=5, ge=1, le=20)
    blooms_level: str = "all"  # remember | understand | apply | analyze | evaluate | create | all
    question_types: List[str] = ["mcq", "short_answer", "long_answer", "numerical"]
    workspace_id: Optional[str] = None


class ExplainFormulaRequest(BaseModel):
    formula: str = Field(min_length=1, max_length=2000)
    workspace_id: Optional[str] = None


class ConceptGraphRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=1000)
    workspace_id: Optional[str] = None


@router.get("/learning-modes")
async def get_learning_modes() -> dict:
    """Return available learning modes and their descriptions."""
    return {
        "modes": [
            {"id": "teach_me", "name": "Teach Me", "description": "Interactive step-by-step Socratic tutor with analogies & visual diagrams."},
            {"id": "eli10", "name": "Explain Like I'm 10", "description": "Simple language, zero jargon, fun everyday analogies."},
            {"id": "professor", "name": "Professor Mode", "description": "Rigorous academic proofs, KaTeX formulas, and research literature context."},
            {"id": "research", "name": "Research Mode", "description": "Deep paper analysis, trade-off evaluation, open problems, and citation extraction."},
            {"id": "exam", "name": "Exam Mode", "description": "High-scoring university/GATE format, key definitions, formulas, and scoring points."},
            {"id": "revision", "name": "Revision Mode", "description": "1-page rapid summary, dense bullet points, and memory mnemonics."},
            {"id": "interview", "name": "Interview Mode", "description": "Core concepts, time/space complexity analysis, edge cases, and code dry-runs."},
        ]
    }


@router.get("/note-styles")
async def get_note_styles() -> dict:
    """Return available note generation styles."""
    return {
        "styles": [
            {"id": "beginner", "name": "Beginner Notes", "description": "Simple, no assumed knowledge, basic definitions & analogies."},
            {"id": "exam", "name": "Exam Notes", "description": "High scoring, 2/5/10 mark patterns, formulas, and key points."},
            {"id": "detailed", "name": "Detailed Notes", "description": "Exhaustive deep-dive explanations, KaTeX proofs, and Mermaid diagrams."},
            {"id": "revision", "name": "Revision Notes", "description": "1-page ultra-concise recap with core takeaways."},
            {"id": "cheatsheet", "name": "Cheat Sheet", "description": "Formula tables, code blocks, shortcuts, and keywords."},
        ]
    }


@router.post("/notes")
async def generate_study_notes(http_request: Request, body: GenerateNotesRequest) -> dict:
    """Generate study notes in any of 5 styles and optionally save as a Note."""
    auth_user = getattr(http_request.state, "user", None) or {}
    user_id = auth_user.get("sub", "default")

    try:
        result = await study_agent_service.generate_study_notes(
            topic=body.topic,
            user_id=user_id,
            style=body.style,
            workspace_id=body.workspace_id,
            custom_instructions=body.custom_instructions,
        )

        saved_note_id = None
        if body.save_as_note:
            note = Note(
                title=result["title"],
                content=result["content"],
                tags=[body.style, "ai-study-notes", body.topic.lower()[:20]],
                workspace_id=body.workspace_id,
                user_id=user_id,
            )
            await note.insert()
            saved_note_id = str(note.id)

        return {
            "title": result["title"],
            "content": result["content"],
            "style": result["style"],
            "citations": result["citations"],
            "noteId": saved_note_id,
        }
    except Exception as e:
        logger.error(f"Failed to generate study notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate study notes: {e}")


@router.post("/quiz")
async def generate_study_quiz(http_request: Request, body: GenerateQuizRequest) -> dict:
    """Generate Bloom's Taxonomy aligned questions with step-by-step solutions and memory tricks."""
    auth_user = getattr(http_request.state, "user", None) or {}
    user_id = auth_user.get("sub", "default")

    try:
        questions = await study_agent_service.generate_questions(
            topic=body.topic,
            user_id=user_id,
            count=body.count,
            blooms_level=body.blooms_level,
            question_types=body.question_types,
            workspace_id=body.workspace_id,
        )
        return {
            "topic": body.topic,
            "count": len(questions),
            "questions": questions,
        }
    except Exception as e:
        logger.error(f"Failed to generate study quiz: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {e}")


@router.post("/formula")
async def explain_formula(http_request: Request, body: ExplainFormulaRequest) -> dict:
    """Exhaustive formula breakdown with KaTeX math derivation and solved numerical examples."""
    auth_user = getattr(http_request.state, "user", None) or {}
    user_id = auth_user.get("sub", "default")

    try:
        result = await study_agent_service.explain_formula(
            formula=body.formula,
            user_id=user_id,
            workspace_id=body.workspace_id,
        )
        return result
    except Exception as e:
        logger.error(f"Formula explanation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to explain formula: {e}")


@router.post("/concept-graph")
async def get_concept_graph(http_request: Request, body: ConceptGraphRequest) -> dict:
    """Extract Knowledge Graph concept hierarchy and Mermaid flowchart for a topic/document."""
    auth_user = getattr(http_request.state, "user", None) or {}
    user_id = auth_user.get("sub", "default")

    try:
        result = await study_agent_service.generate_concept_graph(
            topic=body.topic,
            user_id=user_id,
            workspace_id=body.workspace_id,
        )
        return result
    except Exception as e:
        logger.error(f"Concept graph generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate concept graph: {e}")


@router.get("/references")
async def get_workspace_references(
    http_request: Request, workspace_id: Optional[str] = Query(None)
) -> dict:
    """Extract and link citations, section references, DOIs, and IEEE references in workspace documents."""
    auth_user = getattr(http_request.state, "user", None) or {}
    user_id = auth_user.get("sub", "default")

    try:
        references = await study_agent_service.resolve_references(user_id=user_id, workspace_id=workspace_id)
        return {
            "references": references,
            "count": len(references),
        }
    except Exception as e:
        logger.error(f"Reference extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract references: {e}")
