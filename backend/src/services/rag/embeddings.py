import asyncio
from src.config import settings
from src.utils.logger import logger
from src.services.llm.key_rotator import gemini_rotator


class EmbeddingService:
    def __init__(self):
        self.model = settings.embedding_model
        # Simple in-memory cache keyed by text to avoid re-embedding
        # the same content (e.g. repeated document chunks).
        self._cache: dict[str, list[float]] = {}
        self._cache_max = 500
        logger.info(f"Embedding service initialized with model: {self.model} (supporting key rotation)")

    async def embed_text(self, text: str) -> list[float]:
        # Check in-memory cache first to avoid re-embedding the same text.
        cached = self._cache.get(text)
        if cached is not None:
            return cached

        # Try Gemini embeddings with key rotation
        try:
            def get_embeddings(client):
                return client.models.embed_content(
                    model=self.model,
                    contents=text,
                )

            result = await gemini_rotator.execute_with_retry(get_embeddings)
            if result.embeddings:
                embedding = result.embeddings[0].values or []
                # Store in cache, evict oldest entries if over capacity
                while len(self._cache) >= self._cache_max:
                    self._cache.pop(next(iter(self._cache)), None)
                self._cache[text] = embedding
                return embedding
        except Exception as e:
            logger.warning(f"Gemini embeddings failed after key rotation: {e}")

        # Return zero vector as last resort — document chunking/retrieval
        # will work with degraded quality but won't crash.
        logger.warning(
            f"Embedding generation failed. Returning zero vector (degraded search quality). "
            f"Ensure GEMINI_API_KEY is configured or add an alternative embedding provider."
        )
        return [0.0] * settings.embedding_dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        tasks = [self.embed_text(text) for text in texts]
        return await asyncio.gather(*tasks)


embedding_service = EmbeddingService()

