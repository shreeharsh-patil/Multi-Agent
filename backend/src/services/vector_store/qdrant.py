import asyncio
import hashlib
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


def _deterministic_id(id_str: str) -> int:
    """Generate a deterministic positive 64-bit integer from a string ID."""
    digest = hashlib.sha256(id_str.encode()).hexdigest()
    return int(digest[:16], 16)


class QdrantVectorStore(VectorStore):
    def __init__(self):
        kwargs = {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
        }
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
            kwargs["https"] = True
        self.client = QdrantClient(**kwargs)
        logger.info(f"Qdrant initialized at {settings.qdrant_host}:{settings.qdrant_port}")

    async def store_embeddings(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        await self.create_collection(collection)
        points = [
            PointStruct(
                id=_deterministic_id(id_str),
                vector=emb,
                payload=payload,
            )
            for id_str, emb, payload in zip(ids, embeddings, payloads)
        ]
        await asyncio.to_thread(
            self.client.upsert,
            collection_name=collection,
            points=points,
        )
        logger.info(f"Stored {len(points)} points in '{collection}'")

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        try:
            search_filter = None
            if filter_dict:
                conditions = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_dict.items()]
                search_filter = Filter(must=conditions)

            results = await asyncio.to_thread(
                self.client.search,
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=search_filter,
            )
            return [
                {
                    "id": str(r.id),
                    "content": r.payload.get("content", ""),
                    "metadata": {k: v for k, v in r.payload.items() if k != "content"},
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

    async def delete(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        point_ids = [_deterministic_id(id_str) for id_str in ids]
        await asyncio.to_thread(
            self.client.delete,
            collection_name=collection,
            points_selector=point_ids,
        )
        logger.info(f"Deleted {len(ids)} from '{collection}'")

    async def create_collection(self, collection: str) -> None:
        collections = await asyncio.to_thread(self.client.get_collections)
        if not any(c.name == collection for c in collections.collections):
            await asyncio.to_thread(
                self.client.create_collection,
                collection_name=collection,
                vectors_config=VectorParams(size=settings.embedding_dimension, distance=Distance.COSINE),
            )
            logger.info(f"Created collection '{collection}'")
