from typing import Optional
from src.services.rag.embeddings import embedding_service
from src.services.vector_store.factory import get_vector_store
from src.utils.logger import logger


class Retriever:
    def __init__(self, collection: str = "documents"):
        self.collection = collection

    async def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        query_embedding = await embedding_service.embed_text(query)

        filter_dict = None
        if user_id:
            filter_dict = {"user_id": user_id}

        vs = get_vector_store()
        results = await vs.search(
            collection=self.collection,
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter_dict,
        )

        logger.info(f"Retrieved {len(results)} results for query")
        return results

    async def store_document_chunks(
        self,
        chunks: list[dict],
        user_id: str,
        document_id: str,
        file_name: str,
    ) -> None:
        texts = [c["content"] for c in chunks]
        embeddings = await embedding_service.embed_batch(texts)

        ids = [f"{document_id}_{c['chunk_index']}" for c in chunks]
        payloads = [
            {
                "content": c["content"],
                "user_id": user_id,
                "document_id": document_id,
                "file_name": file_name,
                "chunk_index": c["chunk_index"],
                "page_number": c.get("page_number"),
                "section": c.get("section"),
            }
            for c in chunks
        ]

        vs = get_vector_store()
        await vs.store_embeddings(
            collection=self.collection,
            ids=ids,
            embeddings=embeddings,
            payloads=payloads,
        )

        logger.info(f"Stored {len(chunks)} chunks for document '{file_name}'")


_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
