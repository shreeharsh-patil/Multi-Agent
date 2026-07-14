from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.services.rag.retriever import get_retriever
from src.services.llm import llm_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


class QueryRequest(BaseModel):
    query: str
    user_id: str = "default"
    document_ids: Optional[list[str]] = None
    top_k: int = 5


@router.post("/query")
async def query_knowledge(request: QueryRequest) -> dict:
    try:
        from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
        if await should_use_opendocuments(request.user_id):
            res = await opendocuments_client.query_rag(request.query, top_k=request.top_k)
            return res

        retriever = get_retriever()
        docs = await retriever.retrieve(
            query=request.query,
            user_id=request.user_id,
            top_k=request.top_k,
        )

        if not docs:
            return {
                "results": [],
                "citations": [],
                "answer": "No relevant documents found.",
            }

        response, citations = await llm_service.generate_with_citations(
            prompt=request.query,
            context=docs,
        )

        return {
            "results": docs,
            "citations": citations,
            "answer": response,
        }
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
