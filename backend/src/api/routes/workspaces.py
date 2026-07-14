from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.models.workspace import Workspace
from src.models.document import Document

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


def current_user(request: Request) -> str:
    auth_user = getattr(request.state, "user", None)
    return (auth_user.get("sub") if auth_user else None) or "default"


async def get_accessible_workspace(workspace_id: str, user_id: str) -> Workspace:
    workspace = await Workspace.get(workspace_id)
    if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None
    color: str = "#7c3aed"


def serialize(workspace: Workspace, document_count: int = 0) -> dict:
    return {
        "id": str(workspace.id), "name": workspace.name,
        "description": workspace.description, "color": workspace.color,
        "documentCount": document_count,
        "memberCount": len(workspace.member_ids) + 1,
        "isOwner": False,
        "createdAt": workspace.created_at.isoformat(),
        "updatedAt": workspace.updated_at.isoformat(),
    }


@router.get("")
async def list_workspaces(request: Request) -> list[dict]:
    user_id = current_user(request)
    workspaces = await Workspace.find({"$or": [{"user_id": user_id}, {"member_ids": user_id}]}).sort(-Workspace.updated_at).to_list()
    return [{**serialize(w, await Document.find(Document.workspace_id == str(w.id)).count()), "isOwner": w.user_id == user_id} for w in workspaces]


@router.post("")
async def create_workspace(request: Request, body: WorkspaceCreate) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Workspace name is required")
    workspace = Workspace(user_id=current_user(request), name=name, description=body.description, color=body.color)
    await workspace.insert()
    return serialize(workspace)


@router.patch("/{workspace_id}")
async def update_workspace(workspace_id: str, request: Request, body: WorkspaceCreate) -> dict:
    workspace = await Workspace.get(workspace_id)
    if not workspace or workspace.user_id != current_user(request):
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace.name = body.name.strip() or workspace.name
    workspace.description = body.description
    workspace.color = body.color
    workspace.updated_at = datetime.now(timezone.utc)
    await workspace.save()
    return serialize(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, request: Request) -> dict:
    workspace = await Workspace.get(workspace_id)
    if not workspace or workspace.user_id != current_user(request):
        raise HTTPException(status_code=404, detail="Workspace not found")
    await Document.find(Document.workspace_id == workspace_id, Document.user_id == current_user(request)).update_many({"$set": {"workspace_id": None}})
    await workspace.delete()
    return {"success": True}


@router.post("/{workspace_id}/join")
async def join_workspace(workspace_id: str, request: Request) -> dict:
    workspace = await Workspace.get(workspace_id)
    user_id = current_user(request)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if user_id != workspace.user_id and user_id not in workspace.member_ids:
        workspace.member_ids.append(user_id)
        workspace.updated_at = datetime.now(timezone.utc)
        await workspace.save()
    return serialize(workspace)


@router.get("/{workspace_id}/members")
async def list_members(workspace_id: str, request: Request) -> dict:
    workspace = await get_accessible_workspace(workspace_id, current_user(request))
    return {"ownerId": workspace.user_id, "memberIds": workspace.member_ids}
