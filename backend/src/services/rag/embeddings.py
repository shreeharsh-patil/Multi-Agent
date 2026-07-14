import asyncio
from src.config import settings
from src.utils.logger import logger
from src.services.llm.key_rotator import gemini_rotator


class EmbeddingService:
    def __init__(self):
        self.model = settings.embedding_model
        logger.info(f"Embedding service initialized with model: {self.model} (supporting key rotation)")

    async def embed_text(self, text: str) -> list[float]:
        try:
            def get_embeddings(client):
                return client.models.embed_content(
                    model=self.model,
                    contents=text,
                )

            result = await gemini_rotator.execute_with_retry(get_embeddings)
            return result.embeddings[0].values if result.embeddings else []
        except Exception as e:
            logger.error(f"Embedding generation failed after trying all keys: {e}")
            return []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        tasks = [self.embed_text(text) for text in texts]
        return await asyncio.gather(*tasks)


embedding_service = EmbeddingService()

