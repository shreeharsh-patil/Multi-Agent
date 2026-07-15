from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from src.services.rag.retriever import get_retriever
from src.services.llm import llm_service
from src.models.search_history import SearchHistory
from src.api.middleware import resolve_user_id
from src.utils.logger import logger

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


class QueryRequest(BaseModel):
    query: str
    user_id: str = "default"
    document_ids: Optional[list[str]] = None
    top_k: int = 5
    workspace_id: Optional[str] = None


@router.post("/query")
async def query_knowledge(request: QueryRequest, http_request: Request) -> dict:
    user_id = resolve_user_id(http_request, request.user_id)
    try:
        from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
        if await should_use_opendocuments(user_id):
            res = await opendocuments_client.query_rag(request.query, top_k=request.top_k)
            await _save_search(user_id, request.query, res.get("answer", ""))
            return res

        retriever = get_retriever()
        docs = await retriever.retrieve(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            workspace_id=request.workspace_id,
        )

        if not docs:
            await _save_search(user_id, request.query, "No relevant documents found.")
            return {
                "results": [],
                "citations": [],
                "answer": "No relevant documents found.",
            }

        response, citations = await llm_service.generate_with_citations(
            prompt=request.query,
            context=docs,
        )

        await _save_search(user_id, request.query, response)

        return {
            "results": docs,
            "citations": citations,
            "answer": response,
        }
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _save_search(user_id: str, query: str, answer: str) -> None:
    """Persist a knowledge query so users can revisit their search history."""
    try:
        await SearchHistory(user_id=user_id, query=query, answer=answer or "").insert()
    except Exception as e:
        logger.error(f"Failed to save search history: {e}")


@router.get("/history")
async def list_search_history(http_request: Request, limit: int = 50) -> list[dict]:
    """List the user's recent knowledge searches, newest first."""
    user_id = resolve_user_id(http_request)
    items = await SearchHistory.find(
        SearchHistory.user_id == user_id
    ).sort(-SearchHistory.created_at).limit(limit).to_list()
    return [
        {
            "id": str(h.id),
            "query": h.query,
            "answer": h.answer,
            "createdAt": h.created_at.isoformat(),
        }
        for h in items
    ]


@router.delete("/history/{history_id}")
async def delete_search_history(history_id: str, http_request: Request) -> dict:
    """Delete a single search-history entry."""
    user_id = resolve_user_id(http_request)
    item = await SearchHistory.get(history_id)
    if not item or item.user_id != user_id:
        raise HTTPException(404, "History entry not found")
    await item.delete()
    return {"success": True}
