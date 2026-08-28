"""Typed exceptions for InternetSDK operations."""

from typing import Optional


class InternetError(Exception):
    """Base exception for all InternetSDK errors."""

    def __init__(self, message: str, details: Optional[dict[str, object]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SearchProviderError(InternetError):
    """Raised when an upstream search provider fails or becomes unavailable."""
    pass


class SourceVerificationError(InternetError):
    """Raised when evidence verification fails or finds conflicting data."""
    pass


class RateLimitError(InternetError):
    """Raised when an external search or scraping provider rate limits requests."""
    pass


class DocumentExtractionError(InternetError):
    """Raised when scraping, downloading, or reading a URL document fails."""
    pass


class InvalidResearchRequestError(InternetError):
    """Raised when request parameters violate boundaries or are malformed."""
    pass


class ResearchTimeoutError(InternetError):
    """Raised when research execution exceeds the configured timeout budget."""
    pass
