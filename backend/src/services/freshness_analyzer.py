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
    """Semantic Freshness Detector."""

    LIVE_KEYWORDS = [
        "right now", "live", "bitcoin price", "crypto price", "stock price",
        "weather in", "temperature", "score", "market rate", "usd to inr"
    ]

    CURRENT_KEYWORDS = [
        "latest", "current", "best", "under ₹", "under rs", "under 500", "under 1000",
        "under 60000", "today", "now", "2026", "2025", "price of", "buy", "purchase",
        "admission", "courses", "fees", "placements", "ceo", "president", "version",
        "cloudflare", "models", "gpu", "nvidia", "pcce", "college", "university"
    ]

    RECENT_KEYWORDS = [
        "news", "recent", "trending", "update", "release", "this week", "this month"
    ]

    HISTORICAL_KEYWORDS = [
        "history", "in 2020", "in 2019", "in 2018", "in 2015", "in 2000",
        "origin", "founded in", "past", "historical"
    ]

    STATIC_PATTERNS = [
        r"^what is (tcp|http|udp|ip|dns|html|css|json|sql|python|react)\??$",
        r"^how does (a|an)?\s*(mouse|keyboard|sensor|cpu|gpu|engine|compiler)\s*work\??$",
        r"^explain (gravity|relativity|photosynthesis|binary search)\??$",
    ]

    def analyze(self, query: str) -> Dict[str, Any]:
        text = query.lower().strip()

        # 1. Static pattern check
        for pat in self.STATIC_PATTERNS:
            if re.search(pat, text):
                return {
                    "level": FreshnessLevel.STATIC,
                    "research_required": False,
                    "reason": "Fundamental educational concept without real-time state requirement.",
                }

        # 2. Live requirement check
        if any(kw in text for kw in self.LIVE_KEYWORDS):
            return {
                "level": FreshnessLevel.LIVE,
                "research_required": True,
                "reason": "Requires real-time streaming or live API financial/weather data.",
            }

        # 3. Historical query check
        if any(kw in text for kw in self.HISTORICAL_KEYWORDS) and not any(kw in text for kw in self.CURRENT_KEYWORDS):
            return {
                "level": FreshnessLevel.HISTORICAL,
                "research_required": False,
                "reason": "Query focuses on past historical events.",
            }

        # 4. Current facts / Shopping / Institutions check
        if any(kw in text for kw in self.CURRENT_KEYWORDS) or re.search(r'\b(buy|mouse|laptop|phone|under|price|course|fee|admission)\b', text):
            return {
                "level": FreshnessLevel.CURRENT,
                "research_required": True,
                "reason": "Requires current real-time external data for products, institutions, or live versions.",
            }

        # 5. Recent developments check
        if any(kw in text for kw in self.RECENT_KEYWORDS):
            return {
                "level": FreshnessLevel.RECENT,
                "research_required": True,
                "reason": "Requires recent web research for news and announcements.",
            }

        # Default fallback
        return {
            "level": FreshnessLevel.CURRENT,
            "research_required": True,
            "reason": "Default safety assumption requiring live source grounding.",
        }


freshness_analyzer = FreshnessAnalyzer()
