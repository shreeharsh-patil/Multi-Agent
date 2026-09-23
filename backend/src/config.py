import os
import re
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import Literal


def _is_insecure_secret(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if v.lower() in {"change-this-in-production", "changeme", "secret", "secret-key"}:
        return True
    if len(v) < 16:
        return True
    return False


def split_gemini_api_keys(value: str) -> list[str]:
    """Parse normal comma-separated keys and accidentally concatenated AI Studio keys.

    Gemini AI Studio now issues Authentication Keys with an ``AQ.`` prefix;
    older Traffic Keys begin with ``AIza``.  The UI occasionally receives
    several pasted back-to-back without commas; split on each subsequent key
    prefix so the rotator can use them independently. Comma separation remains
    the preferred and unambiguous configuration format.
    """
    raw = (value or "").strip()
    if not raw:
        return []
    keys: list[str] = []
    for chunk in re.split(r"[,\s]+", raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        starts = [match.start() for match in re.finditer(r"(?:AIza|AQ\.)", chunk)]
        if len(starts) > 1:
            keys.extend(chunk[start:end].strip() for start, end in zip(starts, starts[1:] + [len(chunk)]))
        else:
            keys.append(chunk)
    return keys


class Settings(BaseSettings):
    app_name: str = "Agentic AI Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    mongodb_uri: str = "mongodb://localhost:27017/agentic"
    mongodb_db_name: str = "agentic"

    vector_db_provider: Literal["chroma", "qdrant"] = "chroma"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    chroma_persist_dir: str = "./chroma_data"

    llm_provider: str = "aiand"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"
    embedding_model: str = "text-embedding-004"
    adk_enabled: bool = True

    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_base_url: str = "https://api.openrouter.ai/api/v1"

    nararouter_api_key: str = ""
    nararouter_model: str = "auto/bynara"
    nararouter_base_url: str = "https://router.bynara.id/v1"

    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    mistral_base_url: str = "https://api.mistral.ai/v1"

    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    aiand_api_key: str = ""
    aiand_model: str = "qwen/qwen3.6-27b"
    aiand_base_url: str = "https://api.aiand.com/v1"

    kimi_api_key: str = ""
    kimi_model: str = "kimi-latest"
    kimi_base_url: str = "https://api.moonshot.cn/v1"

    firecrawl_api_key: str = ""
    # Optional Obscura CDP endpoint for managed or self-hosted browser scraping.
    obscura_cdp_url: str = ""
    obscura_timeout_seconds: int = 30
    # Complex ADK transfers and one provider failover can legitimately exceed
    # 45 seconds on a cold start. Keep the connection alive long enough for a
    # healthy secondary route to finish instead of closing a valid stream.
    chat_stream_timeout_seconds: int = 90
    adk_fast_route_timeout_seconds: int = 20
    adk_route_timeout_seconds: int = 60
    # A route is admitted into the ADK rotator only after a real, minimal
    # generation succeeds. Probes run concurrently, so this is a per-key cap.
    adk_provider_probe_timeout_seconds: int = 40
    chat_context_timeout_seconds: int = 3
    oauth_verification_timeout_seconds: int = 8
    deepgram_api_key: str = ""

    image_provider: str = "auto"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    openai_image_quality: str = "medium"
    stability_api_key: str = ""
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_drive_credentials_path: str = ""

    secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    # When False (default), generated/untrusted code is never executed directly
    # on the backend host; it only runs in remote sandboxes (Wandbox/Judge0/Piston).
    allow_local_code_execution: bool = False
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
            if normalized in {"false", "0", "no", "off", "production", "prod", "release", "warn", "warning", "info", "debug", "error"}:
                return False
        return value

    @field_validator("gemini_model", mode="before")
    @classmethod
    def migrate_retired_gemini_model(cls, value):
        """Prevent stale hosting variables from selecting retired models.

        Render still had ``GEMINI_MODEL=gemini-2.0-flash`` after that model
        was shut down. Environment variables override field defaults, so a
        newer default alone cannot repair an existing deployment.
        """
        model = str(value or "").strip()
        retired_models = {
            "gemini-1.0-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-pro",
        }
        return "gemini-3.7-flash" if model.lower() in retired_models else model

    @field_validator("openrouter_model", mode="before")
    @classmethod
    def migrate_retired_openrouter_model(cls, value):
        model = str(value or "").strip()
        retired_models = {
            "google/gemini-2.0-flash-exp:free",
            "google/gemini-2.0-flash-001",
        }
        return "nvidia/nemotron-3-ultra-550b-a55b:free" if model.lower() in retired_models else model

    @field_validator("aiand_model", mode="before")
    @classmethod
    def migrate_retired_aiand_model(cls, value):
        model = str(value or "").strip()
        retired_models = {
            "qwen/qwen-2.5-72b-instruct",
            "qwen/qwen2.5-72b-instruct",
        }
        return "qwen/qwen3.6-27b" if model.lower() in retired_models else model

    @field_validator("groq_model", mode="before")
    @classmethod
    def migrate_retired_groq_model(cls, value):
        """Keep stale Groq environment values on a currently supported chat model.

        Groq retired Qwen 3.6 on 2026-09-14. Existing hosted environment
        variables override code defaults, so migrate them at settings load time.
        GPT-OSS is also normalized to Qwen 3.8 because the ADK LiteLLM path uses
        ``reasoning_format=hidden``, which Qwen supports consistently.
        """
        model = str(value or "").strip()
        stale_models = {
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "mixtral-8x7b-32768",
            "llama3-8b-8192",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
        }
        return "qwen/qwen3.8-27b" if model.lower() in stale_models else model

    @model_validator(mode="after")
    def _reject_insecure_secret(self):
        """Refuse to start with a weak/known JWT signing key outside debug mode.

        A publicly known secret key lets any caller forge valid JWTs for any
        user (full account takeover), so we fail closed instead of silently
        running insecure. Local development can still opt in by setting DEBUG
        and supplying a strong SECRET_KEY.
        """
        if not self.debug and _is_insecure_secret(self.secret_key):
            raise ValueError(
                "REFUSING TO START: SECRET_KEY must be a strong random value of at least 16 characters "
                "outside debug mode. Set a strong SECRET_KEY (or DEBUG=true for local development)."
            )
        return self

    # ---- Agentic Boss (multi-agent orchestration) ----
    agentic_enabled: bool = True
    agentic_max_agents: int = 14
    agentic_max_waves: int = 8
    agentic_max_retries: int = 2
    agentic_max_alternates: int = 1
    agentic_max_replan_rounds: int = 2
    # Hard execution limits.  These are deliberately separate from planning
    # limits so a bad plan or a delegating agent cannot consume a request
    # indefinitely.
    max_agent_iterations: int = 3
    max_delegation_depth: int = 2
    agentic_agent_timeout_seconds: int = 45
    tool_timeout_seconds: int = 15
    agentic_think_timeout_seconds: int = 40
    agentic_include_reviewers: bool = True
    agentic_auto_evaluate: bool = True
    agentic_strong_synthesis: bool = True

    # ---- Google ADK Hierarchical Multi-Agent Architecture ----
    adk_max_specialists_per_task: int = 12
    adk_default_max_specialists: int = 12
    adk_deep_max_specialists: int = 40
    adk_massive_max_specialists: int = 120
    adk_max_concurrent_specialists: int = 8

    # ---- Internet SDK Configuration ----
    internet_default_max_sources: int = 5
    internet_max_sources: int = 20
    internet_request_timeout: float = 15.0
    internet_research_max_iterations: int = 5
    internet_max_concurrency: int = 8

    # ---- ADK Search Planning Mode Limits ----
    search_plan_quick_min_queries: int = 1
    search_plan_quick_max_queries: int = 2
    search_plan_standard_min_queries: int = 3
    search_plan_standard_max_queries: int = 5
    search_plan_deep_min_queries: int = 5
    search_plan_deep_max_queries: int = 10
    search_plan_critical_min_queries: int = 8
    search_plan_critical_max_queries: int = 15

    # ---- ADK Adaptive Research Loop (LoopAgent) Limits ----
    max_research_loop_iterations: int = 3

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
    first_key = next(iter(split_gemini_api_keys(settings.gemini_api_key)), "")
    if first_key:
        os.environ["GEMINI_API_KEY"] = first_key
        # google-genai prioritizes GOOGLE_API_KEY when both variables exist.
        # Keep only the explicitly configured Gemini key so an inherited or
        # stale Google key cannot override the selected credential.
        os.environ.pop("GOOGLE_API_KEY", None)

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
