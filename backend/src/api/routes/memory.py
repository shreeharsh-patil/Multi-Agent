from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from beanie import PydanticObjectId

from src.api.middleware import resolve_user_id
from src.models.user import User
from src.services.memory.service import PROFILE_CATEGORIES, memory_service


router = APIRouter(prefix="/api/memory", tags=["Memory"])


class CreateMemoryRequest(BaseModel):
    content: str = Field(min_length=2, max_length=500)
    key: Optional[str] = None
    type: str = "semantic"
    category: str = "general"
    confidence: float = Field(default=1.0, ge=0, le=1)
    pinned: bool = False


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = Field(default=None, min_length=2, max_length=500)
    category: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    pinned: Optional[bool] = None
    status: Optional[str] = None


class MemorySettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    autoExtract: Optional[bool] = None


def serialize(item) -> dict:
    return {
        "id": str(item.id),
        "key": item.key,
        "content": item.content,
        "type": item.type,
        "category": item.category,
        "confidence": item.confidence,
        "status": item.status,
        "sourceConversationId": item.source_conversation_id,
        "evidence": item.evidence,
        "pinned": item.pinned,
        "accessCount": item.access_count,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }


@router.get("")
async def memory_dashboard(
    request: Request, category: Optional[str] = None, query: Optional[str] = None
) -> dict:
    user_id = resolve_user_id(request)
    if not PydanticObjectId.is_valid(user_id):
        raise HTTPException(404, "User not found")
    user = await User.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    items = await memory_service.list_items(user_id, category=category, query=query)
    return {
        "items": [serialize(item) for item in items],
        "profile": await memory_service.profile(user_id),
        "settings": {
            "enabled": getattr(user.preferences, "memory_enabled", True),
            "autoExtract": getattr(user.preferences, "memory_auto_extract", True),
        },
        "categories": list(PROFILE_CATEGORIES),
    }


@router.post("")
async def create_memory(body: CreateMemoryRequest, request: Request) -> dict:
    user_id = resolve_user_id(request)
    item = await memory_service.store(
        user_id=user_id,
        key=body.key or body.content[:60],
        content=body.content,
        type=body.type,
        category=body.category,
        confidence=body.confidence,
        pinned=body.pinned,
        evidence="Added manually",
    )
    return serialize(item)


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, body: UpdateMemoryRequest, request: Request) -> dict:
    if body.category is not None and body.category not in PROFILE_CATEGORIES:
        raise HTTPException(400, "Invalid memory category")
    if body.status is not None and body.status not in {"active", "archived", "superseded"}:
        raise HTTPException(400, "Invalid memory status")
    item = await memory_service.update(
        resolve_user_id(request), memory_id, **body.model_dump(exclude_unset=True)
    )
    if not item:
        raise HTTPException(404, "Memory not found")
    return serialize(item)


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, request: Request) -> dict:
    if not await memory_service.delete(resolve_user_id(request), memory_id):
        raise HTTPException(404, "Memory not found")
    return {"deleted": True}


@router.delete("")
async def clear_memories(request: Request) -> dict:
    return {"deleted": await memory_service.clear(resolve_user_id(request))}


@router.post("/consolidate")
async def consolidate_memories(request: Request) -> dict:
    user_id = resolve_user_id(request)
    if not PydanticObjectId.is_valid(user_id):
        raise HTTPException(404, "User not found")
    result = await memory_service.consolidate(user_id)
    return result


@router.put("/settings/preferences")
async def update_memory_settings(body: MemorySettingsRequest, request: Request) -> dict:
    user_id = resolve_user_id(request)
    if not PydanticObjectId.is_valid(user_id):
        raise HTTPException(404, "User not found")
    user = await User.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if body.enabled is not None:
        user.preferences.memory_enabled = body.enabled
    if body.autoExtract is not None:
        user.preferences.memory_auto_extract = body.autoExtract
    await user.save()
    return {
        "enabled": getattr(user.preferences, "memory_enabled", True),
        "autoExtract": getattr(user.preferences, "memory_auto_extract", True),
    }
