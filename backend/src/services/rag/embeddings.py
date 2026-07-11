from typing import Optional
from src.config import settings
from src.utils.logger import logger


class EmbeddingService:
    def __init__(self):
        self._client = None
        self.model = settings.embedding_model

    def _get_client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY not configured. "
                    "Set it in .env or environment variables."
                )
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
            logger.info(f"Embedding service initialized with model: {self.model}")
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        client = self._get_client()
        result = client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return result.embeddings[0].values if result.embeddings else []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            emb = await self.embed_text(text)
            embeddings.append(emb)
        return embeddings


embedding_service = EmbeddingService()
