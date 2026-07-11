from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.orchestrator.base import get_orchestrator
from src.utils.logger import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: str = "default"


class ChatResponse(BaseModel):
    conversation_id: str
    agent_id: str
    output: str
    citations: list[dict] = []
    tool_calls: list[dict] = []
    latency_ms: float
    success: bool
    error: Optional[str] = None


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.process(
            user_input=request.message,
            user_id=request.user_id,
            agent_id=request.agent_id,
            conversation_id=request.conversation_id,
        )

        return ChatResponse(
            conversation_id=request.conversation_id or "new",
            agent_id=result["agent_id"],
            output=result["output"],
            citations=result.get("citations", []),
            tool_calls=result.get("tool_calls", []),
            latency_ms=result["latency_ms"],
            success=result["success"],
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
