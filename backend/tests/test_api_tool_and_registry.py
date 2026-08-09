import pytest
import asyncio
from src.services.api_registry import ApiRegistry
from src.tools.api_tool import ApiTool, api_tool


@pytest.mark.asyncio
async def test_api_registry_capabilities():
    """Verify registry initializes and matches capabilities correctly."""
    ApiRegistry.initialize()
    all_apis = ApiRegistry.get_all()
    assert len(all_apis) >= 5

    weather_apis = ApiRegistry.find_apis_by_capability("current_weather")
    assert len(weather_apis) >= 1
    assert weather_apis[0].id == "open-meteo"

    crypto_apis = ApiRegistry.find_apis_by_capability("crypto_price")
    assert len(crypto_apis) >= 1
    assert crypto_apis[0].id == "coingecko"


@pytest.mark.asyncio
async def test_api_tool_ssrf_security():
    """Verify SSRF protection blocks localhost, internal IPs, and unauthorized URLs."""
    tool = ApiTool()

    assert tool.is_url_safe("https://api.open-meteo.com/v1/forecast") is True
    assert tool.is_url_safe("http://localhost:8000/api/chat") is False
    assert tool.is_url_safe("http://127.0.0.1:8000/internal") is False
    assert tool.is_url_safe("http://10.0.0.1/admin") is False
    assert tool.is_url_safe("http://169.254.169.254/latest/meta-data") is False

    res = await tool.execute_api("open-meteo", "http://localhost:8000/internal")
    assert res["success"] is False
    assert "Security Policy Violation" in res["error"]


@pytest.mark.asyncio
async def test_weather_capability_execution():
    """Verify BossAgent/ApiTool handles 'What is the weather in Goa?'."""
    res = await api_tool.execute_with_fallback("current_weather", {"location": "Goa"})
    assert res["success"] is True
    assert res["api_id"] == "open-meteo"

    norm = res["normalized"]
    assert norm["type"] == "weather"
    assert norm["location"] == "Goa"
    assert "temperature" in norm
    assert norm["sourceUrl"] == "https://api.open-meteo.com"


@pytest.mark.asyncio
async def test_crypto_capability_execution():
    """Verify BossAgent/ApiTool handles 'What is Bitcoin price right now?'."""
    res = await api_tool.execute_with_fallback("crypto_price", {"asset": "bitcoin"})
    assert res["success"] is True
    assert res["api_id"] == "coingecko"

    norm = res["normalized"]
    assert norm["type"] == "crypto_price"
    assert norm["asset"] == "BITCOIN"
    assert "price_inr" in norm or "price_usd" in norm
    assert norm["sourceUrl"] == "https://api.coingecko.com"


@pytest.mark.asyncio
async def test_game_deals_capability_execution():
    """Verify BossAgent/ApiTool handles 'Find me the cheapest Steam deal for GTA V'."""
    res = await api_tool.execute_with_fallback("game_deals", {"query": "GTA V"})
    assert res["success"] is True
    assert res["api_id"] == "cheapshark"

    norm = res["normalized"]
    assert norm["type"] == "game_deals"
    assert len(norm["deals"]) >= 1
    deal = norm["deals"][0]
    assert "productUrl" in deal
    assert deal["productUrl"].startswith("http")


@pytest.mark.asyncio
async def test_ip_lookup_capability_execution():
    """Verify BossAgent/ApiTool handles 'Tell me information about IP 8.8.8.8'."""
    res = await api_tool.execute_with_fallback("ip_geolocation", {"ip": "8.8.8.8"})
    assert res["success"] is True

    norm = res["normalized"]
    assert norm["type"] == "ip_info"
    assert norm["ip"] == "8.8.8.8"
    assert "isp" in norm


@pytest.mark.asyncio
async def test_exchange_rate_capability_execution():
    """Verify BossAgent/ApiTool handles 'What's the current USD to INR exchange rate?'."""
    res = await api_tool.execute_with_fallback("exchange_rate", {"from": "USD", "to": "INR"})
    assert res["success"] is True

    norm = res["normalized"]
    assert norm["type"] == "exchange_rate"
    assert norm["target"] == "INR"
    assert norm["rate"] > 0
