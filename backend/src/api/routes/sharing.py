import secrets
from fastapi import APIRouter, HTTPException, Request
from src.models.conversation import Conversation
from src.models.workspace import Workspace
from src.models.workspace import ChatShare

router = APIRouter(prefix="/api/shares", tags=["Sharing"])


def user_id(request: Request) -> str:
    return (getattr(request.state, "user", None) or {}).get("sub", "default")


@router.post("/chat/{conversation_id}")
async def create_chat_share(conversation_id: str, request: Request) -> dict:
    conv = await Conversation.get(conversation_id)
    if not conv or conv.user_id != user_id(request):
        raise HTTPException(404, "Conversation not found")
    existing = await ChatShare.find_one(ChatShare.conversation_id == conversation_id, ChatShare.owner_id == user_id(request))
    share = existing or ChatShare(token=secrets.token_urlsafe(32), conversation_id=conversation_id, owner_id=user_id(request))
    if not existing:
        await share.insert()
    return {"token": share.token, "conversationId": conversation_id}


@router.delete("/chat/{conversation_id}")
async def revoke_chat_share(conversation_id: str, request: Request) -> dict:
    share = await ChatShare.find_one(ChatShare.conversation_id == conversation_id, ChatShare.owner_id == user_id(request))
    if share:
        await share.delete()
    return {"success": True}


@router.get("/chat/{token}")
async def read_shared_chat(token: str) -> dict:
    share = await ChatShare.find_one(ChatShare.token == token)
    if not share:
        raise HTTPException(404, "Share link not found or revoked")
    conv = await Conversation.get(share.conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return {
        "id": str(conv.id), "title": conv.title, "ownerId": share.owner_id,
        "messages": [{"role": m.role, "content": m.content, "agentId": m.agent_id} for m in conv.messages],
        "createdAt": conv.created_at.isoformat(), "updatedAt": conv.updated_at.isoformat(),
    }


@router.post("/workspace/{workspace_id}/join")
async def join_shared_workspace(workspace_id: str, request: Request) -> dict:
    workspace = await Workspace.get(workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    uid = user_id(request)
    if uid != workspace.user_id and uid not in workspace.member_ids:
        workspace.member_ids.append(uid)
        await workspace.save()
    return {"id": str(workspace.id), "name": workspace.name, "member": True}
