from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


class QdrantVectorStore(VectorStore):
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
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
                id=int(hash(id_str) % (2**63)),
                vector=emb,
                payload=payload,
            )
            for id_str, emb, payload in zip(ids, embeddings, payloads)
        ]
        self.client.upsert(collection_name=collection, points=points)
        logger.info(f"Stored {len(points)} points in '{collection}'")

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        try:
            results = self.client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=filter,
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
        point_ids = [int(hash(id_str) % (2**63)) for id_str in ids]
        self.client.delete(collection_name=collection, points_selector=point_ids)
        logger.info(f"Deleted {len(ids)} from '{collection}'")

    async def create_collection(self, collection: str) -> None:
        collections = self.client.get_collections().collections
        if not any(c.name == collection for c in collections):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info(f"Created collection '{collection}'")
