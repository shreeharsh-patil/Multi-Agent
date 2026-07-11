import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.adk.runner import process_message, process_message_stream
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


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
):
    """SSE streaming chat endpoint (POST).

    Streams ADK events as Server-Sent Events.
    Uses POST to support long messages and avoid URL length limits.
    The client reads the stream and accumulates the response incrementally.
    """
    conv_id = body.conversation_id or "default"

    async def event_generator():
        try:
            async for sse_event in process_message_stream(
                message=body.message,
                user_id=body.user_id,
                conversation_id=conv_id,
            ):
                if await request.is_disconnected():
                    break

                event_type = sse_event["event"]
                data = sse_event["data"]

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'output': '', 'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
