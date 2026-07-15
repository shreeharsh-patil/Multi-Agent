from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
import io
from src.models.note import Note
from src.api.middleware import resolve_user_id
from src.services.notes.exporter import notes_exporter
from src.utils.logger import logger

router = APIRouter(prefix="/api/notes", tags=["Notes"])


class CreateNoteRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []
    source_document_id: Optional[str] = None
    user_id: str = "default"


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


@router.get("")
async def list_notes(http_request: Request, user_id: str = "default") -> list[dict]:
    """List all notes for a user."""
    user_id = resolve_user_id(http_request, user_id)
    notes = await Note.find(Note.user_id == user_id).sort(-Note.updated_at).to_list()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
            "preview": n.content[:200] if len(n.content) > 200 else n.content,
            "tags": n.tags,
            "sourceDocumentId": n.source_document_id,
            "createdAt": n.created_at.isoformat(),
            "updatedAt": n.updated_at.isoformat(),
        }
        for n in notes
    ]


@router.post("")
async def create_note(request: CreateNoteRequest, http_request: Request) -> dict:
    """Create a new note."""
    note = Note(
        user_id=resolve_user_id(http_request, request.user_id),
        title=request.title,
        content=request.content,
        tags=request.tags,
        source_document_id=request.source_document_id,
    )
    await note.insert()
    logger.info(f"Created note: {note.title}")
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "createdAt": note.created_at.isoformat(),
    }


@router.get("/{note_id}")
async def get_note(note_id: str, http_request: Request) -> dict:
    """Get a single note by ID."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or note.user_id != user_id:
        raise HTTPException(404, "Note not found")
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "sourceDocumentId": note.source_document_id,
        "createdAt": note.created_at.isoformat(),
        "updatedAt": note.updated_at.isoformat(),
    }


@router.put("/{note_id}")
async def update_note(note_id: str, request: UpdateNoteRequest, http_request: Request) -> dict:
    """Update an existing note."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or note.user_id != user_id:
        raise HTTPException(404, "Note not found")

    if request.title is not None:
        note.title = request.title
    if request.content is not None:
        note.content = request.content
    if request.tags is not None:
        note.tags = request.tags

    await note.save()
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "updatedAt": note.updated_at.isoformat(),
    }


@router.delete("/{note_id}")
async def delete_note(note_id: str, http_request: Request) -> dict:
    """Delete a note."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or note.user_id != user_id:
        raise HTTPException(404, "Note not found")
    await note.delete()
    return {"success": True, "message": "Note deleted"}


@router.get("/{note_id}/export")
async def export_note(
    note_id: str,
    format: Literal["pdf", "docx", "markdown"] = Query("markdown", alias="format"),
) -> Response:
    """Export a note as PDF, DOCX, or Markdown.

    Accessed via a direct browser link (no Authorization header), so it is not
    user-scoped; the note id itself is the capability.
    """
    note = await Note.get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")

    content_type_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "markdown": "text/markdown",
    }

    extension_map = {
        "pdf": "pdf",
        "docx": "docx",
        "markdown": "md",
    }

    try:
        if format == "pdf":
            file_bytes = await notes_exporter.export_pdf(note.title, note.content)
        elif format == "docx":
            file_bytes = await notes_exporter.export_docx(note.title, note.content)
        else:
            file_bytes = await notes_exporter.export_markdown(note.title, note.content)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in note.title)
        filename = f"{safe_title}.{extension_map[format]}"

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=content_type_map[format],
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_bytes)),
            },
        )
    except ImportError as e:
        raise HTTPException(500, detail=str(e))
    except Exception as e:
        logger.error(f"Note export failed: {e}")
        raise HTTPException(500, detail=f"Export failed: {str(e)}")
