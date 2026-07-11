from google import genai
from src.config import settings
from src.utils.logger import logger


class EmbeddingService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.embedding_model
        logger.info(f"Embedding service initialized with model: {self.model}")

    async def embed_text(self, text: str) -> list[float]:
        result = self.client.models.embed_content(
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
