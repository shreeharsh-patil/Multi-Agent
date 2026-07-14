"""OpenAI-compatible LLM provider (used by OpenRouter, Groq, etc.)."""

from typing import Optional
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, name: str, api_key: str, model: str, base_url: str):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"{self.name} provider initialized with model: {self.model}")
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
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"{self.name} generation failed", extra={"error": str(e)})
            raise
