"""Weather & News Agent API routes — real-time data fetching endpoints."""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

from src.agents.weather_news.agent import (
    _fetch_weather_json, _fetch_weather_brief, _fetch_news,
    _parse_weather, _format_news, NEWS_FEEDS,
)
from src.utils.logger import logger

router = APIRouter(prefix="/api/weather-news", tags=["Weather & News"])


# ── Request schemas ────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str
    city: Optional[str] = "London"
    news_category: Optional[str] = "World"
    user_id: Optional[str] = "default"


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/weather")
async def get_weather(
    city: str = Query("London", description="City name for weather lookup"),
):
    """Fetch current weather + 3-day forecast for a city from wttr.in."""
    data = await _fetch_weather_json(city)
    if data:
        markdown = _parse_weather(data, city)
        # Extract structured current conditions for the UI cards
        cur = data["current_condition"][0]
        nearest = data.get("nearest_area", [{}])[0]
        area = nearest.get("areaName", [{}])[0].get("value", city)
        country = nearest.get("country", [{}])[0].get("value", "")

        forecast = []
        for day in data.get("weather", [])[:3]:
            hourly = day.get("hourly", [])
            desc = hourly[4]["weatherDesc"][0]["value"] if len(hourly) > 4 else "N/A"
            chance_rain = hourly[4].get("chanceofrain", "0") if len(hourly) > 4 else "0"
            forecast.append({
                "date": day.get("date", ""),
                "maxTempC": int(day.get("maxtempC", 0)),
                "minTempC": int(day.get("mintempC", 0)),
                "description": desc,
                "chanceOfRain": int(chance_rain),
                "hourly": [
                    {
                        "time": h.get("time", ""),
                        "tempC": int(h.get("tempC", 0)),
                        "desc": h["weatherDesc"][0]["value"] if h.get("weatherDesc") else "",
                        "chanceOfRain": int(h.get("chanceofrain", 0)),
                    }
                    for h in hourly[::2][:4]
                ],
            })

        return {
            "success": True,
            "city": area,
            "country": country,
            "markdown": markdown,
            "current": {
                "description": cur["weatherDesc"][0]["value"],
                "tempC": int(cur["temp_C"]),
                "tempF": int(cur["temp_F"]),
                "feelsLikeC": int(cur["FeelsLikeC"]),
                "humidity": int(cur["humidity"]),
                "windKmph": int(cur["windspeedKmph"]),
                "windDir": cur["winddir16Point"],
                "visibilityKm": int(cur["visibility"]),
                "uvIndex": cur.get("uvIndex", "N/A"),
                "pressureHpa": cur.get("pressure", "N/A"),
                "weatherCode": int(cur.get("weatherCode", 116)),
            },
            "forecast": forecast,
        }
    else:
        brief = await _fetch_weather_brief(city)
        return {"success": True, "city": city, "country": "", "markdown": brief, "current": None, "forecast": []}


@router.get("/news")
async def get_news(
    category: str = Query("World", description="News category"),
    limit: int = Query(10, ge=1, le=20),
):
    """Fetch latest news headlines from RSS feeds for a given category."""
    cat = category if category in NEWS_FEEDS else "World"
    articles = (await _fetch_news(cat)) or []
    return {
        "success": True,
        "category": cat,
        "categories": list(NEWS_FEEDS.keys()),
        "articles": articles[:limit],
        "markdown": _format_news(articles[:limit], cat),
    }


@router.get("/categories")
async def get_categories():
    """Return available news categories."""
    return {"categories": list(NEWS_FEEDS.keys())}


@router.post("/ask")
async def ask_agent(request: Request, body: AskRequest):
    """Natural-language query — fetches real-time data + LLM enrichment."""
    from src.agents.registry import AgentRegistry
    agent = AgentRegistry.get_agent("weather_news")
    if not agent:
        raise HTTPException(status_code=503, detail="WeatherNewsAgent not available")
    ctx = {
        "city": body.city or "London",
        "news_category": body.news_category or "World",
        "user_id": body.user_id,
    }
    try:
        result = await agent.execute(body.query, ctx)
        return {"success": result.success, "output": result.output, "metadata": result.metadata}
    except Exception as exc:
        logger.error("WeatherNewsAgent error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
