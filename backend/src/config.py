import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    app_name: str = "Multi-Agent AI Platform"
    app_version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    mongodb_uri: str = "mongodb://localhost:27017/multi-agent-platform"
    mongodb_db_name: str = "multi-agent-platform"

    vector_db_provider: Literal["chroma", "qdrant"] = "chroma"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    chroma_persist_dir: str = "./chroma_data"

    llm_provider: str = "aiand"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-004"

    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    nararouter_api_key: str = ""
    nararouter_model: str = "auto/bynara"
    nararouter_base_url: str = "https://router.bynara.id/v1"

    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    mistral_base_url: str = "https://api.mistral.ai/v1"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    aiand_api_key: str = ""
    aiand_model: str = "qwen/qwen3.6-27b"
    aiand_base_url: str = "https://api.aiand.com/v1"

    firecrawl_api_key: str = ""
    deepgram_api_key: str = ""

    image_provider: str = "auto"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    openai_image_quality: str = "medium"
    stability_api_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_drive_credentials_path: str = ""

    secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    embedding_dimension: int = 768
    enable_multimodal_ocr: bool = True
    ocr_min_page_chars: int = 40
    allowed_origins: str = "http://localhost:3000,https://agentcampus.vercel.app"

    opendocuments_api_url: str = "http://localhost:5001"
    use_opendocuments_rag: bool = False

    log_level: str = "INFO"

    @field_validator("mongodb_uri", mode="before")
    @classmethod
    def clean_mongodb_uri(cls, value):
        """Clean copy-pasted MongoDB URI containing control chars or whitespaces."""
        if isinstance(value, str):
            import re
            # Remove all whitespace/newlines/tabs
            value = re.sub(r"\s+", "", value)
            # Remove non-printable control characters (ASCII < 32 or >= 127)
            value = "".join(ch for ch in value if 31 < ord(ch) < 127)
            value = value.strip()
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Accept common environment values without crashing startup.

        Some hosting environments set DEBUG to values such as ``release``.
        Pydantic's boolean parser rejects those strings, which previously
        prevented the entire backend from importing.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "development", "dev"}:
                return True
            if normalized in {"false", "0", "no", "off", "production", "prod", "release"}:
                return False
        return value

    model_config = {
        # Resolve both env files so startup works from either the repository
        # root or backend directory. The backend file contains service keys;
        # the root file contains shared/frontend settings.
        "env_file": (
            str(Path(__file__).resolve().parents[1] / ".env"),
            str(Path(__file__).resolve().parents[2] / ".env"),
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

if settings.gemini_api_key:
    first_key = next((k.strip() for k in settings.gemini_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["GEMINI_API_KEY"] = first_key
        os.environ["GOOGLE_API_KEY"] = first_key

if settings.openrouter_api_key:
    first_key = next((k.strip() for k in settings.openrouter_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["OPENROUTER_API_KEY"] = first_key

if settings.nararouter_api_key:
    first_key = next((k.strip() for k in settings.nararouter_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["NARAROUTER_API_KEY"] = first_key

if settings.groq_api_key:
    first_key = next((k.strip() for k in settings.groq_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["GROQ_API_KEY"] = first_key

if settings.aiand_api_key:
    first_key = next((k.strip() for k in settings.aiand_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["AIAND_API_KEY"] = first_key

if settings.firecrawl_api_key:
    first_key = next((k.strip() for k in settings.firecrawl_api_key.split(",") if k.strip()), "")
    if first_key:
        os.environ["FIRECRAWL_API_KEY"] = first_key

