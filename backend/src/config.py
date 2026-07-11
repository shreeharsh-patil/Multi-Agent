from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    app_name: str = "Multi-Agent AI Platform"
    app_version: str = "0.1.0"
    debug: bool = True
    secret_key: str = "change-this-in-production"

    host: str = "0.0.0.0"
    port: int = 8000

    mongodb_uri: str = "mongodb://localhost:27017/multi-agent-platform"
    mongodb_db_name: str = "multi-agent-platform"

    vector_db_provider: Literal["chroma", "qdrant"] = "chroma"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    chroma_persist_dir: str = "./chroma_data"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-004"

    google_drive_credentials_path: str = ""

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
