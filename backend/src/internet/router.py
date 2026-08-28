"""Query classification and routing logic for InternetSDK."""

import re
from typing import Optional
from src.internet.models import ResearchMode, FreshnessFilter, SearchProviderType
from src.utils.logger import logger


class InternetQueryRouter:
    """Classifies user intents and routes them to optimal retrieval strategies."""

    def __init__(self):
        self._news_keywords = {
            "news", "breaking", "latest", "recent", "today", "yesterday",
            "this week", "announced", "launch", "current events", "update"
        }
        self._academic_keywords = {
            "paper", "arxiv", "doi", "peer-reviewed", "benchmark",
            "methodology", "dataset", "journal", "citation", "algorithm"
        }
        self._technical_keywords = {
            "docs", "documentation", "api", "sdk", "github", "release notes",
            "changelog", "rfc", "specification", "error code", "stack trace"
        }

    def determine_mode(self, query: str, explicit_mode: Optional[ResearchMode] = None) -> ResearchMode:
        """Determine research mode based on explicit parameter or query complexity."""
        if explicit_mode:
            return explicit_mode

        q_lower = query.lower()
        word_count = len(q_lower.split())

        if word_count <= 4 and not any(kw in q_lower for kw in self._news_keywords | self._academic_keywords):
            return ResearchMode.QUICK

        if any(kw in q_lower for kw in ["in-depth", "comprehensive", "deep research", "full breakdown", "investigate"]):
            return ResearchMode.DEEP

        return ResearchMode.STANDARD

    def determine_freshness(self, query: str, explicit_freshness: Optional[FreshnessFilter] = None) -> FreshnessFilter:
        """Infer temporal sensitivity from query phrasing."""
        if explicit_freshness and explicit_freshness != FreshnessFilter.ANYTIME:
            return explicit_freshness

        q_lower = query.lower()
        if any(kw in q_lower for kw in ["today", "right now", "breaking", "live updates", "real-time"]):
            return FreshnessFilter.REALTIME
        if any(kw in q_lower for kw in ["this week", "past 7 days", "latest"]):
            return FreshnessFilter.WEEK
        if any(kw in q_lower for kw in ["this month", "recent"]):
            return FreshnessFilter.MONTH

        return FreshnessFilter.ANYTIME

    def select_provider(self, query: str, preferred_provider: Optional[SearchProviderType] = None) -> SearchProviderType:
        """Select the most suitable underlying search provider."""
        if preferred_provider and preferred_provider != SearchProviderType.AUTO:
            return preferred_provider

        q_lower = query.lower()
        if any(kw in q_lower for kw in self._news_keywords):
            return SearchProviderType.GOOGLE_GROUNDED
        if any(kw in q_lower for kw in self._technical_keywords):
            return SearchProviderType.DUCKDUCKGO

        return SearchProviderType.AUTO
