from typing import Optional
from datetime import datetime
from src.models.memory import MemoryItem
from src.services.rag.embeddings import embedding_service
from src.services.vector_store.factory import vector_store
from src.utils.logger import logger


class MemoryService:
    def __init__(self):
        self.collection = "memories"

    async def store(
        self,
        user_id: str,
        key: str,
        content: str,
        type: str = "conversation",
        value: Optional[dict] = None,
    ) -> MemoryItem:
        memory = MemoryItem(
            user_id=user_id,
            type=type,
            key=key,
            content=content,
            value=value,
        )

        embedding = await embedding_service.embed_text(content)
        memory.embedding = embedding

        await memory.insert()

        await vector_store.store_embeddings(
            collection=self.collection,
            ids=[str(memory.id)],
            embeddings=[embedding],
            payloads=[{
                "user_id": user_id,
                "key": key,
                "content": content,
                "type": type,
            }],
        )

        logger.info(f"Stored memory: {key}")
        return memory

    async def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        query_embedding = await embedding_service.embed_text(query)

        results = await vector_store.search(
            collection=self.collection,
            query_embedding=query_embedding,
            top_k=top_k,
            filter={"user_id": user_id},
        )

        return results

    async def get_recent(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        memories = await MemoryItem.find(
            MemoryItem.user_id == user_id
        ).sort(-MemoryItem.created_at).limit(limit).to_list()

        return memories

    async def delete(self, memory_id: str) -> bool:
        memory = await MemoryItem.get(memory_id)
        if memory:
            await memory.delete()
            await vector_store.delete(self.collection, [memory_id])
            return True
        return False


memory_service = MemoryService()
