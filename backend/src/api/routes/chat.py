from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.adk.runner import process_message
from src.utils.logger import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: str = "default"


class ChatResponse(BaseModel):
    conversation_id: str
    output: str
    citations: list[dict] = []
    agent_traces: list[dict] = []
    events_count: int = 0
    success: bool = True
    error: Optional[str] = None


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        conv_id = request.conversation_id or "default"
        result = await process_message(
            message=request.message,
            user_id=request.user_id,
            conversation_id=conv_id,
        )

        return ChatResponse(
            conversation_id=conv_id,
            output=result["output"],
            citations=result.get("citations", []),
            agent_traces=result.get("agent_traces", []),
            events_count=result.get("events_count", 0),
            success=True,
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
