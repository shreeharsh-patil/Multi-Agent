"""Internal API Registry Infrastructure.

Maintains metadata for registered public APIs, capability matching,
reliability scores, authentication parameters, and health configuration.
Used internally by BossAgent and API Tool for dynamic capability-based selection.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.utils.logger import logger


@dataclass
class ApiMetadata:
    id: str
    name: str
    description: str
    category: str
    baseUrl: str
    sampleEndpoint: str
    capabilities: List[str]
    authentication: str = "none"  # "none", "apiKey", "OAuth"
    methods: List[str] = field(default_factory=lambda: ["GET"])
    rateLimits: str = "unlimited"
    reliability: float = 0.95
    enabled: bool = True


class ApiRegistry:
    """Internal registry of external APIs accessible to BossAgent."""

    _apis: Dict[str, ApiMetadata] = {}

    @classmethod
    def initialize(cls):
        if cls._apis:
            return

        apis = [
            ApiMetadata(
                id="open-meteo",
                name="Open-Meteo Weather API",
                description="Free weather forecast API for current conditions, temperature, humidity, and forecasts.",
                category="Environment & Weather",
                baseUrl="https://api.open-meteo.com",
                sampleEndpoint="https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
                capabilities=["current_weather", "weather", "weather_forecast", "temperature", "climate"],
                authentication="none",
                reliability=0.98,
            ),
            ApiMetadata(
                id="coingecko",
                name="CoinGecko Crypto API",
                description="Live cryptocurrency prices, 24h changes, market cap, and volume in INR and USD.",
                category="Blockchain & Crypto",
                baseUrl="https://api.coingecko.com",
                sampleEndpoint="https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=inr,usd&include_24hr_change=true",
                capabilities=["crypto_price", "bitcoin_price", "cryptocurrency", "token_price", "market_price"],
                authentication="none",
                reliability=0.95,
            ),
            ApiMetadata(
                id="cheapshark",
                name="CheapShark Game Deals API",
                description="Search PC game deals, Steam discounts, prices, savings, and seller links.",
                category="Entertainment & Games",
                baseUrl="https://www.cheapshark.com",
                sampleEndpoint="https://www.cheapshark.com/api/1.0/deals?title={title}&storeID=1",
                capabilities=["game_deals", "game_price", "steam_deal", "shopping_game", "discount_finder"],
                authentication="none",
                reliability=0.96,
            ),
            ApiMetadata(
                id="ipify-geo",
                name="IPify & IP Geolocation API",
                description="IP address lookup, geolocation, ISP provider, and network details.",
                category="Geocoding & Location",
                baseUrl="https://api.ipify.org",
                sampleEndpoint="https://api.ipify.org?format=json",
                capabilities=["ip_geolocation", "ip_lookup", "ip_info", "network_ip"],
                authentication="none",
                reliability=0.99,
            ),
            ApiMetadata(
                id="frankfurter",
                name="Frankfurter Exchange Rates API",
                description="Foreign exchange conversion rates published by ECB.",
                category="Business & Finance",
                baseUrl="https://api.frankfurter.app",
                sampleEndpoint="https://api.frankfurter.app/latest?from={from_curr}&to={to_curr}",
                capabilities=["exchange_rate", "currency_conversion", "forex", "usd_to_inr"],
                authentication="none",
                reliability=0.97,
            ),
            ApiMetadata(
                id="adviceslip",
                name="Advice Slip API",
                description="Random daily life advice and quotes.",
                category="News & Media",
                baseUrl="https://api.adviceslip.com",
                sampleEndpoint="https://api.adviceslip.com/advice",
                capabilities=["quotes", "advice", "inspiration"],
                authentication="none",
                reliability=0.95,
            ),
            ApiMetadata(
                id="agify",
                name="Agify Name Age Predictor API",
                description="Predict estimated age from first names.",
                category="Development & Tools",
                baseUrl="https://api.agify.io",
                sampleEndpoint="https://api.agify.io?name={name}",
                capabilities=["age_prediction", "demographics"],
                authentication="none",
                reliability=0.94,
            ),
        ]

        for api_item in apis:
            cls._apis[api_item.id] = api_item

    @classmethod
    def get_all(cls) -> List[ApiMetadata]:
        cls.initialize()
        return [api for api in cls._apis.values() if api.enabled]

    @classmethod
    def get_by_id(cls, api_id: str) -> Optional[ApiMetadata]:
        cls.initialize()
        return cls._apis.get(api_id)

    @classmethod
    def find_apis_by_capability(cls, capability: str) -> List[ApiMetadata]:
        cls.initialize()
        cap_clean = capability.lower().replace("-", "_").strip()
        candidates = []
        for api in cls._apis.values():
            if not api.enabled:
                continue
            for cap in api.capabilities:
                if cap_clean in cap or cap in cap_clean:
                    candidates.append(api)
                    break
        candidates.sort(key=lambda a: a.reliability, reverse=True)
        return candidates
