from typing import Optional
import chromadb
from chromadb.config import Settings
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


class ChromaVectorStore(VectorStore):
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at {settings.chroma_persist_dir}")

    async def store_embeddings(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        collection_obj = self.client.get_or_create_collection(collection)
        metadatas = []
        documents = []
        for p in payloads:
            metadatas.append({k: str(v) if isinstance(v, (dict, list)) else v for k, v in p.items() if k != "content"})
            documents.append(p.get("content", ""))

        collection_obj.add(
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
        filter: Optional[dict] = None,
    ) -> list[dict]:
        try:
            collection_obj = self.client.get_collection(collection)
            results = collection_obj.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter,
            )
            hits = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    hits.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": results["distances"][0][i] if results["distances"] else 0,
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
            collection_obj = self.client.get_collection(collection)
            collection_obj.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} from collection '{collection}'")
        except Exception as e:
            logger.warning(f"Delete failed: {e}")

    async def create_collection(self, collection: str) -> None:
        self.client.get_or_create_collection(collection)
        logger.info(f"Ensured collection '{collection}' exists")
