"""Freshness Analyzer & Semantic Freshness Detection Engine.

Classifies user requests into freshness levels:
- LIVE: Immediate live data (Bitcoin price right now, current weather, stock price).
- CURRENT: Up-to-date facts (best mouse under 500, PCCE Goa courses, latest AI models, current CEO).
- RECENT: Recent news/developments (tech news today, recent AI developments).
- HISTORICAL: Past events/history (PCCE history in 2020).
- STATIC: Fundamental concepts (What is TCP, how does a mouse sensor work).
- MIXED: Combination of static and current.
"""

from enum import Enum
import re
from typing import Dict, Any, List


class FreshnessLevel(str, Enum):
    LIVE = "LIVE"
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    HISTORICAL = "HISTORICAL"
    STATIC = "STATIC"
    MIXED = "MIXED"


class FreshnessAnalyzer:
    """Semantic Freshness Detector for Phase 15 Automatic Search Triggers."""

    LIVE_KEYWORDS = [
        "right now", "live", "bitcoin price", "crypto price", "stock price",
        "weather", "weather in", "temperature", "score", "market rate", "stock",
        "market", "company status", "usd to inr"
    ]

    CURRENT_KEYWORDS = [
        "latest", "today", "current", "recent", "price", "available", "availability",
        "news", "release", "released", "version", "security advisory", "github activity",
        "github", "what's new", "whats new", "changes", "changelog", "best",
        "under ₹", "under rs", "under 500", "under 1000", "under 60000", "now",
        "2026", "2025", "price of", "buy", "purchase", "admission", "courses",
        "fees", "placements", "ceo", "president", "cloudflare", "models", "gpu",
        "nvidia", "pcce", "college", "university"
    ]

    RECENT_KEYWORDS = [
        "news", "recent", "trending", "update", "release", "released",
        "this week", "this month", "changes", "adk changes"
    ]

    HISTORICAL_KEYWORDS = [
        "history", "in 2020", "in 2019", "in 2018", "in 2015", "in 2000",
        "origin", "founded in", "past", "historical"
    ]

    STATIC_PATTERNS = [
        r"^what is (a|an)?\s*(tcp|http|udp|ip|dns|html|css|json|sql|python|react|linked list|stack|queue|tree|graph|recursion|binary search|binary search algorithm|sorting|algorithm|array|hash table|pointer|matrix|class|function|oop|polymorphism|inheritance|encapsulation)( in (oop|python|java|c\+\+|cs))?[\.\?\!]?$",
        r"^how (does|do) (a|an)?\s*(mouse|keyboard|sensor|cpu|gpu|engine|compiler|linked list|stack|queue|array|recursion)\s*work[\.\?\!]?$",
        r"^explain (react hooks|hooks in react|react hook|gravity|relativity|photosynthesis|binary search|binary search algorithm|linked list|recursion|dynamic programming|oop|polymorphism|inheritance|encapsulation)[\.\?\!]?$",
        r"^(calculate|compute|solve)\s+[\d\+\-\*\/\^\(\)\.\s]+$",
        r"\b(analyze|plot|chart|compute|dataset|summary statistics|csv)\b",
    ]

    def analyze(self, query: str) -> Dict[str, Any]:
        text = query.lower().strip()

        has_live_keyword = any(kw in text for kw in self.LIVE_KEYWORDS)
        has_current_keyword = any(kw in text for kw in self.CURRENT_KEYWORDS)
        has_recent_keyword = any(kw in text for kw in self.RECENT_KEYWORDS)

        # 1. If query contains an explicit live or freshness trigger, fresh research is mandatory
        if has_live_keyword:
            return {
                "level": FreshnessLevel.LIVE,
                "research_required": True,
                "reason": "Requires real-time streaming or live API financial/weather/market data.",
            }

        if has_current_keyword or re.search(r'\b(buy|mouse|laptop|phone|under|price|course|fee|admission)\b', text):
            return {
                "level": FreshnessLevel.CURRENT,
                "research_required": True,
                "reason": "Requires current real-time external data for products, versions, releases, or specifications.",
            }

        if has_recent_keyword:
            return {
                "level": FreshnessLevel.RECENT,
                "research_required": True,
                "reason": "Requires recent web research for news, updates, and announcements.",
            }

        # 2. Static / timeless pattern check (bypasses web when no freshness trigger exists)
        for pat in self.STATIC_PATTERNS:
            if re.search(pat, text):
                return {
                    "level": FreshnessLevel.STATIC,
                    "research_required": False,
                    "reason": "Fundamental educational concept without real-time state requirement.",
                }

        # 3. Historical query check
        if any(kw in text for kw in self.HISTORICAL_KEYWORDS):
            return {
                "level": FreshnessLevel.HISTORICAL,
                "research_required": False,
                "reason": "Query focuses on past historical events.",
            }

        # Default fallback
        return {
            "level": FreshnessLevel.CURRENT,
            "research_required": True,
            "reason": "Default safety assumption requiring live source grounding.",
        }


freshness_analyzer = FreshnessAnalyzer()
