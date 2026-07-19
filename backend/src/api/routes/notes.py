from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
import io
import json
import base64
from src.models.note import Note
from src.api.middleware import resolve_user_id
from src.services.notes.exporter import notes_exporter
from src.services.auth.service import verify_access_token
from src.utils.logger import logger

router = APIRouter(prefix="/api/notes", tags=["Notes"])


class CreateNoteRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []
    source_document_id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: str = "default"


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    workspace_id: Optional[str] = None


async def check_note_access(note: Note, user_id: str) -> bool:
    if note.user_id == user_id:
        return True
    if note.workspace_id:
        from src.models.workspace import Workspace
        workspace = await Workspace.get(note.workspace_id)
        if workspace and (workspace.user_id == user_id or user_id in workspace.member_ids):
            return True
    return False


class ConnectionManager:
    def __init__(self):
        # Maps room_id -> list of WebSockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict, sender: WebSocket):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass


manager = ConnectionManager()


@router.websocket("/{note_id}/ws")
async def note_websocket_endpoint(websocket: WebSocket, note_id: str):
    token = websocket.query_params.get("token")
    user_id = "default"
    if token:
        try:
            payload = verify_access_token(token)
            if payload and payload.get("sub"):
                user_id = payload["sub"]
        except Exception:
            pass

    note = await Note.get(note_id)
    if not note or not await check_note_access(note, user_id):
        await websocket.close(code=1008)  # Policy Violation
        return

    await manager.connect(note_id, websocket)

    try:
        # 1. Send all stored updates to the newly connected client
        if note.yjs_updates:
            for update in note.yjs_updates:
                encoded_update = base64.b64encode(update).decode('utf-8')
                await websocket.send_json({
                    "type": "sync",
                    "data": encoded_update
                })

        # 2. Start loop for receiving and broadcasting messages
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data")

            if msg_type == "sync" and msg_data:
                try:
                    update_bytes = base64.b64decode(msg_data)
                    # Persist the update
                    if not note.yjs_updates:
                        note.yjs_updates = []
                    note.yjs_updates.append(update_bytes)
                    await note.save()

                    # Broadcast to other users in the room
                    await manager.broadcast(note_id, data, websocket)
                except Exception as e:
                    logger.error(f"Error handling sync update: {e}")
            elif msg_type == "awareness":
                # Awareness updates are not persisted, just broadcasted
                await manager.broadcast(note_id, data, websocket)

    except WebSocketDisconnect:
        manager.disconnect(note_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error in note room {note_id}: {e}")
        manager.disconnect(note_id, websocket)


@router.get("")
async def list_notes(
    http_request: Request,
    workspace_id: Optional[str] = Query(None),
    user_id: str = "default"
) -> list[dict]:
    """List all notes for a user or workspace."""
    user_id = resolve_user_id(http_request, user_id)
    if workspace_id:
        from src.models.workspace import Workspace
        workspace = await Workspace.get(workspace_id)
        if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
            raise HTTPException(status_code=403, detail="Access denied to this workspace")
        notes = await Note.find(Note.workspace_id == workspace_id).sort(-Note.updated_at).to_list()
    else:
        notes = await Note.find(Note.user_id == user_id, Note.workspace_id == None).sort(-Note.updated_at).to_list()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
            "preview": n.content[:200] if len(n.content) > 200 else n.content,
            "tags": n.tags,
            "sourceDocumentId": n.source_document_id,
            "workspaceId": n.workspace_id,
            "createdAt": n.created_at.isoformat(),
            "updatedAt": n.updated_at.isoformat(),
        }
        for n in notes
    ]


@router.post("")
async def create_note(request: CreateNoteRequest, http_request: Request) -> dict:
    """Create a new note."""
    user_id = resolve_user_id(http_request, request.user_id)
    if request.workspace_id:
        from src.models.workspace import Workspace
        workspace = await Workspace.get(request.workspace_id)
        if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
            raise HTTPException(status_code=403, detail="Cannot create note in this workspace")
    note = Note(
        user_id=user_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        source_document_id=request.source_document_id,
        workspace_id=request.workspace_id,
    )
    await note.insert()
    logger.info(f"Created note: {note.title}")
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "workspaceId": note.workspace_id,
        "createdAt": note.created_at.isoformat(),
    }


@router.get("/{note_id}")
async def get_note(note_id: str, http_request: Request) -> dict:
    """Get a single note by ID."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or not await check_note_access(note, user_id):
        raise HTTPException(404, "Note not found")
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "sourceDocumentId": note.source_document_id,
        "workspaceId": note.workspace_id,
        "createdAt": note.created_at.isoformat(),
        "updatedAt": note.updated_at.isoformat(),
    }


@router.put("/{note_id}")
async def update_note(note_id: str, request: UpdateNoteRequest, http_request: Request) -> dict:
    """Update an existing note."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or not await check_note_access(note, user_id):
        raise HTTPException(404, "Note not found")

    if request.title is not None:
        note.title = request.title
    if request.content is not None:
        note.content = request.content
    if request.tags is not None:
        note.tags = request.tags
    if request.workspace_id is not None:
        if request.workspace_id:
            from src.models.workspace import Workspace
            workspace = await Workspace.get(request.workspace_id)
            if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
                raise HTTPException(status_code=403, detail="Cannot assign note to this workspace")
        note.workspace_id = request.workspace_id

    await note.save()
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "workspaceId": note.workspace_id,
        "updatedAt": note.updated_at.isoformat(),
    }


@router.delete("/{note_id}")
async def delete_note(note_id: str, http_request: Request) -> dict:
    """Delete a note."""
    user_id = resolve_user_id(http_request)
    note = await Note.get(note_id)
    if not note or not await check_note_access(note, user_id):
        raise HTTPException(404, "Note not found")
    await note.delete()
    return {"success": True, "message": "Note deleted"}



@router.get("/{note_id}/export")
async def export_note(
    note_id: str,
    http_request: Request,
    format: Literal["pdf", "docx", "markdown"] = Query("markdown", alias="format"),
) -> Response:
    """Export an accessible note as PDF, DOCX, or Markdown."""
    note = await Note.get(note_id)
    user_id = resolve_user_id(http_request)
    if not note or not await check_note_access(note, user_id):
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
