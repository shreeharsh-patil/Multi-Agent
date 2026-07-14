"""OpenAI-compatible LLM provider (used by OpenRouter, Groq, etc.)."""

import asyncio
from typing import Optional
from src.utils.logger import logger
from src.services.llm.base import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, name: str, api_key: str, model: str, base_url: str):
        self.name = name
        self.keys = [k.strip() for k in api_key.split(",") if k.strip()]
        self.model = model
        self.base_url = base_url
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
                
                # Update the index to the successful key for future calls
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
        raise last_error

