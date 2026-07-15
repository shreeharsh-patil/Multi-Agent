from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Optional


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        ...

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM.

        Default implementation yields the full non-streaming response as
        a single chunk so that providers without native streaming still work.
        """
        text = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        yield text

    async def generate_with_citations(
        self,
        prompt: str,
        context: list[dict],
        system_instruction: Optional[str] = None,
    ) -> tuple[str, list[dict]]:
        context_block = "\n\n".join(
            f"[Source: {c.get('file_name', 'Unknown')}"
            + (f", Page {c.get('page_number')}" if c.get('page_number') else "")
            + (f", Section: {c.get('section')}" if c.get('section') else "")
            + f"]\n{c.get('content', '')}"
            for c in context
        )

        full_prompt = f"""Context from documents:
{context_block}

User query: {prompt}

Answer based on the context above. Include citations using [Source: filename, Page X] format."""

        response = await self.generate(
            prompt=full_prompt,
            system_instruction=system_instruction or "You are a helpful AI assistant. Always cite your sources.",
        )

        citations = [
            {
                "file_name": c.get("file_name", "Unknown"),
                "page_number": c.get("page_number"),
                "section": c.get("section"),
                "text": c.get("content", "")[:200],
            }
            for c in context
        ]

        return response, citations

    async def generate_multimodal(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        max_output_tokens: int = 4096,
    ) -> str:
        raise NotImplementedError("The configured LLM provider does not support image inputs")
