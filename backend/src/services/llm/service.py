"""LLM service - delegates to the configured provider."""

from collections.abc import AsyncGenerator
from typing import Optional
from src.config import settings
from src.utils.logger import logger
from src.services.llm.factory import get_llm_provider


class LLMService:
    def __init__(self):
        self._provider = None

    async def _get_provider(self):
        if self._provider is None:
            self._provider = get_llm_provider()
            logger.info(f"LLM service ready — primary provider: Groq (fastest), auto-rotation active")
        return self._provider

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        provider = await self._get_provider()
        return await provider.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        provider = await self._get_provider()
        async for chunk in provider.generate_stream(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ):
            yield chunk

    async def generate_with_citations(
        self,
        prompt: str,
        context: list[dict],
        system_instruction: Optional[str] = None,
    ) -> tuple[str, list[dict]]:
        provider = await self._get_provider()
        return await provider.generate_with_citations(
            prompt=prompt,
            context=context,
            system_instruction=system_instruction,
        )

    async def generate_multimodal(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        max_output_tokens: int = 4096,
    ) -> str:
        provider = await self._get_provider()
        return await provider.generate_multimodal(
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            max_output_tokens=max_output_tokens,
        )


llm_service = LLMService()
