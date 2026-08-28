"""Configuration for InternetSDK research, scraping, and verification subsystems."""

from dataclasses import dataclass
from src.config import settings

INTERNET_DEFAULT_MAX_SOURCES: int = settings.internet_default_max_sources
INTERNET_MAX_SOURCES: int = settings.internet_max_sources
INTERNET_REQUEST_TIMEOUT: float = settings.internet_request_timeout
INTERNET_RESEARCH_MAX_ITERATIONS: int = settings.internet_research_max_iterations
INTERNET_MAX_CONCURRENCY: int = settings.internet_max_concurrency


@dataclass(frozen=True)
class InternetConfig:
    """Immutable per-instance configuration for InternetSDK."""

    default_max_sources: int = INTERNET_DEFAULT_MAX_SOURCES
    max_sources: int = INTERNET_MAX_SOURCES
    request_timeout: float = INTERNET_REQUEST_TIMEOUT
    research_max_iterations: int = INTERNET_RESEARCH_MAX_ITERATIONS
    max_concurrency: int = INTERNET_MAX_CONCURRENCY
    enable_cache: bool = True
    cache_ttl_seconds: int = 1800
