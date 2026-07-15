import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.adk.runner import process_message, process_message_stream
from src.orchestrator.base import get_orchestrator
from src.orchestrator.router import AgentRouter
from src.agents.custom import CustomAgent
from src.models.agent import AgentConfig
from src.models.conversation import Conversation, Message
from src.utils.logger import logger
from beanie import PydanticObjectId
from src.models.workspace import Workspace

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _friendly_chat_error(error: Exception) -> str:
    """Return a useful client-facing message for common provider failures."""
    message = str(error)
    if "429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
        return (
            "The AI provider quota is exhausted for the configured Gemini API key. "
            "Enable billing or use a Gemini key/model with available quota, then restart the backend."
        )
    if "API key" in message or "api_key" in message.lower():
        return "The Gemini API key is missing or invalid. Set GEMINI_API_KEY in backend/.env and restart the backend."
    return message or "The AI agent could not generate a response."


class AttachmentInfo(BaseModel):
    name: str
    size: int
    documentId: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: str = "default"
    attachments: list[AttachmentInfo] = []
    team_agents: list[str] = []
    workspace_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    output: str
    citations: list[dict] = []
    agent_traces: list[dict] = []
    events_count: int = 0
    success: bool = True
    error: Optional[str] = None


async def can_access_conversation(conv: Conversation, user_id: str) -> bool:
    if conv.user_id == user_id:
        return True
    if not conv.workspace_id:
        return False
    workspace = await Workspace.get(conv.workspace_id)
    return bool(workspace and (workspace.user_id == user_id or user_id in workspace.member_ids))


async def _save_messages(
    conv_id: str,
    user_id: str,
    user_message: str,
    agent_message: str,
    agent_id: Optional[str] = None,
    is_new: bool = False,
    attachments: Optional[list[dict]] = None,
    workspace_id: Optional[str] = None,
):
    """Save user and assistant messages to the Conversation in MongoDB."""
    try:
        user_metadata = {}
        if attachments:
            user_metadata["attachments"] = attachments

        if is_new:
            # Create a new conversation with auto-title
            title = user_message[:80] + ("..." if len(user_message) > 80 else "")
            conv = Conversation(
                id=conv_id,
                user_id=user_id,
                title=title,
                agent_id=agent_id,
                workspace_id=workspace_id,
                messages=[
                    Message(
                        role="user",
                        content=user_message,
                        agent_id=agent_id,
                        metadata=user_metadata,
                    )
                ],
            )
            await conv.insert()
        else:
            conv = await Conversation.get(conv_id)
            if conv:
                if workspace_id and not conv.workspace_id:
                    conv.workspace_id = workspace_id
                conv.messages.append(
                    Message(
                        role="user",
                        content=user_message,
                        agent_id=agent_id,
                        metadata=user_metadata,
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
            conv.updated_at = datetime.now(timezone.utc)
            await conv.save()
    except Exception as e:
        logger.error(f"Failed to save messages: {e}")


@router.get("/conversations")
async def list_conversations(http_request: Request, user_id: str = "default") -> list[dict]:
    """List all conversations for a user."""
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id

    owned = await Conversation.find(Conversation.user_id == resolved_user_id).to_list()
    workspace_ids = [str(w.id) for w in await Workspace.find({"member_ids": resolved_user_id}).to_list()]
    shared = await Conversation.find({"workspace_id": {"$in": workspace_ids}}).to_list() if workspace_ids else []
    convs = sorted({str(c.id): c for c in owned + shared}.values(), key=lambda c: c.updated_at, reverse=True)

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
async def get_conversation(conv_id: str, http_request: Request) -> dict:
    """Get a conversation with all messages."""
    conv = await Conversation.get(conv_id)
    user_id = (getattr(http_request.state, "user", None) or {}).get("sub", "default")
    if not conv or not await can_access_conversation(conv, user_id):
        raise HTTPException(404, "Conversation not found")

    return {
        "id": str(conv.id),
        "title": conv.title,
        "agentId": conv.agent_id,
        "workspaceId": conv.workspace_id,
        "messages": [
            {
                "id": str(i),
                "role": m.role,
                "content": m.content,
                "agentId": m.agent_id,
                "metadata": m.metadata,
            }
            for i, m in enumerate(conv.messages)
        ],
        "createdAt": conv.created_at.isoformat(),
        "updatedAt": conv.updated_at.isoformat(),
    }


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, http_request: Request) -> dict:
    """Delete a conversation."""
    conv = await Conversation.get(conv_id)
    user_id = (getattr(http_request.state, "user", None) or {}).get("sub", "default")
    if not conv or conv.user_id != user_id:
        raise HTTPException(404, "Conversation not found")
    await conv.delete()
    return {"success": True, "message": "Conversation deleted"}


@router.post("")
async def chat(http_request: Request, body: ChatRequest) -> ChatResponse:
    try:
        conv_id = body.conversation_id or str(PydanticObjectId())
        is_new = not bool(body.conversation_id)

        # Use authenticated user from JWT if available, fall back to request body
        auth_user = getattr(http_request.state, "user", None)
        user_id = (auth_user.get("sub") if auth_user else None) or body.user_id
        if body.conversation_id:
            existing = await Conversation.get(body.conversation_id)
            if not existing or not await can_access_conversation(existing, user_id):
                raise HTTPException(status_code=404, detail="Conversation not found")
        if body.workspace_id:
            workspace = await Workspace.get(body.workspace_id)
            if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
                raise HTTPException(status_code=404, detail="Workspace not found")
        routed_agent_id = body.agent_id or AgentRouter().route(body.message)

        google_access_token = http_request.headers.get("X-Google-Access-Token", "")
        custom_config = await AgentConfig.find_one(AgentConfig.agent_id == body.agent_id, AgentConfig.user_id == user_id, AgentConfig.custom == True) if body.agent_id and body.agent_id.startswith("custom_") else None
        if body.team_agents:
            result = await get_orchestrator().process_team(body.message, user_id, body.team_agents, conv_id)
        elif custom_config:
            custom_agent = CustomAgent(custom_config)
            get_orchestrator().registry.register(custom_agent)
            agent_result = await custom_agent.execute(body.message, {"user_id": user_id})
            result = {"output": agent_result.output, "citations": [], "agent_traces": [{"agent_id": custom_config.agent_id, "event_type": "CustomAgent", "has_content": bool(agent_result.output)}], "events_count": 1}
        elif routed_agent_id == "calendar":
            calendar_agent = get_orchestrator().registry.get_agent("calendar")
            if not calendar_agent:
                raise HTTPException(status_code=503, detail="Calendar Agent is not initialized")
            agent_result = await calendar_agent.execute(body.message, {"user_id": user_id, "google_access_token": google_access_token})
            result = {"output": agent_result.output, "citations": [], "agent_traces": [{"agent_id": "calendar", "event_type": "CalendarAction", "has_content": bool(agent_result.output)}], "events_count": 1}
        elif body.workspace_id:
            knowledge_agent = get_orchestrator().registry.get_agent("knowledge")
            if not knowledge_agent:
                raise HTTPException(status_code=503, detail="Knowledge Agent is not initialized")
            agent_result = await knowledge_agent.execute(
                body.message, {"user_id": user_id, "conversation_id": conv_id, "workspace_id": body.workspace_id}
            )
            result = {"output": agent_result.output, "citations": agent_result.citations, "agent_traces": [{"agent_id": "knowledge", "event_type": "WorkspaceQuery", "has_content": True}], "events_count": 1}
        else:
            result = await process_message(message=body.message, user_id=user_id, conversation_id=conv_id)

        # Persist messages to MongoDB
        attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
        await _save_messages(
            conv_id=conv_id,
            user_id=user_id,
            user_message=body.message,
            agent_message=result["output"],
            agent_id=body.agent_id,
            is_new=is_new,
            attachments=attachments_data,
            workspace_id=body.workspace_id,
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
        friendly_error = _friendly_chat_error(e)
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=friendly_error)


@router.post("/stream")
async def chat_stream(
    http_request: Request,
    body: ChatRequest,
):
    """SSE streaming chat endpoint (POST).

    Streams ADK events as Server-Sent Events.
    Uses POST to support long messages and avoid URL length limits.
    The client reads the stream and accumulates the response incrementally.
    """
    conv_id = body.conversation_id or str(PydanticObjectId())
    is_new = not bool(body.conversation_id)

    # Use authenticated user from JWT if available
    auth_user = getattr(http_request.state, "user", None)
    user_id = (auth_user.get("sub") if auth_user else None) or body.user_id
    if body.conversation_id:
        existing = await Conversation.get(body.conversation_id)
        if not existing or not await can_access_conversation(existing, user_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
    if body.workspace_id:
        workspace = await Workspace.get(body.workspace_id)
        if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
            raise HTTPException(status_code=404, detail="Workspace not found")
    routed_agent_id = body.agent_id or AgentRouter().route(body.message)
    custom_config = await AgentConfig.find_one(AgentConfig.agent_id == body.agent_id, AgentConfig.user_id == user_id, AgentConfig.custom == True) if body.agent_id and body.agent_id.startswith("custom_") else None

    accumulated_output = ""

    async def event_generator():
        nonlocal accumulated_output
        try:
            if body.team_agents:
                team_result = await get_orchestrator().process_team(
                    body.message, user_id, body.team_agents, conv_id
                )
                yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"
                for stage in team_result["stages"]:
                    yield f"event: agent\ndata: {json.dumps({'agent_id': stage['agent_id']})}\n\n"
                    yield f"event: team_stage\ndata: {json.dumps({'agent_id': stage['agent_id'], 'status': 'complete'})}\n\n"
                    stage_text = f"### {stage['agent_id'].title()} Agent\n{stage['output']}\n\n"
                    yield f"event: chunk\ndata: {json.dumps({'text': stage_text})}\n\n"
                accumulated_output = team_result["output"]
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(
                    conv_id=conv_id, user_id=user_id, user_message=body.message,
                    agent_message=accumulated_output, agent_id="teamwork", is_new=is_new,
                    attachments=attachments_data,
                    workspace_id=body.workspace_id,
                )
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            if custom_config:
                custom_agent = CustomAgent(custom_config)
                get_orchestrator().registry.register(custom_agent)
                agent_result = await custom_agent.execute(body.message, {"user_id": user_id})
                yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"
                yield f"event: agent\ndata: {json.dumps({'agent_id': custom_config.agent_id})}\n\n"
                yield f"event: chunk\ndata: {json.dumps({'text': agent_result.output})}\n\n"
                accumulated_output = agent_result.output
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id=custom_config.agent_id, is_new=is_new, attachments=attachments_data, workspace_id=body.workspace_id)
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            if routed_agent_id == "calendar":
                calendar_agent = get_orchestrator().registry.get_agent("calendar")
                if not calendar_agent:
                    raise HTTPException(status_code=503, detail="Calendar Agent is not initialized")
                agent_result = await calendar_agent.execute(body.message, {"user_id": user_id, "google_access_token": http_request.headers.get("X-Google-Access-Token", "")})
                yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"
                yield f"event: agent\ndata: {json.dumps({'agent_id': 'calendar'})}\n\n"
                yield f"event: chunk\ndata: {json.dumps({'text': agent_result.output})}\n\n"
                accumulated_output = agent_result.output
                await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id="calendar", is_new=is_new, workspace_id=body.workspace_id)
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            if body.workspace_id:
                knowledge_agent = get_orchestrator().registry.get_agent("knowledge")
                if not knowledge_agent:
                    raise HTTPException(status_code=503, detail="Knowledge Agent is not initialized")
                agent_result = await knowledge_agent.execute(
                    body.message, {"user_id": user_id, "conversation_id": conv_id, "workspace_id": body.workspace_id}
                )
                yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"
                yield f"event: agent\ndata: {json.dumps({'agent_id': 'knowledge'})}\n\n"
                yield f"event: chunk\ndata: {json.dumps({'text': agent_result.output})}\n\n"
                accumulated_output = agent_result.output
                await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id="knowledge", is_new=is_new, workspace_id=body.workspace_id)
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            async for sse_event in process_message_stream(
                message=body.message, user_id=user_id, conversation_id=conv_id,
            ):
                if await http_request.is_disconnected():
                    break

                event_type = sse_event["event"]
                data = sse_event["data"]

                # Track accumulated output for persistence
                if event_type == "chunk" and "text" in data:
                    accumulated_output += data["text"]

                # On complete, persist to MongoDB
                if event_type == "complete":
                    attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                    await _save_messages(
                        conv_id=conv_id,
                        user_id=user_id,
                        user_message=body.message,
                        agent_message=data.get("output", accumulated_output),
                        agent_id=body.agent_id,
                        is_new=is_new,
                        attachments=attachments_data,
                        workspace_id=body.workspace_id,
                    )

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        except Exception as e:
            friendly_error = _friendly_chat_error(e)
            logger.error(f"Stream error: {e}", exc_info=True)
            # Still try to save what we have
            if accumulated_output:
                await _save_messages(
                    conv_id=conv_id,
                    user_id=user_id,
                    user_message=body.message,
                    agent_message=accumulated_output,
                    agent_id=body.agent_id,
                    is_new=is_new,
                )
            yield f"event: error\ndata: {json.dumps({'error': friendly_error})}\n\n"
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
