import asyncio
import contextlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from src.config import settings
from src.adk.runner import process_message, process_message_stream, process_fast_message_stream
from src.orchestrator.boss import get_boss_agent
from src.orchestrator.router import AgentRouter
from src.orchestrator.dynamic import plan_dynamic
from src.agents.custom import CustomAgent
from src.models.agent import AgentConfig
from src.models.conversation import Conversation, Message, Citation
from src.utils.logger import logger
from beanie import PydanticObjectId
from src.models.workspace import Workspace
from src.models.document import Document, DocumentChunk
from src.services.image_generation import generate_and_store_image

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Image extensions used to detect whether an attached file is viewable inline
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
MAX_ATTACHMENT_CONTEXT_CHARS = 30000
MAX_ATTACHMENT_CHARS = 15000
# These agents are implemented in the ADK graph even when an optional legacy
# registry import fails.  They must remain selectable from the chat UI.
ADK_BUILTIN_AGENT_IDS = {"knowledge"}


def _adk_routing_preamble(agent_id: str | None, team_agents: list[str]) -> str:
    """Pass UI choices to BossAgent as hints, never as a forced workflow."""
    if team_agents:
        return (
            "SYSTEM ROUTING HINT: The user suggested these specialists: "
            f"{', '.join(team_agents)}. BossAgent must independently select the "
            "smallest suitable workflow and may use different specialists. Verify "
            "current or external claims with native Google Search grounding.\n\n"
        )
    if agent_id and agent_id not in {"auto", "image"}:
        return (
            f"SYSTEM ROUTING HINT: The user selected `{agent_id}`. BossAgent decides "
            "whether that specialist is needed and selects the workflow. For unverified "
            "named entities, locations, acronyms, or current facts, use native Google "
            "Search grounding and cite sources; do not guess.\n\n"
        )
    return ""


def _chat_log(request_id: str, stage: str, status: str, started_at: float | None = None, **fields):
    """Emit bounded, correlated diagnostics for one chat request."""
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2) if started_at else None
    payload = {
        "request_id": request_id,
        "stage": stage,
        "status": status,
        "elapsed_ms": elapsed_ms,
        **fields,
    }
    level = logger.error if status == "error" else logger.info
    level("chat_pipeline", extra=payload)


async def _word_chunks(text: str):
    """Yield display-friendly chunks for agents without native streaming."""
    for word in re.findall(r"\S+\s*|\s+", text):
        yield word
        await asyncio.sleep(0)


async def _await_with_heartbeats(awaitable, http_request: Request, timeout_seconds: float):
    """Await non-streaming work while keeping SSE alive and cancellable."""
    task = asyncio.create_task(awaitable)
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    try:
        while True:
            if await http_request.is_disconnected():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                raise asyncio.CancelledError

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                raise TimeoutError("Agent execution timed out")

            done, _ = await asyncio.wait({task}, timeout=min(1.5, remaining))
            if done:
                yield True, task.result()
                return
            yield False, None
    finally:
        if not task.done():
            task.cancel()


async def _load_attachment_text(doc: Document) -> str:
    """Load content for one exact attachment without relying on RAG similarity."""
    chunks = await DocumentChunk.find({"document_id": str(doc.id)}).sort("chunk_index").to_list()
    if chunks:
        extracted = "\n\n".join(chunk.content for chunk in chunks if chunk.content.strip())
        if extracted.strip():
            return extracted.strip()

    # Fallback: parse document directly from file_path if available
    if doc.file_path and os.path.exists(doc.file_path):
        ext = (doc.file_type or "").lstrip(".").lower()
        if ext not in IMAGE_EXTENSIONS:
            from src.services.rag.parser import document_parser
            try:
                parsed = await asyncio.to_thread(document_parser.parse, doc.file_path, ext)
                if parsed and parsed.text.strip():
                    return parsed.text.strip()
            except Exception as exc:
                logger.warning(f"Direct parse failed for attachment {doc.file_name}: {exc}")

            try:
                with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read().strip()
            except Exception:
                pass
    return ""


async def _build_attachment_context(
    attachments: list | None,
    user_id: str | None = None,
    user_query: str = "",
    conv_id: str | None = None,
) -> str:
    """Build a prompt prefix containing the actual contents of attached files (current & previous turns)."""
    target_attachments: list = []
    seen_doc_ids: set = set()

    if attachments:
        for att in attachments:
            doc_id = att.get("documentId") if isinstance(att, dict) else getattr(att, "documentId", None)
            if doc_id:
                seen_doc_ids.add(doc_id)
            target_attachments.append(att)

    # Search previous turns in the conversation for uploaded attachments
    if conv_id:
        try:
            conv = await Conversation.get(conv_id)
            if conv and conv.messages:
                for m in conv.messages:
                    if m.metadata and isinstance(m.metadata, dict):
                        prev_atts = m.metadata.get("attachments")
                        if prev_atts and isinstance(prev_atts, list):
                            for pa in prev_atts:
                                d_id = pa.get("documentId") if isinstance(pa, dict) else getattr(pa, "documentId", None)
                                if d_id and d_id not in seen_doc_ids:
                                    seen_doc_ids.add(d_id)
                                    target_attachments.append(pa)
        except Exception as e:
            logger.warning(f"Could not load previous attachments for conversation {conv_id}: {e}")

    if not target_attachments:
        return ""

    sections: list[str] = []
    used_chars = 0
    for att in target_attachments:
        doc_id = att.get("documentId") if isinstance(att, dict) else getattr(att, "documentId", None)
        name = att.get("name") if isinstance(att, dict) else getattr(att, "name", "unknown")
        if not doc_id:
            sections.append(f"## {name}\nThe upload did not return a document identifier, so its contents are unavailable.")
            continue

        try:
            doc = await Document.get(doc_id)
        except Exception:
            doc = None

        if not doc:
            # OpenDocuments returns external IDs instead of local MongoDB IDs.
            try:
                from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client

                if user_id and await should_use_opendocuments(user_id):
                    result = await opendocuments_client.query_rag(
                        user_query or f"Summarize the contents of {name}",
                        top_k=8,
                    )
                    matching = [
                        item for item in result.get("results", [])
                        if (item.get("metadata", {}).get("file_name") or "").casefold() == name.casefold()
                    ]
                    items = matching or result.get("results", [])
                    content = "\n\n".join(item.get("content", "") for item in items if item.get("content"))
                    if content:
                        excerpt = content[:MAX_ATTACHMENT_CHARS]
                        sections.append(f"## {name}\n{excerpt}")
                        used_chars += len(excerpt)
                        continue
            except Exception as exc:
                logger.warning("Could not load OpenDocuments attachment %s: %s", name, exc)
            sections.append(f"## {name}\nThe uploaded document could not be loaded.")
            continue

        if doc and user_id and doc.user_id != user_id and doc.user_id != "default":
            accessible = bool(doc.workspace_id and await can_use_workspace(doc.workspace_id, user_id))
            if not accessible:
                sections.append(f"## {name}\nThe uploaded document is not available to the current user.")
                continue

        is_image = doc.file_type in IMAGE_EXTENSIONS if doc else False
        content = await _load_attachment_text(doc)
        # Upload-time OCR can return only a generic metadata sentence when the
        # vision provider is temporarily unavailable. Retry with the actual
        # image when the user asks a question about it.
        generic_image_result = bool(
            content and re.match(r"^(?:Image attachment|Uploaded image)\b", content.strip(), re.IGNORECASE)
        )
        if (not content or generic_image_result) and is_image and doc.file_type != "svg" and doc.file_path and os.path.exists(doc.file_path):
            # Retry vision at question time if upload-time analysis was unavailable.
            from src.services.rag.ocr import analyze_image

            mime_type = "image/jpeg" if doc.file_type in {"jpg", "jpeg"} else f"image/{doc.file_type}"
            try:
                image_bytes = await asyncio.to_thread(Path(doc.file_path).read_bytes)
                content = (await analyze_image(image_bytes, mime_type, doc.file_name)).strip()
                if content:
                    await DocumentChunk(
                        document_id=str(doc.id),
                        user_id=doc.user_id,
                        content=content,
                        chunk_index=0,
                        section="Image analysis",
                        metadata={"file_name": doc.file_name, "kind": "vision_ocr"},
                    ).insert()
            except Exception as exc:
                logger.warning("Vision analysis retry failed for %s: %s", doc.file_name, exc)

        if content:
            remaining = MAX_ATTACHMENT_CONTEXT_CHARS - used_chars
            excerpt = content[: min(MAX_ATTACHMENT_CHARS, remaining)]
            sections.append(f"## {doc.file_name} ({doc.file_type})\n{excerpt}")
            used_chars += len(excerpt)
            if len(content) > len(excerpt):
                sections[-1] += "\n[Content truncated to fit the chat context.]"
        else:
            kind = "image" if is_image else "document"
            sections.append(
                f"## {doc.file_name} ({doc.file_type})\n"
                f"No readable {kind} content was extracted. Do not claim to know what is inside it."
            )

        if used_chars >= MAX_ATTACHMENT_CONTEXT_CHARS:
            break

    if not sections:
        return ""

    image_note = (
        "At least one attachment is an image. Use its visual analysis to answer questions about what is shown, "
        "including objects, people, layout, text, diagrams, and visible relationships.\n\n"
        if any("(png)" in section or "(jpg)" in section or "(jpeg)" in section or "(gif)" in section or "(webp)" in section for section in sections)
        else ""
    )
    return (
        "The user attached or referenced the following files in this conversation. Their extracted contents are provided below. "
        "Answer from this content and identify the file when multiple files are present. "
        "Do not say you cannot view an image if visual analysis is included below.\n\n"
        + image_note
        + "\n\n".join(sections)
        + "\n\nUser's request:\n"
    )


async def _generate_image_message(
    prompt: str,
    user_id: str,
    workspace_id: str | None,
    drive_access_token: str | None = None,
    drive_refresh_token: str | None = None,
) -> str:
    image = await generate_and_store_image(
        prompt=prompt,
        user_id=user_id,
        workspace_id=workspace_id,
        drive_access_token=drive_access_token,
        drive_refresh_token=drive_refresh_token,
    )
    content = f"![Generated image]({image.download_url})"
    if image.revised_prompt and image.revised_prompt != prompt:
        content += f"\n\n*Prompt used: {image.revised_prompt}*"
    return content


def _friendly_chat_error(error: Exception) -> str:
    """Return a safe client-facing message; full details stay in server logs."""
    message = str(error)
    lowered = message.lower()
    err_type = type(error).__name__

    # Actual connection / transport network failures
    if any(net_err in err_type.lower() or net_err in lowered for net_err in ["connecterror", "connectionrefused", "clientconnecterror", "dnscounter", "socket.error"]):
        return "The AI provider is temporarily unavailable. Please retry."

    if "429" in message or "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
        return "The AI provider rate limit was reached. Please wait a moment and retry."

    if "api key" in lowered or "api_key" in lowered or "unauthenticated" in lowered or "invalid_key" in lowered:
        return "The AI service is not configured correctly. Please contact the administrator."

    if "timeout" in lowered or "timed out" in lowered:
        return "Agent execution timed out. Please retry."

    return "Unable to generate a response. Please retry."


def _chat_error_status(error: Exception) -> int:
    message = str(error).lower()
    if "429" in message or "rate limit" in message or "quota" in message:
        return 429
    if "timeout" in message or "timed out" in message:
        return 504
    return 503


class AttachmentInfo(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0, le=50 * 1024 * 1024)
    documentId: Optional[str] = None


class ChatRequest(BaseModel):
    request_id: Optional[str] = Field(default=None, min_length=8, max_length=128)
    message: str = Field(max_length=20_000)
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: str = "default"
    attachments: list[AttachmentInfo] = Field(default_factory=list, max_length=10)
    team_agents: list[str] = Field(default_factory=list, max_length=8)
    workspace_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        # Attachment-only messages are supported, but blank text must not
        # consume an agent execution when no attachment is supplied.
        if not value.strip() and not value:
            return ""
        return value.strip()


class ChatResponse(BaseModel):
    conversation_id: str
    output: str
    citations: list[dict] = Field(default_factory=list)
    agent_traces: list[dict] = Field(default_factory=list)
    events_count: int = 0
    success: bool = True
    error: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None


async def can_access_conversation(conv: Conversation, user_id: str) -> bool:
    if conv.user_id == user_id:
        return True
    if not conv.workspace_id:
        return False
    workspace = await Workspace.get(conv.workspace_id)
    return bool(workspace and (workspace.user_id == user_id or user_id in workspace.member_ids))


async def _generate_chat_topic(user_message: str, agent_message: str) -> str:
    """Use LLM to generate a clean, concise, 3-6 word topic title for a conversation."""
    try:
        from src.services.llm import get_llm_provider
        llm = get_llm_provider()
        topic = await llm.generate(
            prompt=f"User Prompt: {user_message[:400]}\nAssistant Response: {agent_message[:200]}",
            system_instruction=(
                "You are a topic title generator for an AI chat workspace. "
                "Analyze the user prompt and generate a concise, professional title-case topic title "
                "(3 to 6 words max). Output ONLY the title text itself with no quotes, markdown, or punctuation."
            ),
            temperature=0.3,
            max_output_tokens=25,
        )
        clean_topic = topic.strip().strip('"\'`').strip()
        if clean_topic and len(clean_topic) <= 90:
            return clean_topic
    except Exception as e:
        logger.warning(f"Could not generate LLM topic title: {e}")

    fallback = user_message.strip()
    return fallback[:60] + ("..." if len(fallback) > 60 else "")


async def _save_messages(
    conv_id: str,
    user_id: str,
    user_message: str,
    agent_message: str,
    agent_id: Optional[str] = None,
    is_new: bool = False,
    attachments: Optional[list[dict]] = None,
    workspace_id: Optional[str] = None,
    citations: Optional[list[dict]] = None,
    request_id: Optional[str] = None,
):
    """Persist one exchange idempotently using the client request ID."""
    try:
        user_metadata = {}
        if attachments:
            user_metadata["attachments"] = attachments
        if request_id:
            user_metadata["request_id"] = request_id

        now = datetime.now(timezone.utc)
        user_msg = Message(
            role="user",
            content=user_message,
            agent_id=agent_id,
            metadata=user_metadata,
        )
        assistant_msg = Message(
            role="assistant",
            content=agent_message,
            agent_id=agent_id,
            citations=[Citation(**c) for c in citations] if citations else [],
            metadata={"request_id": request_id} if request_id else {},
        )

        conv = await Conversation.get(conv_id)
        if conv:
            matching_indexes = [
                index for index, message in enumerate(conv.messages)
                if request_id and message.metadata.get("request_id") == request_id
            ]
            if matching_indexes:
                # A retry replaces the prior assistant result while retaining
                # exactly one copy of the original user request.
                first = matching_indexes[0]
                conv.messages = [
                    message for index, message in enumerate(conv.messages)
                    if index not in matching_indexes
                ]
                conv.messages[first:first] = [user_msg, assistant_msg]
            else:
                conv.messages.extend([user_msg, assistant_msg])
            conv.updated_at = now
            if workspace_id:
                conv.workspace_id = workspace_id
            if is_new or conv.title in ["New Conversation", "New Chat"] or len(conv.messages) <= 2:
                conv.title = user_message.strip()[:60] or "New Conversation"
            await conv.save()
        else:
            title = user_message.strip()[:60] or "New Conversation"
            conv = Conversation(
                id=conv_id,
                user_id=user_id,
                title=title,
                agent_id=agent_id,
                workspace_id=workspace_id,
                messages=[user_msg, assistant_msg],
                created_at=now,
                updated_at=now,
            )
            await conv.insert()

        # Extraction is intentionally best-effort and runs after persistence so
        # chat latency and reliability do not depend on the profiling model call.
        from src.services.memory.service import memory_service
        task = asyncio.create_task(memory_service.extract_from_exchange(
            user_id=user_id,
            user_message=user_message,
            assistant_message=agent_message,
            conversation_id=conv_id,
        ))
        def _log_extraction_failure(completed: asyncio.Task):
            if completed.cancelled():
                return
            error = completed.exception()
            if error:
                logger.warning("memory_extraction_failed", extra={"request_id": request_id, "error": str(error)[:500]})

        task.add_done_callback(_log_extraction_failure)
    except Exception as e:
        logger.error("chat_persistence_failed", extra={"request_id": request_id, "conversation_id": conv_id, "error": str(e)[:500]}, exc_info=True)


@router.get("/conversations")
async def list_conversations(http_request: Request, user_id: str = "default") -> list[dict]:
    """List all conversations for a user."""
    auth_user = getattr(http_request.state, "user", None)
    resolved_user_id = (auth_user.get("sub") if auth_user else None) or user_id
    user_email = auth_user.get("email") if auth_user else None

    query = {"$or": [{"user_id": resolved_user_id}]}
    if user_email:
        query["$or"].append({"user_id": user_email})

    owned = await Conversation.find(query).to_list()
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
    """Get a conversation with all messages (returns new conversation structure if not yet persisted)."""
    try:
        conv = await Conversation.get(conv_id)
    except Exception as e:
        logger.error("conversation_load_failed", extra={"conversation_id": conv_id, "error": str(e)[:500]}, exc_info=True)
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable") from e

    user_id = (getattr(http_request.state, "user", None) or {}).get("sub", "default")
    if not conv:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "id": conv_id,
            "title": "New Conversation",
            "agentId": "boss_agent",
            "workspaceId": None,
            "messages": [],
            "createdAt": now_iso,
            "updatedAt": now_iso,
        }
    if not await can_access_conversation(conv, user_id):
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
                "citations": [citation.model_dump() for citation in m.citations],
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


class RenameConversationRequest(BaseModel):
    title: str


@router.patch("/conversations/{conv_id}")
async def rename_conversation(
    conv_id: str, body: RenameConversationRequest, http_request: Request
) -> dict:
    """Rename a conversation (owner only)."""
    conv = await Conversation.get(conv_id)
    user_id = (getattr(http_request.state, "user", None) or {}).get("sub", "default")
    if not conv or conv.user_id != user_id:
        raise HTTPException(404, "Conversation not found")
    new_title = body.title.strip()[:120]
    if not new_title:
        raise HTTPException(400, "Title cannot be empty")
    conv.title = new_title
    conv.updated_at = datetime.now(timezone.utc)
    await conv.save()
    return {"success": True, "id": str(conv.id), "title": conv.title}



async def _build_full_conversation_history(conv_id: Optional[str], max_messages: int = 50, max_chars: int = 30000) -> str:
    """Format recent conversation history from MongoDB without truncating message contents to tiny snippets."""
    if not conv_id:
        return ""
    try:
        conv = await Conversation.get(conv_id)
        if not conv or not conv.messages:
            return ""

        recent = conv.messages[-max_messages:]
        lines = []
        for m in recent:
            role = "USER" if m.role == "user" else f"ASSISTANT ({m.agent_id or 'Agent'})"
            content = (m.content or "").strip()
            if content:
                lines.append(f"{role}: {content}")
            if m.metadata and isinstance(m.metadata, dict):
                atts = m.metadata.get("attachments")
                if atts and isinstance(atts, list):
                    for a in atts:
                        name = a.get("name") if isinstance(a, dict) else getattr(a, "name", None)
                        if name:
                            lines.append(f"   [Attached file: {name}]")

        if not lines:
            return ""

        history_str = "\n".join(lines)
        if len(history_str) > max_chars:
            history_str = "... (earlier conversation history omitted)\n" + history_str[-max_chars:]
        return history_str
    except Exception as e:
        logger.warning(f"Could not load conversation history for {conv_id}: {e}")
        return ""


@router.post("")
async def chat(http_request: Request, body: ChatRequest, response: Response) -> ChatResponse:
    if not body.message and not body.attachments:
        raise HTTPException(status_code=400, detail="Message or attachment is required")
    conv_id = body.conversation_id or str(PydanticObjectId())
    request_id = body.request_id or getattr(http_request.state, "request_id", None) or http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_started_at = time.perf_counter()
    try:
        is_new = not bool(body.conversation_id)

        # Use authenticated user from JWT if available, fall back to request body
        auth_user = getattr(http_request.state, "user", None)
        user_id = (auth_user.get("sub") if auth_user else None) or body.user_id
        # Authorize stored state before it can be read into the LLM context.
        if body.conversation_id:
            existing = await Conversation.get(body.conversation_id)
            if existing and not await can_access_conversation(existing, user_id):
                raise HTTPException(status_code=404, detail="Conversation not found")
            is_new = existing is None
        if body.workspace_id:
            workspace = await Workspace.get(body.workspace_id)
            if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
                raise HTTPException(status_code=404, detail="Workspace not found")

        from src.services.memory.service import memory_service
        try:
            async with asyncio.timeout(settings.chat_context_timeout_seconds):
                memory_context, attachment_context, history_snippet = await asyncio.gather(
                    memory_service.build_context(user_id, body.message),
                    _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),
                    _build_full_conversation_history(body.conversation_id),
                )
        except TimeoutError:
            _chat_log(request_id, "context", "error", request_started_at, error="context timeout")
            memory_context, attachment_context, history_snippet = "", "", ""

        history_prefix = f"=== PREVIOUS CONVERSATION HISTORY ===\n{history_snippet}\n====================================\n\n" if history_snippet else ""
        augmented_message = history_prefix + memory_context + attachment_context + body.message
        augmented_message = _adk_routing_preamble(body.agent_id, body.team_agents) + augmented_message

        routed_agent_id = AgentRouter().route_smart(body.message, body.agent_id)
        automatic_mode = body.agent_id in (None, "auto") and not body.team_agents
        automatic_plan = plan_dynamic(body.message, bool(body.attachments), bool(body.workspace_id)) if automatic_mode else None
        # Automatic requests use one explicitly selected specialist by default.
        # Escalate to the supervisor only when the structured plan requires
        # multiple independent responsibilities.
        planned_agent_id = (automatic_plan or {}).get("steps", [{}])[0].get("agent_id") if automatic_plan else None
        effective_agent_id = routed_agent_id if routed_agent_id != "auto" else planned_agent_id
        use_dynamic_orchestration = bool(automatic_mode and len((automatic_plan or {}).get("steps", [])) > 1)

        google_access_token = http_request.headers.get("X-Google-Access-Token", "")
        google_refresh_token = http_request.headers.get("X-Google-Refresh-Token", "")
        custom_config = await AgentConfig.find_one(AgentConfig.agent_id == body.agent_id, AgentConfig.user_id == user_id, AgentConfig.custom == True) if body.agent_id and body.agent_id.startswith("custom_") else None
        if custom_config:
            augmented_message = (
                "CUSTOM ADK AGENT INSTRUCTION:\n"
                f"{custom_config.system_instruction}\n\n"
                + augmented_message
            )

        now_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M UTC")
        augmented_message = f"SYSTEM TIME CONTEXT: Current server time is {now_str}.\n\n" + augmented_message
        google_agent_context = {
            "user_id": user_id,
            "workspace_id": body.workspace_id,
            "google_access_token": google_access_token,
            "google_refresh_token": google_refresh_token,
            "current_datetime": now_str,
            "conversation_history": history_snippet,
            "has_attachments": bool(body.attachments),
            "request_id": request_id,
        }

        explicit_agent_id = body.agent_id if (body.agent_id and body.agent_id not in ("auto", "image") and not body.agent_id.startswith("custom_")) else None
        registry_agent = get_boss_agent().registry.get_metadata(explicit_agent_id) if explicit_agent_id else None
        if (
            body.agent_id not in (None, "auto", "image")
            and not body.agent_id.startswith("custom_")
            and body.agent_id not in ADK_BUILTIN_AGENT_IDS
            and not registry_agent
        ):
            raise HTTPException(status_code=422, detail=f"Unknown or disabled agent: {body.agent_id}")
        if body.agent_id and body.agent_id.startswith("custom_") and not custom_config:
            raise HTTPException(status_code=422, detail="Unknown or disabled custom agent")
        invalid_team_agents = [agent_id for agent_id in body.team_agents if not get_boss_agent().registry.get_metadata(agent_id)]
        if invalid_team_agents:
            raise HTTPException(status_code=422, detail=f"Unknown or disabled team agent: {invalid_team_agents[0]}")

        if routed_agent_id == "image":
            drive_token = http_request.headers.get("X-Drive-Access-Token") or google_access_token
            drive_refresh = http_request.headers.get("X-Drive-Refresh-Token") or google_refresh_token
            output = await _generate_image_message(
                body.message, user_id, body.workspace_id,
                drive_access_token=drive_token, drive_refresh_token=drive_refresh
            )
            result = {"output": output, "citations": [], "agent_traces": [{"agent_id": "image", "event_type": "ImageGeneration", "has_content": True}], "events_count": 1}
        else:
            result = await process_message(message=augmented_message, user_id=user_id, conversation_id=conv_id, workspace_id=body.workspace_id)

        # Persist messages to MongoDB (use clean body.message for display/title, not augmented)
        attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
        await _save_messages(
            conv_id=conv_id,
            user_id=user_id,
            user_message=body.message,
            agent_message=result["output"],
            agent_id=effective_agent_id or body.agent_id,
            is_new=is_new,
            attachments=attachments_data,
            workspace_id=body.workspace_id,
            citations=result.get("citations"),
            request_id=request_id,
        )

        return ChatResponse(
            conversation_id=conv_id,
            output=result["output"],
            citations=result.get("citations", []),
            agent_traces=result.get("agent_traces", []),
            events_count=result.get("events_count", 0),
            success=True,
            request_id=request_id,
        )
    except HTTPException:
        # Preserve real client errors (notably conversation authorization) as
        # their intended HTTP status instead of turning them into a 200 chat
        # payload that looks like a model failure.
        raise
    except Exception as e:
        friendly_error = _friendly_chat_error(e)
        response.status_code = _chat_error_status(e)
        _chat_log(request_id, "request", "error", request_started_at, error=str(e)[:500])
        logger.error(f"Chat error [{request_id}]: {e}", exc_info=True)
        return ChatResponse(
            conversation_id=conv_id,
            output=friendly_error,
            citations=[],
            agent_traces=[],
            events_count=0,
            success=False,
            error=friendly_error,
            error_code="CHAT_REQUEST_FAILED",
            request_id=request_id,
        )


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
    if not body.message and not body.attachments:
        raise HTTPException(status_code=400, detail="Message or attachment is required")
    request_id = body.request_id or getattr(http_request.state, "request_id", None) or http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_started_at = time.perf_counter()
    _chat_log(request_id, "request", "start", input_chars=len(body.message), has_attachments=bool(body.attachments))
    conv_id = body.conversation_id or str(PydanticObjectId())
    is_new = not bool(body.conversation_id)

    # Use authenticated user from JWT if available
    auth_user = getattr(http_request.state, "user", None)
    user_id = (auth_user.get("sub") if auth_user else None) or body.user_id
    _chat_log(request_id, "authentication", "complete", request_started_at, authenticated=bool(auth_user), user_id_present=bool(user_id))
    if body.conversation_id:
        existing = await Conversation.get(body.conversation_id)
        if existing and not await can_access_conversation(existing, user_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Keep stream and non-stream semantics aligned with GET
        # /conversations/{id}: an unknown, valid ID represents a new chat,
        # while an existing conversation owned by somebody else remains 404.
        is_new = existing is None
    _chat_log(request_id, "conversation", "complete", request_started_at, conversation_id=conv_id, is_new=is_new)
    if body.workspace_id:
        workspace = await Workspace.get(body.workspace_id)
        if not workspace or (workspace.user_id != user_id and user_id not in workspace.member_ids):
            raise HTTPException(status_code=404, detail="Workspace not found")
    routed_agent_id = AgentRouter().route_smart(body.message, body.agent_id)
    automatic_mode = body.agent_id in (None, "auto") and not body.team_agents
    dynamic_plan = plan_dynamic(body.message, bool(body.attachments), bool(body.workspace_id)) if automatic_mode else None
    planned_agent_id = (dynamic_plan or {}).get("steps", [{}])[0].get("agent_id") if dynamic_plan else None
    effective_agent_id = routed_agent_id if routed_agent_id != "auto" else planned_agent_id
    use_dynamic_orchestration = bool(automatic_mode and len((dynamic_plan or {}).get("steps", [])) > 1)
    fast_path = bool(
        automatic_mode
        and not body.attachments
        and not body.workspace_id
        and not body.conversation_id
        and len((dynamic_plan or {}).get("steps", [])) <= 1
        and not re.search(r"(?i)\b(research|latest|current|search|calculate|calendar|drive|file|pdf|web)\b", body.message)
    )
    _chat_log(request_id, "routing", "complete", request_started_at, routed_agent=effective_agent_id, automatic=automatic_mode, supervisor=use_dynamic_orchestration)
    custom_config = await AgentConfig.find_one(AgentConfig.agent_id == body.agent_id, AgentConfig.user_id == user_id, AgentConfig.custom == True) if body.agent_id and body.agent_id.startswith("custom_") else None
    explicit_registry_agent = get_boss_agent().registry.get_metadata(effective_agent_id) if effective_agent_id else None
    if (
        body.agent_id not in (None, "auto", "image")
        and not body.agent_id.startswith("custom_")
        and body.agent_id not in ADK_BUILTIN_AGENT_IDS
        and not explicit_registry_agent
    ):
        raise HTTPException(status_code=422, detail=f"Unknown or disabled agent: {body.agent_id}")
    if body.agent_id and body.agent_id.startswith("custom_") and not custom_config:
        raise HTTPException(status_code=422, detail="Unknown or disabled custom agent")
    invalid_team_agents = [agent_id for agent_id in body.team_agents if not get_boss_agent().registry.get_metadata(agent_id)]
    if invalid_team_agents:
        raise HTTPException(status_code=422, detail=f"Unknown or disabled team agent: {invalid_team_agents[0]}")

    accumulated_output = ""

    async def event_generator():
        nonlocal accumulated_output
        try:
            # Open the response immediately, then prepare optional context while
            # the client is already showing the active assistant state.
            yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id, 'request_id': request_id})}\n\n"
            from src.services.memory.service import memory_service
            context_started_at = time.perf_counter()
            _chat_log(request_id, "context", "start", fast_path=fast_path)
            if fast_path:
                memory_context, attachment_context, history_snippet = "", "", ""
            else:
                try:
                    async with asyncio.timeout(settings.chat_context_timeout_seconds):
                        memory_context, attachment_context, history_snippet = await asyncio.gather(
                            memory_service.build_context(user_id, body.message),
                            _build_attachment_context(body.attachments, user_id, body.message, conv_id=body.conversation_id),
                            _build_full_conversation_history(body.conversation_id),
                        )
                except TimeoutError:
                    _chat_log(request_id, "context", "error", context_started_at, error="context timeout")
                    memory_context, attachment_context, history_snippet = "", "", ""
            _chat_log(request_id, "context", "complete", context_started_at, history_chars=len(history_snippet or ""), attachment_chars=len(attachment_context or ""))
            history_prefix = f"=== PREVIOUS CONVERSATION HISTORY ===\n{history_snippet}\n====================================\n\n" if history_snippet else ""
            augmented_message = history_prefix + memory_context + attachment_context + body.message
            augmented_message = _adk_routing_preamble(body.agent_id, body.team_agents) + augmented_message
            if custom_config:
                augmented_message = (
                    "CUSTOM ADK AGENT INSTRUCTION:\n"
                    f"{custom_config.system_instruction}\n\n"
                    + augmented_message
                )

            now_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M UTC")
            augmented_message = f"SYSTEM TIME CONTEXT: Current server time is {now_str}.\n\n" + augmented_message
            stream_google_context = {
                "user_id": user_id,
                "workspace_id": body.workspace_id,
                "google_access_token": http_request.headers.get("X-Google-Access-Token", ""),
                "google_refresh_token": http_request.headers.get("X-Google-Refresh-Token", ""),
                "current_datetime": now_str,
                "conversation_history": history_snippet,
                "has_attachments": bool(body.attachments),
                "request_id": request_id,
            }

            event_queue: list[dict] = []

            if routed_agent_id == "image":
                drive_token = http_request.headers.get("X-Drive-Access-Token") or stream_google_context["google_access_token"]
                drive_refresh = http_request.headers.get("X-Drive-Refresh-Token") or stream_google_context["google_refresh_token"]
                async for done, value in _await_with_heartbeats(
                    _generate_image_message(
                        body.message, user_id, body.workspace_id,
                        drive_access_token=drive_token, drive_refresh_token=drive_refresh,
                    ),
                    http_request,
                    settings.chat_stream_timeout_seconds,
                ):
                    if not done:
                        yield ": heartbeat\n\n"
                    else:
                        accumulated_output = value
                yield f"event: agent\ndata: {json.dumps({'agent_id': 'image'})}\n\n"
                yield f"event: chunk\ndata: {json.dumps({'text': accumulated_output})}\n\n"
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(
                    conv_id=conv_id, user_id=user_id, user_message=body.message,
                    agent_message=accumulated_output, agent_id="image", is_new=is_new,
                    attachments=attachments_data, workspace_id=body.workspace_id,
                    request_id=request_id,
                )
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            # All conversational specialist, team, and workspace requests run
            # through the same ADK hierarchy.  This prevents selected agents
            # from bypassing Google grounding and provider/key failover via the
            # legacy llm_service execution paths below.
            async for sse_event in process_message_stream(
                message=augmented_message, user_id=user_id, conversation_id=conv_id, workspace_id=body.workspace_id,
            ):
                if await http_request.is_disconnected():
                    return
                event_type = "complete" if sse_event["event"] == "completed" else sse_event["event"]
                data = sse_event["data"]
                if event_type == "start":
                    continue
                if event_type == "chunk":
                    accumulated_output += data.get("text", "")
                if event_type == "complete":
                    attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                    await _save_messages(
                        conv_id=conv_id, user_id=user_id, user_message=body.message,
                        agent_message=data.get("output", accumulated_output),
                        agent_id=effective_agent_id or body.agent_id, is_new=is_new,
                        attachments=attachments_data, workspace_id=body.workspace_id,
                        citations=data.get("citations"), request_id=request_id,
                    )
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            return

            if use_dynamic_orchestration and routed_agent_id != "image":
                _chat_log(request_id, "orchestration", "start", plan_agents=[step.get("agent_id") for step in dynamic_plan.get("steps", [])])

                # The queue lets the dynamic executor report live progress
                # while specialist tasks run concurrently via BossAgent.
                async def on_dynamic_event(event_name: str, data: dict):
                    # Translate internal Boss events into the stable SSE
                    # contract consumed by the UI.
                    if event_name == "plan_created":
                        event_queue.append({"event": "plan", "data": {
                            "complexity": data.get("complexity"),
                            "agents": [
                                {"agent_id": item.get("agent_id"), "label": item.get("title"), "reason": item.get("objective")}
                                for item in data.get("nodes", [])
                                if item.get("agent_id") != "final-synthesizer"
                            ],
                        }})
                    elif event_name == "agent_completed":
                        event_queue.append({"event": "agent_complete", "data": {**data, "success": True}})
                    elif event_name == "agent_failed":
                        event_queue.append({"event": "agent_complete", "data": {**data, "success": False}})
                    else:
                        event_queue.append({"event": event_name, "data": data})

                dynamic_task = asyncio.create_task(get_boss_agent().process_dynamic(
                    augmented_message,
                    user_id,
                    dynamic_plan,
                    conv_id,
                    context=stream_google_context,
                    on_event=on_dynamic_event,
                ))
                dynamic_deadline = asyncio.get_running_loop().time() + settings.chat_stream_timeout_seconds
                last_heartbeat = asyncio.get_running_loop().time()
                while not dynamic_task.done() or event_queue:
                    if await http_request.is_disconnected():
                        dynamic_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await dynamic_task
                        _chat_log(request_id, "request", "complete", request_started_at, cancelled=True)
                        return
                    while event_queue:
                        queued = event_queue.pop(0)
                        yield f"event: {queued['event']}\ndata: {json.dumps(queued['data'], ensure_ascii=False)}\n\n"
                    if not dynamic_task.done():
                        now = asyncio.get_running_loop().time()
                        if now - last_heartbeat > 1.5:
                            yield ": heartbeat\n\n"
                            last_heartbeat = now
                        if now >= dynamic_deadline:
                            dynamic_task.cancel()
                            with contextlib.suppress(asyncio.CancelledError):
                                await dynamic_task
                            raise TimeoutError("BossAgent execution timed out")
                        await asyncio.sleep(0.05)
                dynamic_result = await dynamic_task
                _chat_log(request_id, "boss_agent", "complete", request_started_at, output_chars=len(dynamic_result.get("output") or ""))
                accumulated_output = dynamic_result["output"]
                async for word in _word_chunks(accumulated_output):
                    yield f"event: chunk\ndata: {json.dumps({'text': word})}\n\n"
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(
                    conv_id=conv_id, user_id=user_id, user_message=body.message,
                    agent_message=accumulated_output, agent_id="boss_agent", is_new=is_new,
                    attachments=attachments_data, workspace_id=body.workspace_id,
                    citations=dynamic_result.get("citations"),
                    request_id=request_id,
                )
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id, 'citations': dynamic_result.get('citations', [])})}\n\n"
                return

            if body.team_agents:
                team_result = None
                async for done, value in _await_with_heartbeats(
                    get_boss_agent().process_team(
                        augmented_message,
                        user_id,
                        body.team_agents,
                        conv_id,
                        context={"google_access_token": http_request.headers.get("X-Google-Access-Token", ""), "google_refresh_token": http_request.headers.get("X-Google-Refresh-Token", ""), "conversation_history": history_snippet},
                    ),
                    http_request,
                    settings.chat_stream_timeout_seconds,
                ):
                    if not done:
                        yield ": heartbeat\n\n"
                    else:
                        team_result = value
                if not team_result or not team_result.get("success"):
                    raise RuntimeError((team_result or {}).get("output") or "Team execution failed")
                for stage in team_result["stages"]:
                    yield f"event: agent\ndata: {json.dumps({'agent_id': stage['agent_id']})}\n\n"
                    yield f"event: team_stage\ndata: {json.dumps({'agent_id': stage['agent_id'], 'status': 'complete'})}\n\n"
                    stage_text = f"### {stage['agent_id'].title()} Agent\n{stage['output']}\n\n"
                    async for word in _word_chunks(stage_text):
                        yield f"event: chunk\ndata: {json.dumps({'text': word})}\n\n"
                accumulated_output = team_result["output"]
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(
                    conv_id=conv_id, user_id=user_id, user_message=body.message,
                    agent_message=accumulated_output, agent_id="teamwork", is_new=is_new,
                    attachments=attachments_data,
                    workspace_id=body.workspace_id,
                    request_id=request_id,
                )
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            if custom_config:
                custom_agent = CustomAgent(custom_config)
                get_boss_agent().registry.register(custom_agent)
                agent_result = None
                async for done, value in _await_with_heartbeats(
                    custom_agent.execute(augmented_message, {"user_id": user_id, "conversation_history": history_snippet, "request_id": request_id}),
                    http_request,
                    settings.agentic_agent_timeout_seconds,
                ):
                    if not done:
                        yield ": heartbeat\n\n"
                    else:
                        agent_result = value
                if not agent_result.success or not (agent_result.output or "").strip():
                    raise RuntimeError(agent_result.error or "Selected agent returned an empty response")
                yield f"event: agent\ndata: {json.dumps({'agent_id': custom_config.agent_id})}\n\n"
                async for word in _word_chunks(agent_result.output):
                    yield f"event: chunk\ndata: {json.dumps({'text': word})}\n\n"
                accumulated_output = agent_result.output
                attachments_data = [a.model_dump() for a in body.attachments] if body.attachments else None
                await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id=custom_config.agent_id, is_new=is_new, attachments=attachments_data, workspace_id=body.workspace_id, request_id=request_id)
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"
                return

            explicit_agent_id = body.agent_id if (body.agent_id and body.agent_id not in ("auto", "image") and not body.agent_id.startswith("custom_")) else None
            registry_agent = get_boss_agent().registry.get_agent(explicit_agent_id) if explicit_agent_id else None

            if registry_agent:
                agent_result = None
                async for done, value in _await_with_heartbeats(
                    registry_agent.execute(augmented_message, stream_google_context),
                    http_request,
                    settings.agentic_agent_timeout_seconds,
                ):
                    if not done:
                        yield ": heartbeat\n\n"
                    else:
                        agent_result = value
                if not agent_result.success or not (agent_result.output or "").strip():
                    raise RuntimeError(agent_result.error or "Selected agent returned an empty response")
                yield f"event: agent\ndata: {json.dumps({'agent_id': explicit_agent_id})}\n\n"
                async for word in _word_chunks(agent_result.output):
                    yield f"event: chunk\ndata: {json.dumps({'text': word})}\n\n"
                accumulated_output = agent_result.output
                await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id=explicit_agent_id, is_new=is_new, workspace_id=body.workspace_id, citations=agent_result.citations, request_id=request_id)
                yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id, 'citations': agent_result.citations})}\n\n"
                return

            if body.workspace_id and body.agent_id in (None, "auto", "knowledge"):
                knowledge_agent = get_boss_agent().registry.get_agent("knowledge")
                if knowledge_agent:
                    agent_result = None
                    async for done, value in _await_with_heartbeats(
                        knowledge_agent.execute(
                            augmented_message, {**stream_google_context, "workspace_id": body.workspace_id, "conversation_id": conv_id}
                        ),
                        http_request,
                        settings.agentic_agent_timeout_seconds,
                    ):
                        if not done:
                            yield ": heartbeat\n\n"
                        else:
                            agent_result = value
                    if not agent_result.success or not (agent_result.output or "").strip():
                        raise RuntimeError(agent_result.error or "Knowledge agent returned an empty response")
                    yield f"event: agent\ndata: {json.dumps({'agent_id': 'knowledge'})}\n\n"
                    async for word in _word_chunks(agent_result.output):
                        yield f"event: chunk\ndata: {json.dumps({'text': word})}\n\n"
                    accumulated_output = agent_result.output
                    await _save_messages(conv_id=conv_id, user_id=user_id, user_message=body.message, agent_message=accumulated_output, agent_id="knowledge", is_new=is_new, workspace_id=body.workspace_id, citations=agent_result.citations, request_id=request_id)
                    yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id, 'citations': agent_result.citations})}\n\n"
                    return


            async for sse_event in process_message_stream(
                message=augmented_message, user_id=user_id, conversation_id=conv_id,
            ):
                if await http_request.is_disconnected():
                    break

                # ADK runner historically emits ``completed`` while the chat
                # SSE contract (and frontend) uses ``complete``. Normalize at
                # the API boundary so a valid ADK response cannot be mistaken
                # for a stream that closed without completion.
                event_type = "complete" if sse_event["event"] == "completed" else sse_event["event"]
                data = sse_event["data"]
                if event_type in {"agent", "trace", "complete", "error"}:
                    _chat_log(request_id, f"stream_{event_type}", "complete", request_started_at, agent_id=data.get("agent_id"))

                # The endpoint has already sent its start event before context
                # preparation, so avoid sending a duplicate from the runner.
                if event_type == "start":
                    continue

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
                        agent_id=effective_agent_id or body.agent_id,
                        is_new=is_new,
                        attachments=attachments_data,
                        workspace_id=body.workspace_id,
                        citations=data.get("citations"),
                        request_id=request_id,
                    )

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        except Exception as e:
            friendly_error = _friendly_chat_error(e)
            logger.error(f"Stream error: {e}", exc_info=True)
            _chat_log(request_id, "request", "error", request_started_at, error=str(e)[:500], output_chars=len(accumulated_output))
            # Still try to save what we have
            if accumulated_output:
                await _save_messages(
                    conv_id=conv_id,
                    user_id=user_id,
                    user_message=body.message,
                    agent_message=accumulated_output,
                    agent_id=effective_agent_id or body.agent_id,
                    is_new=is_new,
                    request_id=request_id,
                )
            yield f"event: error\ndata: {json.dumps({'error': friendly_error, 'code': 'CHAT_REQUEST_FAILED', 'request_id': request_id})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'output': accumulated_output, 'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
