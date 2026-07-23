from typing import Optional
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._collections: dict[str, list[dict]] = {}

    async def store_embeddings(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        if collection not in self._collections:
            self._collections[collection] = []
        for id_, emb, p in zip(ids, embeddings, payloads):
            self._collections[collection] = [x for x in self._collections[collection] if x["id"] != id_]
            self._collections[collection].append({
                "id": id_,
                "embedding": emb,
                "metadata": p,
                "content": p.get("content", ""),
            })

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        items = self._collections.get(collection, [])
        if filter_dict:
            filtered = []
            for item in items:
                meta = item.get("metadata", {})
                if all(meta.get(k) == v for k, v in filter_dict.items()):
                    filtered.append(item)
            items = filtered
        results = []
        for item in items:
            score = sum(a * b for a, b in zip(query_embedding, item["embedding"])) if item["embedding"] else 0.0
            results.append({
                "id": item["id"],
                "content": item["content"],
                "metadata": item["metadata"],
                "score": float(score),
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def delete(self, collection: str, ids: list[str]) -> None:
        if collection in self._collections:
            ids_set = set(ids)
            self._collections[collection] = [x for x in self._collections[collection] if x["id"] not in ids_set]

    async def create_collection(self, collection: str) -> None:
        if collection not in self._collections:
            self._collections[collection] = []


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        provider = settings.vector_db_provider
        logger.info(f"Initializing vector store: {provider}")

        try:
            if provider == "qdrant":
                from src.services.vector_store.qdrant import QdrantVectorStore
                _vector_store = QdrantVectorStore()
            else:
                from src.services.vector_store.chroma import ChromaVectorStore
                _vector_store = ChromaVectorStore()
        except Exception as e:
            logger.warning(f"Failed to initialize '{provider}' vector store ({e}). Falling back to InMemoryVectorStore.")
            _vector_store = InMemoryVectorStore()

    return _vector_store
