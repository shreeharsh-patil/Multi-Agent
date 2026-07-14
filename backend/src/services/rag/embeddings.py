import asyncio
from src.config import settings
from src.utils.logger import logger


class EmbeddingService:
    def __init__(self):
        self._client = None
        self._lock = asyncio.Lock()
        self.model = settings.embedding_model

    async def _get_client(self):
        if self._client is None:
            async with self._lock:
                if self._client is not None:
                    return self._client
                if not settings.gemini_api_key:
                    raise ValueError(
                        "GEMINI_API_KEY not configured. "
                        "Set it in .env or environment variables."
                    )
                from google import genai
                self._client = await asyncio.to_thread(
                    lambda: genai.Client(api_key=settings.gemini_api_key)
                )
                logger.info(f"Embedding service initialized with model: {self.model}")
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        client = await self._get_client()
        result = await asyncio.to_thread(
            client.models.embed_content,
            model=self.model,
            contents=text,
        )
        return result.embeddings[0].values if result.embeddings else []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        tasks = [self.embed_text(text) for text in texts]
        return await asyncio.gather(*tasks)


embedding_service = EmbeddingService()
