import asyncio
from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider
from src.services.llm.key_rotator import gemini_rotator


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self.model = settings.gemini_model
        logger.info(f"Gemini provider initialized with model: {self.model} (supporting key rotation)")

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        try:
            config = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction

            # Define the function that calls the SDK
            def generate_content(client):
                return client.models.generate_content(
                    model=self.model,
                    contents=[prompt],
                    config=config,
                )

            response = await gemini_rotator.execute_with_retry(generate_content)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed after trying all keys", extra={"error": str(e)})
            raise

