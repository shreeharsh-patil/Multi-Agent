import asyncio
import os
from typing import Callable, Any
from google import genai
from google.genai import types
from src.config import settings
from src.utils.logger import logger

class GeminiClientRotator:
    def __init__(self):
        # Split the keys by comma and clean them
        raw_keys = settings.gemini_api_key or ""
        self.keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.clients = []
        self._current_idx = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    def _init_clients(self):
        if self._initialized:
            return
        if not self.keys:
            raise ValueError("GEMINI_API_KEY is not configured in .env.")
        
        for key in self.keys:
            try:
                # The SDK gives GOOGLE_API_KEY precedence over GEMINI_API_KEY.
                # This service owns Gemini credentials, so prevent a stale
                # process/host variable from silently overriding this key.
                os.environ.pop("GOOGLE_API_KEY", None)
                os.environ["GEMINI_API_KEY"] = key
                client = genai.Client(
                    api_key=key,
                    http_options=types.HttpOptions(api_version='v1')
                )
                self.clients.append((key, client))
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client for a key: {e}")
        
        if not self.clients:
            raise ValueError("No valid GEMINI_API_KEYs could be initialized.")
        
        logger.info(f"Gemini client rotator initialized with {len(self.clients)} key(s).")
        self._initialized = True

    async def execute_with_retry(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a client operation, rotating keys if a rate limit or API error occurs.

        The callable `func` must accept the client as its first argument, e.g.:
        `func(client, *args, **kwargs)`
        """
        self._init_clients()
        attempts = len(self.clients)
        
        async with self._lock:
            start_idx = self._current_idx

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            key, client = self.clients[idx]
            
            # Mask the key for logging
            masked_key = f"...{key[-4:]}" if len(key) > 4 else "..."
            
            try:
                # Execute the SDK function
                result = await asyncio.to_thread(func, client, *args, **kwargs)
                
                # Update the index to the successful key for future calls
                async with self._lock:
                    self._current_idx = idx
                
                return result
            except Exception as e:
                last_error = e
                err_msg = str(e)
                # Check for rate limit (429), quota exceeded, or ResourceExhausted errors
                if "429" in err_msg or "quota" in err_msg.lower() or "resource" in err_msg.lower() or "exhausted" in err_msg.lower():
                    logger.warning(
                        f"Gemini API key rotation: Key {masked_key} rate limited/exhausted. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )
                else:
                    logger.warning(
                        f"Gemini API key rotation: Call failed with key {masked_key}. "
                        f"Error: {err_msg}. Retrying with next key..."
                    )
        
        logger.error(f"All {attempts} Gemini API keys failed.")
        raise last_error

gemini_rotator = GeminiClientRotator()
