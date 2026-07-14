import asyncio
from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self._client = None
        self._lock = asyncio.Lock()
        self.model = settings.gemini_model

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
                logger.info(f"Gemini provider initialized with model: {self.model}")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        client = await self._get_client()
        try:
            config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=[prompt],
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed", extra={"error": str(e)})
            raise
