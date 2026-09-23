"""OpenAI-compatible LLM provider (used by OpenRouter, Groq, etc.)."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Optional

from src.services.llm.base import BaseLLMProvider
from src.utils.logger import logger


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, name: str, api_key: str, model: str, base_url: str, timeout_seconds: int = 30):
        self.name = name
        self.keys = [k.strip() for k in api_key.split(",") if k.strip()]
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.clients = []
        self._current_idx = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    def _init_clients(self):
        if self._initialized:
            return
        if not self.keys:
            raise ValueError(f"{self.name} API key not configured")

        from openai import AsyncOpenAI

        for key in self.keys:
            try:
                client = AsyncOpenAI(
                    api_key=key,
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                )
                self.clients.append((key, client))
            except Exception as e:
                logger.error(f"Failed to initialize {self.name} client: {e}")

        if not self.clients:
            raise ValueError(f"No valid API keys could be initialized for {self.name}")

        logger.info(f"{self.name} provider initialized with {len(self.clients)} key(s) and model: {self.model}")
        self._initialized = True

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        self._init_clients()
        attempts = len(self.clients)

        async with self._lock:
            start_idx = self._current_idx

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            key, client = self.clients[idx]
            masked_key = f"...{key[-4:]}" if len(key) > 4 else "..."

            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                )

                # A successful response makes this key the preferred starting
                # point for the next request from the same provider.
                async with self._lock:
                    self._current_idx = idx

                return response.choices[0].message.content or ""
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower() or "rate" in err_msg.lower() or "limit" in err_msg.lower():
                    logger.warning(
                        f"{self.name} API key rotation: Key {masked_key} rate limited/exhausted. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )
                else:
                    logger.warning(
                        f"{self.name} API key rotation: Call failed with key {masked_key}. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )

        logger.error(f"All {attempts} API keys for {self.name} failed.")
        if last_error is None:
            raise RuntimeError(f"{self.name} has no usable API clients")
        raise last_error

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream one coherent generation without replaying partial output.

        A second key is safe only before anything has reached the caller. Once
        a chunk has been yielded, retrying the prompt with another key/model can
        concatenate two independent generations in one assistant message.
        """
        self._init_clients()
        attempts = len(self.clients)

        async with self._lock:
            start_idx = self._current_idx

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            key, client = self.clients[idx]
            masked_key = f"...{key[-4:]}" if len(key) > 4 else "..."
            emitted = False

            try:
                stream = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        emitted = True
                        yield delta.content

                # Only mark the key as preferred after the stream completes.
                # A stream that dies halfway through is not a healthy success.
                async with self._lock:
                    self._current_idx = idx
                return

            except Exception as e:
                last_error = e
                err_msg = str(e)

                # Never replay a prompt once any text is visible to the caller.
                # Let the outer streaming layer surface/handle the interruption
                # rather than corrupting one message with a second generation.
                if emitted:
                    logger.warning(
                        f"{self.name} stream interrupted after emitting output with key {masked_key}; "
                        "not retrying another key to avoid duplicate/mixed text."
                    )
                    raise

                if "429" in err_msg or "quota" in err_msg.lower() or "rate" in err_msg.lower() or "limit" in err_msg.lower():
                    logger.warning(
                        f"{self.name} API key rotation: Key {masked_key} rate limited/exhausted before output. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )
                else:
                    logger.warning(
                        f"{self.name} API key rotation: Call failed before output with key {masked_key}. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )

        logger.error(f"All {attempts} API keys for {self.name} failed for streaming.")
        if last_error is None:
            raise RuntimeError(f"{self.name} has no usable API clients")
        raise last_error
