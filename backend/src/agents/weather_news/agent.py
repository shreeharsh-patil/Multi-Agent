"""Weather & News Agent — fetches real-time data from wttr.in and RSS feeds,
then uses the LLM to enrich and narrate the information.
No API keys are required for weather or news fetching.
"""

import asyncio
from defusedxml import ElementTree as SafeET
from typing import Optional
import httpx

from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger

# ── Constants ──────────────────────────────────────────────────────────────

WEATHER_URL = "https://wttr.in/{city}?format=j1"
WTTR_BRIEF_URL = "https://wttr.in/{city}?format=3"   # one-liner fallback

NEWS_FEEDS: dict[str, list[str]] = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "Technology": [
        "https://techcrunch.com/feed/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ],
    "Science": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "Health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
    ],
    "Sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
    ],
    "AI/Tech": [
        "https://hnrss.org/frontpage",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
}
DEFAULT_CATEGORY = "World"
MAX_ARTICLES = 10
HTTP_TIMEOUT = 3.5

WMO_WEATHER_CODES = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤",
    2: "Partly cloudy ⛅",
    3: "Overcast ☁️",
    45: "Fog 🌫",
    48: "Depositing rime fog 🌫",
    51: "Light drizzle 🌧",
    53: "Moderate drizzle 🌧",
    55: "Dense drizzle 🌧",
    61: "Slight rain 🌧",
    63: "Moderate rain 🌧",
    65: "Heavy rain 🌧",
    71: "Slight snow ❄️",
    73: "Moderate snow ❄️",
    75: "Heavy snow ❄️",
    80: "Slight rain showers 🌦",
    81: "Moderate rain showers 🌦",
    82: "Violent rain showers ⛈",
    95: "Thunderstorm 🌩",
    96: "Thunderstorm with slight hail ⛈",
    99: "Thunderstorm with heavy hail ⛈",
}


async def _fetch_open_meteo_weather(city: str) -> Optional[str]:
    """Fetch live weather from Open-Meteo (100% Free, zero key, ultra-fast sub-second response)."""
    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            geo_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            if geo_resp.status_code != 200:
                return None
            geo_data = geo_resp.json()
            results = geo_data.get("results", [])
            if not results:
                return None

            loc = results[0]
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            location_name = f"{loc.get('name', city)}, {loc.get('country', '')}".strip(", ")

            w_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": "true",
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                },
            )
            if w_resp.status_code != 200:
                return None
            w_data = w_resp.json()
            cur = w_data.get("current_weather", {})
            temp_c = cur.get("temperature", "N/A")
            wind = cur.get("windspeed", "N/A")
            code = cur.get("weathercode", 0)
            condition = WMO_WEATHER_CODES.get(code, "Clear")

            daily = w_data.get("daily", {})
            dates = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])

            forecast_lines = []
            for i in range(min(3, len(dates))):
                d_code = codes[i] if i < len(codes) else 0
                d_cond = WMO_WEATHER_CODES.get(d_code, "Clear")
                forecast_lines.append(
                    f"| {dates[i]} | {d_cond} | {mins[i]}°C – {maxs[i]}°C |"
                )

            forecast_table = (
                "| Date | Condition | Temp Range |\n"
                "|------|-----------|------------|\n"
                + "\n".join(forecast_lines)
            ) if forecast_lines else ""

            return f"""## 🌤 Current Weather — {location_name}

| Metric | Value |
|--------|-------|
| **Condition** | {condition} |
| **Temperature** | {temp_c}°C |
| **Wind Speed** | {wind} km/h |

### 📅 3-Day Forecast

{forecast_table}
"""
    except Exception as err:
        logger.warning(f"Open-Meteo weather fetch failed for {city}: {err}")
        return None


# ── Fetch helpers ─────────────────────────────────────────────────────────

async def _fetch_weather_json(city: str) -> Optional[dict]:
    """Fetch full weather JSON from wttr.in."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        async with httpx.AsyncClient(timeout=3.5, follow_redirects=True, headers=headers) as client:
            r = await client.get(WEATHER_URL.format(city=city.replace(" ", "+")))
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("wttr.in JSON fetch failed for %s: %s", city, exc)
        return None


async def _fetch_weather_brief(city: str) -> str:
    """Single-line weather summary as fallback."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        async with httpx.AsyncClient(timeout=3.5, follow_redirects=True, headers=headers) as client:
            r = await client.get(WTTR_BRIEF_URL.format(city=city.replace(" ", "+")))
            r.raise_for_status()
            return r.text.strip()
    except Exception as exc:
        logger.warning("wttr.in brief fetch failed: %s", exc)
        return f"Weather data unavailable for {city}."


def _parse_weather(data: dict, city: str) -> str:
    """Convert wttr.in JSON → concise Markdown block."""
    try:
        cur = data["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp_c = cur["temp_C"]
        temp_f = cur["temp_F"]
        feels_c = cur["FeelsLikeC"]
        humidity = cur["humidity"]
        wind_kmph = cur["windspeedKmph"]
        wind_dir = cur["winddir16Point"]
        visibility = cur["visibility"]
        uv = cur.get("uvIndex", "N/A")
        pressure = cur.get("pressure", "N/A")

        nearest = data.get("nearest_area", [{}])[0]
        area = nearest.get("areaName", [{}])[0].get("value", city)
        country = nearest.get("country", [{}])[0].get("value", "")

        forecast_lines = []
        for day in data.get("weather", [])[:3]:
            date = day.get("date", "")
            max_c = day.get("maxtempC", "?")
            min_c = day.get("mintempC", "?")
            hourly = day.get("hourly", [])
            day_desc = hourly[4]["weatherDesc"][0]["value"] if len(hourly) > 4 else "N/A"
            chance_rain = hourly[4].get("chanceofrain", "?") if len(hourly) > 4 else "?"
            forecast_lines.append(
                f"| {date} | {day_desc} | {min_c}°C – {max_c}°C | 🌧 {chance_rain}% |"
            )

        forecast_table = (
            "| Date | Condition | Temp Range | Rain Chance |\n"
            "|------|-----------|------------|-------------|\n"
            + "\n".join(forecast_lines)
        ) if forecast_lines else ""

        return f"""## 🌤 Current Weather — {area}, {country}

| Metric | Value |
|--------|-------|
| **Condition** | {desc} |
| **Temperature** | {temp_c}°C / {temp_f}°F |
| **Feels Like** | {feels_c}°C |
| **Humidity** | {humidity}% |
| **Wind** | {wind_kmph} km/h {wind_dir} |
| **Visibility** | {visibility} km |
| **UV Index** | {uv} |
| **Pressure** | {pressure} hPa |

### 📅 3-Day Forecast

{forecast_table}
"""
    except Exception as exc:
        logger.warning("Weather parse error: %s", exc)
        return f"Could not parse weather data for {city}."


async def _fetch_news(category: str) -> list[dict]:
    """Fetch and parse RSS/Atom feed for the given category with fallback feeds."""
    urls = NEWS_FEEDS.get(category, NEWS_FEEDS[DEFAULT_CATEGORY])
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    import re

    for url in urls:
        try:
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
                headers=headers,
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                xml_text = r.text

            root = SafeET.fromstring(xml_text)
            items = root.findall(".//{*}item") or root.findall(".//item") or root.findall(".//{*}entry") or root.findall(".//entry")
            articles = []
            for item in items[:MAX_ARTICLES]:
                def txt(tag: str) -> str:
                    el = item.find(f"{{*}}{tag}") or item.find(tag)
                    if el is None:
                        return ""
                    if tag == "link" and el.attrib.get("href"):
                        return el.attrib.get("href")
                    return (el.text or "").strip()

                title = txt("title").replace("<![CDATA[", "").replace("]]>", "")
                link = txt("link")
                desc = txt("description") or txt("summary") or txt("content")
                desc = desc.replace("<![CDATA[", "").replace("]]>", "")
                desc = re.sub(r"<[^>]+>", "", desc).strip()[:300]
                pub_date = txt("pubDate") or txt("published") or txt("updated")

                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": desc,
                        "pubDate": pub_date,
                    })

            if articles:
                return articles
        except Exception as exc:
            logger.warning("RSS fetch/parse failed for %s at %s: %s", category, url, exc)

    return []


def _format_news(articles: list[dict], category: str) -> str:
    if not articles:
        return f"No news articles found for **{category}**."
    lines = [f"## 📰 {category} News — Latest {len(articles)} Headlines\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"### {i}. {a['title']}")
        if a["description"]:
            lines.append(f"> {a['description']}")
        if a["link"]:
            lines.append(f"[Read more]({a['link']})")
        if a["pubDate"]:
            lines.append(f"*Published: {a['pubDate'][:30]}*")
        lines.append("")
    return "\n".join(lines)


# ── Agent ─────────────────────────────────────────────────────────────────

class WeatherNewsAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="weather_news",
            name="Weather & News Agent",
            description=(
                "Real-time weather forecasts and top headlines fetched live "
                "from wttr.in and major RSS feeds — no API keys needed."
            ),
            icon="CloudSun",
            capabilities=[
                "real_time_weather",
                "3_day_forecast",
                "live_news_headlines",
                "category_news",
                "ai_weather_insights",
            ],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        """Detect intent (weather / news / both) from user_input, fetch data, enrich with LLM."""
        from src.services.llm import llm_service

        lower = user_input.lower()

        # Detect weather vs news intent
        explicit_weather = any(w in lower for w in [
            "weather", "temperature", "forecast", "rain", "humidity", "wind",
            "climate", "sunny", "cloudy", "storm", "snow", "hot", "cold",
        ])
        wants_news = any(w in lower for w in [
            "news", "headline", "article", "latest", "update", "current",
            "today", "breaking", "report", "story",
        ])

        wants_weather = explicit_weather
        if not wants_weather and not wants_news:
            wants_news = True

        # Detect city for weather
        city = context.get("city", "")
        if not city:
            import re
            m = re.search(
                r"(?:weather|forecast|temperature|climate)\s+(?:in|for|at|of)?\s*([a-z ]{2,30})",
                lower,
            )
            city = m.group(1).strip().title() if m else "India"

        # Detect news category
        category = context.get("news_category", DEFAULT_CATEGORY)
        for cat in NEWS_FEEDS:
            if cat.lower() in lower:
                category = cat
                break

        # Fetch concurrently
        tasks = []
        if wants_weather:
            tasks.append(_fetch_weather_json(city))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        if wants_news:
            tasks.append(_fetch_news(category))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        weather_data, news_articles = await asyncio.gather(*tasks)

        # Format raw data
        sections: list[str] = []

        if wants_weather:
            # 1. Try Open-Meteo API first (sub-second, 100% free, zero key)
            weather_text = await _fetch_open_meteo_weather(city)
            if not weather_text:
                # 2. Fallback to wttr.in JSON
                w_json = await _fetch_weather_json(city)
                if w_json:
                    weather_text = _parse_weather(w_json, city)
                else:
                    # 3. Fallback to wttr.in brief summary
                    brief = await _fetch_weather_brief(city)
                    weather_text = f"## 🌤 Weather — {city}\n\n{brief}"
            if weather_text:
                sections.append(weather_text)

        if wants_news and news_articles:
            sections.append(_format_news(news_articles, category))

        raw_data = "\n\n---\n\n".join(sections) if sections else "No live feeds fetched."

        # LLM enrichment — summarize & add insights
        try:
            enriched = await llm_service.generate(
                prompt=f"User request: {user_input}\n\nLive context:\n\n{raw_data}",
                system_instruction=(
                    "You are an intelligent, helpful Weather, News, and Knowledge AI Assistant. "
                    "Your top priority is to directly, accurately, and thoroughly answer the user's specific question "
                    "(e.g., if asked 'what is E20 fuel?', explain E20 fuel, its 20% ethanol blend, engine compatibility, and benefits in detail). "
                    "Use the live weather/news data provided below if relevant to the query. "
                    "Do NOT output unrelated weather forecasts if the user's question is about a different topic (such as fuel, automobiles, technology, science, etc.)."
                ),
            )
            return AgentResult(success=True, output=enriched, metadata={"city": city, "news_category": category})
        except Exception as exc:
            logger.error("LLM enrichment failed: %s", exc)
            # Return raw data without enrichment
            return AgentResult(success=True, output=raw_data, metadata={"city": city, "news_category": category})
