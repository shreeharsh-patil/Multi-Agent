import asyncio
from typing import Optional
from src.config import settings
from src.utils.logger import logger


class LLMService:
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
                # genai.Client is sync — initialize once under lock
                self._client = await asyncio.to_thread(
                    lambda: genai.Client(api_key=settings.gemini_api_key)
                )
                logger.info(f"LLM service initialized with model: {self.model}")
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

            # genai.models.generate_content is sync — run in thread pool
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=[prompt],
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM generation failed", extra={"error": str(e)})
            raise

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


llm_service = LLMService()
