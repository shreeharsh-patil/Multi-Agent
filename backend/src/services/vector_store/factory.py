from src.services.vector_store.base import VectorStore
from src.services.vector_store.chroma import ChromaVectorStore
from src.services.vector_store.qdrant import QdrantVectorStore
from src.config import settings
from src.utils.logger import logger


def get_vector_store() -> VectorStore:
    provider = settings.vector_db_provider
    logger.info(f"Initializing vector store: {provider}")

    if provider == "qdrant":
        return QdrantVectorStore()
    return ChromaVectorStore()


vector_store: VectorStore = get_vector_store()
