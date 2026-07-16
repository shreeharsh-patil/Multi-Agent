import asyncio
from typing import Optional
import chromadb
from chromadb.config import Settings
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


class ChromaVectorStore(VectorStore):
    def __init__(self):
        self._client = None
        self._lock = asyncio.Lock()

    async def _get_client(self):
        if self._client is None:
            async with self._lock:
                if self._client is not None:
                    return self._client
                self._client = await asyncio.to_thread(
                    lambda: chromadb.PersistentClient(
                        path=settings.chroma_persist_dir,
                        settings=Settings(anonymized_telemetry=False),
                    )
                )
                logger.info(f"ChromaDB initialized at {settings.chroma_persist_dir}")
        return self._client

    async def store_embeddings(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        client = await self._get_client()
        collection_obj = await asyncio.to_thread(client.get_or_create_collection, collection)
        metadatas = []
        documents = []
        for p in payloads:
            metadatas.append({k: str(v) if isinstance(v, (dict, list)) else v for k, v in p.items() if k != "content"})
            documents.append(p.get("content", ""))

        await asyncio.to_thread(
            collection_obj.add,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.info(f"Stored {len(ids)} embeddings in collection '{collection}'")

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        try:
            client = await self._get_client()
            collection_obj = await asyncio.to_thread(client.get_collection, collection)
            results = await asyncio.to_thread(
                collection_obj.query,
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict,
            )
            hits = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1.0 / (1.0 + distance)
                    hits.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": score,
                    })
            return hits
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

    async def delete(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        try:
            client = await self._get_client()
            collection_obj = await asyncio.to_thread(client.get_collection, collection)
            await asyncio.to_thread(collection_obj.delete, ids=ids)
            logger.info(f"Deleted {len(ids)} from collection '{collection}'")
        except Exception as e:
            logger.warning(f"Delete failed: {e}")

    async def create_collection(self, collection: str) -> None:
        client = await self._get_client()
        await asyncio.to_thread(client.get_or_create_collection, collection)
        logger.info(f"Ensured collection '{collection}' exists")
