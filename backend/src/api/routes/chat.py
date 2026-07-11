import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.adk.runner import process_message, process_message_stream
from src.models.conversation import Conversation, Message
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


async def _save_messages(
    conv_id: str,
    user_id: str,
    user_message: str,
    agent_message: str,
    agent_id: Optional[str] = None,
    is_new: bool = False,
):
    """Save user and assistant messages to the Conversation in MongoDB."""
    try:
        if is_new:
            # Create a new conversation with auto-title
            title = user_message[:80] + ("..." if len(user_message) > 80 else "")
            conv = Conversation(
                id=conv_id,
                user_id=user_id,
                title=title,
                agent_id=agent_id,
                messages=[
                    Message(
                        role="user",
                        content=user_message,
                        agent_id=agent_id,
                    )
                ],
            )
            await conv.insert()
        else:
            conv = await Conversation.get(conv_id)
            if conv:
                conv.messages.append(
                    Message(
                        role="user",
                        content=user_message,
                        agent_id=agent_id,
                    )
                )

        # Add assistant response
        if conv:
            conv.messages.append(
                Message(
                    role="assistant",
                    content=agent_message,
                    agent_id=agent_id,
                )
            )
            conv.updated_at = datetime.utcnow()
            await conv.save()
    except Exception as e:
        logger.error(f"Failed to save messages: {e}")


@router.get("/conversations")
async def list_conversations(user_id: str = "default") -> list[dict]:
    """List all conversations for a user."""
    convs = await Conversation.find(
        Conversation.user_id == user_id
    ).sort(-Conversation.updated_at).to_list()

    return [
        {
            "id": str(c.id),
            "title": c.title,
            "agentId": c.agent_id,
            "messageCount": len(c.messages),
            "lastMessage": c.messages[-1].content[:100] if c.messages else "",
            "createdAt": c.created_at.isoformat(),
            "updatedAt": c.updated_at.isoformat(),
        }
        for c in convs
    ]


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str) -> dict:
    """Get a conversation with all messages."""
    conv = await Conversation.get(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    return {
        "id": str(conv.id),
        "title": conv.title,
        "agentId": conv.agent_id,
        "messages": [
            {
                "id": str(i),
                "role": m.role,
                "content": m.content,
                "agentId": m.agent_id,
            }
            for i, m in enumerate(conv.messages)
        ],
        "createdAt": conv.created_at.isoformat(),
        "updatedAt": conv.updated_at.isoformat(),
    }


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str) -> dict:
    """Delete a conversation."""
    conv = await Conversation.get(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    await conv.delete()
    return {"success": True, "message": "Conversation deleted"}


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        conv_id = request.conversation_id or str(uuid.uuid4())
        is_new = not bool(request.conversation_id)

        result = await process_message(
            message=request.message,
            user_id=request.user_id,
            conversation_id=conv_id,
        )

        # Persist messages to MongoDB
        await _save_messages(
            conv_id=conv_id,
            user_id=request.user_id,
            user_message=request.message,
            agent_message=result["output"],
            agent_id=request.agent_id,
            is_new=is_new,
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
    conv_id = body.conversation_id or str(uuid.uuid4())
    is_new = not bool(body.conversation_id)
    accumulated_output = ""

    async def event_generator():
        nonlocal accumulated_output
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

                # Track accumulated output for persistence
                if event_type == "chunk" and "text" in data:
                    accumulated_output += data["text"]

                # On complete, persist to MongoDB
                if event_type == "complete":
                    await _save_messages(
                        conv_id=conv_id,
                        user_id=body.user_id,
                        user_message=body.message,
                        agent_message=data.get("output", accumulated_output),
                        agent_id=body.agent_id,
                        is_new=is_new,
                    )

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            # Still try to save what we have
            if accumulated_output:
                await _save_messages(
                    conv_id=conv_id,
                    user_id=body.user_id,
                    user_message=body.message,
                    agent_message=accumulated_output,
                    agent_id=body.agent_id,
                    is_new=is_new,
                )
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
