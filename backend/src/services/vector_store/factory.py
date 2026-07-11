from typing import Optional
from src.services.vector_store.base import VectorStore
from src.config import settings
from src.utils.logger import logger


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        provider = settings.vector_db_provider
        logger.info(f"Initializing vector store: {provider}")

        if provider == "qdrant":
            from src.services.vector_store.qdrant import QdrantVectorStore
            _vector_store = QdrantVectorStore()
        else:
            from src.services.vector_store.chroma import ChromaVectorStore
            _vector_store = ChromaVectorStore()

    return _vector_store
