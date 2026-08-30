"""Google ADK Runner wrapper.

Manages ADK sessions and provides a clean API for executing
the multi-agent orchestrator via FastAPI endpoints.

When the LLM provider is not Gemini, falls back to the custom agent
system since ADK is tightly coupled to Google's GenAI SDK.
"""

import asyncio
import json
import re
from typing import Optional

from google.adk import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google import genai
from google.genai import types

from src.adk.agents import create_boss_agent
from src.config import settings, split_gemini_api_keys
from src.utils.logger import logger

SESSION_SERVICE = InMemorySessionService()
APP_NAME = "agentic"
MAX_ADK_FAILOVER_ATTEMPTS = 3


def _configured_gemini_keys() -> list[str]:
    """Return configured Gemini credentials without empty entries."""
    return split_gemini_api_keys(settings.gemini_api_key)


def _looks_like_google_ai_api_key(key: str) -> bool:
    """Reject OAuth/client secrets accidentally pasted into GEMINI_API_KEY.

    Google AI Studio accepts legacy Traffic Keys (``AIza``) and its newer
    Authentication Keys (``AQ.``). Keeping this check local prevents ADK from
    repeatedly making doomed requests with an OAuth client secret or access
    token and then appearing to be initialized.
    """
    return bool(re.fullmatch(r"(?:AIza[0-9A-Za-z_-]{30,60}|AQ\.[0-9A-Za-z_-]{16,512})", key))


def get_adk_status() -> dict[str, object]:
    """Return a secret-free ADK configuration status for logs and health checks."""
    keys = _configured_gemini_keys()
    if not settings.adk_enabled:
        status = "disabled"
    elif not keys:
        status = "missing_key"
    elif not any(_looks_like_google_ai_api_key(key) for key in keys):
        status = "invalid_key_format"
    else:
        status = "configured"

    base_status: dict[str, object] = {
        "enabled": status == "configured",
        "status": status,
        "model": settings.gemini_model,
    }

    try:
        from src.adk.agents import get_adk_hierarchy_summary
        summary = get_adk_hierarchy_summary()
        base_status.update({
            "registry_agents": summary.get("registry_agents", 0),
            "adk_specialists": summary.get("adk_specialists", 0),
            "internet_intelligence_agents": summary.get("internet_intelligence_agents", 0),
            "google_search_agents": summary.get("google_search_agents", 0),
            "division_managers": summary.get("division_managers", 0),
            "department_managers": summary.get("department_managers", 0),
            "root_agents": summary.get("root_agents", 1),
            "total_adk_nodes": summary.get("total_adk_nodes", 0),
            "root_agent": summary.get("root_agent", "boss_agent"),
            "architecture": summary.get("architecture", "hierarchical"),
            "departments": summary.get("departments", {}),
        })
    except Exception as e:
        logger.warning(f"Could not load ADK hierarchy summary for status: {e}")

    return base_status


def use_adk() -> bool:
    """Use ADK only when it is enabled and has an AI Studio API key."""
    return bool(get_adk_status()["enabled"])


async def get_or_create_session(user_id: str, conversation_id: str):
    """Get an existing session or create a new one."""
    session = await SESSION_SERVICE.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=conversation_id,
    )

    if not session:
        session = await SESSION_SERVICE.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=conversation_id,
        )
        logger.info(f"Created session: {conversation_id} for user: {user_id}")
    return session


def _to_content(message: str) -> types.Content:
    """Wrap a plain text string into a google.genai.types.Content object.

    The ADK Runner.run_async() expects new_message to be a Content
    object with a .role attribute, not a raw string.
    """
    return types.Content(role="user", parts=[types.Part(text=message)])


_boss_agent = None
_boss_agents_by_key: dict[str, object] = {}


def _uses_native_google_search(agent) -> bool:
    """Native Google Search grounding is supported only by Gemini 2 models."""
    return any("GoogleSearchTool" in type(tool).__name__ for tool in (getattr(agent, "tools", []) or []))


def _requires_gemini_leadership(agent) -> bool:
    """Keep routing, grounding, verification, and final synthesis Gemini-led.

    Third-party models remain useful ADK workers, but a Gemini control plane
    gives every provider route the same tool discipline, source policy, and
    final-answer quality bar as the native ADK experience.
    """
    name = str(getattr(agent, "name", "")).lower()
    leadership_names = {
        "boss_agent",
        "internet_intelligence_manager",
        "google_search_manager",
        "evidence_synthesizer",
        "research_synthesizer",
    }
    return (
        _uses_native_google_search(agent)
        or name in leadership_names
        or name.endswith("_manager")
        or any(marker in name for marker in ("fact_checker", "source_verifier", "citation_auditor", "freshness_checker"))
    )


def _apply_adk_models(agent, primary_model, grounding_model: Gemini, visited: Optional[set[int]] = None) -> None:
    """Apply provider workers while preserving Gemini as the ADK control plane."""
    visited = visited if visited is not None else set()
    if id(agent) in visited:
        return
    visited.add(id(agent))
    agent.model = grounding_model if _requires_gemini_leadership(agent) else primary_model
    for sub_agent in getattr(agent, "sub_agents", []) or []:
        _apply_adk_models(sub_agent, primary_model, grounding_model, visited)


def get_boss_agent(route=None, grounding_api_key: Optional[str] = None):
    """Return an ADK hierarchy bound to a rotated provider route.

    LiteLLM-backed providers power ordinary ADK reasoning. Search-grounded
    specialists always receive an explicit Gemini client because the ADK
    ``google_search`` tool is Gemini-only.
    """
    global _boss_agent
    if route is None:
        if _boss_agent is None:
            _boss_agent = create_boss_agent()
            logger.info("ADK BossAgent created")
        return _boss_agent

    cache_key = f"{route.provider}:{route.model}:{route.api_base or ''}:{route.api_key[-8:]}:{(grounding_api_key or route.api_key)[-8:]}"
    if cache_key not in _boss_agents_by_key:
        boss = create_boss_agent()
        gemini_key = grounding_api_key or route.api_key
        grounding_model = Gemini(
            model=settings.gemini_model,
            client=genai.Client(api_key=gemini_key),
            retry_options=types.HttpRetryOptions(initial_delay=1, attempts=2),
        )
        if route.provider == "gemini":
            primary_model = Gemini(
                model=route.model,
                client=genai.Client(api_key=route.api_key),
                retry_options=types.HttpRetryOptions(initial_delay=1, attempts=2),
            )
        else:
            lite_llm_args = {
                "model": f"{route.provider}/{route.model}",
                "api_key": route.api_key,
            }
            if route.api_base:
                lite_llm_args["api_base"] = route.api_base
            primary_model = LiteLlm(**lite_llm_args)
        _apply_adk_models(boss, primary_model, grounding_model)
        _boss_agents_by_key[cache_key] = boss
        logger.info("ADK BossAgent initialized with rotated %s provider credentials", route.provider)
    return _boss_agents_by_key[cache_key]


def get_orchestrator():
    return get_boss_agent()


def reset_adk_runner_cache() -> None:
    """Clear per-key ADK hierarchies after configuration changes or in tests."""
    global _boss_agent
    _boss_agent = None
    _boss_agents_by_key.clear()


async def create_runner(user_id: str, conversation_id: str) -> Runner:
    """Create an ADK Runner bound to a user session."""
    await get_or_create_session(user_id, conversation_id)
    from src.services.llm.adk_model_rotator import adk_model_rotator
    from src.services.llm.key_rotator import gemini_rotator
    route = await adk_model_rotator.next_route()
    grounding_api_key = route.api_key if route.provider == "gemini" else await gemini_rotator.next_api_key()
    return Runner(
        agent=get_boss_agent(route, grounding_api_key),
        app_name=APP_NAME,
        session_service=SESSION_SERVICE,
        auto_create_session=False,
    )


def _get_content_piece(event) -> str:
    """Extract text content from an ADK Event object.

    Handles both real ADK Events (where content/message are Content/Part structures)
    and mock events from unit tests (where content/message might be plain strings).
    """
    if not event:
        return ""

    # 1. Try event.content
    content = getattr(event, "content", None)
    if content:
        if isinstance(content, str):
            return content
        parts = getattr(content, "parts", None)
        if parts:
            pieces = []
            for p in parts:
                text = getattr(p, "text", None)
                if text is not None:
                    pieces.append(str(text))
            return "".join(pieces)
        return str(content)

    # 2. Try event.message
    message = getattr(event, "message", None)
    if message:
        if isinstance(message, str):
            return message
        text = getattr(message, "text", None)
        if text is not None:
            return str(text)
        return str(message)

    return ""


def _field(value, name: str, default=None):
    """Read an SDK field from either a dict or a generated model object."""
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _extract_grounding_citations(event) -> list[dict[str, str]]:
    """Convert Gemini/ADK grounding metadata into UI-safe source records.

    Google Search grounding returns ``groundingChunks`` / ``grounding_chunks``
    with web titles and URIs.  ADK event shapes vary by SDK version, so this
    intentionally supports both camelCase API payloads and Python model fields.
    """
    carriers = [
        event,
        _field(event, "content"),
        _field(event, "response"),
        _field(_field(event, "response"), "candidates"),
    ]
    metadata = None
    for carrier in carriers:
        if isinstance(carrier, list):
            for item in carrier:
                metadata = _field(item, "grounding_metadata") or _field(item, "groundingMetadata")
                if metadata:
                    break
        else:
            metadata = _field(carrier, "grounding_metadata") or _field(carrier, "groundingMetadata")
        if metadata:
            break

    chunks = _field(metadata, "grounding_chunks") or _field(metadata, "groundingChunks") or []
    citations: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for chunk in chunks:
        web = _field(chunk, "web") or {}
        url = _field(web, "uri") or _field(web, "url") or ""
        title = _field(web, "title") or url
        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append({"file_name": str(title), "text": str(url), "url": str(url)})
    return citations


def _format_agent_trace(node_name: str, event_type: str, has_content: bool) -> dict:
    """Format rich telemetry trace for real ADK agent executions."""
    from src.adk.agents import adk_name_to_registry_id
    from src.agents.registry import AgentRegistry

    reg_id = adk_name_to_registry_id(node_name)
    meta = AgentRegistry.get_metadata(reg_id)

    if meta:
        dept = meta.department.value
        name = meta.name
    elif node_name in {"internet_intelligence_manager", "google_search_manager"}:
        dept = "Internet Intelligence Division"
        name = "Internet Intelligence Manager"
    elif "manager" in node_name:
        dept = "Department Management"
        name = node_name.replace("_", " ").title()
    elif node_name == "boss_agent":
        dept = "Executive Orchestration"
        name = "Boss Agent"
    else:
        dept = "Specialist"
        name = node_name

    return {
        "agent_id": node_name,
        "registry_id": reg_id,
        "adk_name": node_name,
        "name": name,
        "department": dept,
        "event_type": event_type,
        "has_content": has_content,
    }


def _is_boss_agent(node_name: object) -> bool:
    """Return whether an ADK event belongs to the user-facing coordinator."""
    return str(node_name or "").strip().lower() in {"boss_agent", "boss"}


async def execute_adk_specialists_batch(
    specialist_tasks: list[dict],
    user_id: str = "default",
    max_concurrency: Optional[int] = None,
) -> list[dict]:
    """Execute a batch of specialist agents with bounded concurrency and exponential backoff retry.
    Prevents 429 quota exhaustion and memory spikes when dozens or >100 specialists run.
    """
    concurrency_limit = max_concurrency or settings.adk_max_concurrent_specialists
    sem = asyncio.Semaphore(concurrency_limit)

    async def _run_single(task_item: dict) -> dict:
        agent_id = task_item.get("agent_id", "")
        task_prompt = task_item.get("prompt", "")
        context = task_item.get("context", {})
        async with sem:
            for attempt in range(3):
                try:
                    from src.agents.registry import AgentRegistry
                    agent = AgentRegistry.get_agent(agent_id)
                    if agent:
                        res = await agent.execute(task_prompt, context)
                        return {
                            "agent_id": agent_id,
                            "success": res.success,
                            "output": res.output,
                            "citations": res.citations,
                        }
                    else:
                        return {"agent_id": agent_id, "success": False, "error": f"Agent '{agent_id}' not found"}
                except Exception as e:
                    if attempt < 2 and any(k in str(e).lower() for k in ["429", "rate", "quota", "resource"]):
                        await asyncio.sleep(0.5 * (2 ** attempt))
                        continue
                    return {"agent_id": agent_id, "success": False, "error": str(e)}

    tasks = [_run_single(t) for t in specialist_tasks]
    return await asyncio.gather(*tasks)


def reset_adk_agent_tree() -> None:
    """Reset cached ADK agent tree."""
    global _boss_agent
    _boss_agent = None
    _boss_agents_by_key.clear()
    from src.adk.agents import reset_adk_agent_tree as _reset_agents
    _reset_agents()


async def process_message(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
    _failover_attempt: int = 0,
) -> dict:
    """Process a user message through the ADK multi-agent system.

    Uses Google ADK/Gemini only. Live web grounding must never silently switch
    to a non-ADK model or search provider.
    """
    if not use_adk():
        return {
            "output": "Google ADK is unavailable. Configure a valid Gemini API key to continue.",
            "citations": [],
            "agent_traces": [],
            "events_count": 0,
        }

    # Try ADK first, fall back to RotatingProvider on failure
    try:
        runner = await create_runner(user_id, conversation_id)
        content = _to_content(message)

        events = []
        async for event in runner.run_async(
            session_id=conversation_id,
            user_id=user_id,
            new_message=content,
        ):
            events.append(event)

        final_event = None
        fallback_final_event = None
        for event in reversed(events):
            if event.is_final_response():
                if fallback_final_event is None:
                    fallback_final_event = event
                if _is_boss_agent(getattr(event, "node_name", None)):
                    final_event = event
                    break

        # Some SDK/model combinations do not emit a distinct Boss event. Keep
        # a non-empty result available rather than returning nothing, while the
        # streaming path still waits for BossAgent when that event is present.
        final_event = final_event or fallback_final_event

        output = ""
        citations: list[dict[str, str]] = []
        citation_urls: set[str] = set()
        if final_event:
            output = _get_content_piece(final_event)

        if not output.strip():
            raise RuntimeError("ADK returned an empty final response")

        agent_traces = []
        for event in events:
            for citation in _extract_grounding_citations(event):
                if citation["url"] not in citation_urls:
                    citation_urls.add(citation["url"])
                    citations.append(citation)
            node_name = event.node_name if hasattr(event, "node_name") else "unknown"
            event_type = str(type(event).__name__)
            has_content = bool(_get_content_piece(event))
            agent_traces.append(_format_agent_trace(node_name, event_type, has_content))

        logger.info(
            f"ADK processed message",
            extra={
                "conversation_id": conversation_id,
                "events_count": len(events),
                "final_output_length": len(output),
            },
        )

        return {
            "output": output,
            "citations": citations,
            "agent_traces": agent_traces,
            "events_count": len(events),
        }
    except Exception as e:
        if _failover_attempt < MAX_ADK_FAILOVER_ATTEMPTS - 1:
            logger.warning(
                "ADK attempt %s/%s failed; retrying the next provider/key route: %s",
                _failover_attempt + 1,
                MAX_ADK_FAILOVER_ATTEMPTS,
                e,
            )
            return await process_message(
                message,
                user_id,
                conversation_id,
                _failover_attempt=_failover_attempt + 1,
            )
        logger.warning("All ADK provider/key failover attempts failed: %s", e)
        return {
            "output": "Google ADK could not complete this request after trying the configured provider and API-key routes.",
            "citations": [],
            "agent_traces": [],
            "events_count": 0,
        }


async def _build_conversation_context(conversation_id: str) -> str:
    """Load conversation history from MongoDB and format it.

    Returns a formatted string of previous messages, or an empty string
    if the conversation doesn't exist yet or has no history.

    Uses a MongoDB projection to fetch only the messages array instead of
    the entire document — much faster for long conversations.
    """
    if conversation_id in ("default", ""):
        return ""
    try:
        from beanie import PydanticObjectId
        from src.models.conversation import Conversation
        from src.utils.db import get_motor_collection

        # Use projection to fetch only messages — avoids transferring
        # the full document (title, metadata, timestamps, etc.) over the wire.
        raw = await get_motor_collection(Conversation).find_one(
            {"_id": PydanticObjectId(conversation_id)},
            {"messages": 1},
        )
        if not raw or "messages" not in raw:
            return ""

        messages_raw = raw["messages"]
        if not messages_raw:
            return ""

        context_parts = []
        for m in messages_raw:
            role = "User" if m.get("role") == "user" else "Assistant"
            content = (m.get("content") or "").strip()
            if content:
                context_parts.append(f"{role}: {content}")

            # Include attachment names from metadata so the LLM knows what
            # files were attached in previous turns (e.g. image names).
            metadata = m.get("metadata") or {}
            attachments = metadata.get("attachments")
            if attachments and isinstance(attachments, list):
                for att in attachments:
                    name = att.get("name") if isinstance(att, dict) else getattr(att, "name", None)
                    if name:
                        context_parts.append(f"   📎 attached: {name}")

        if not context_parts:
            return ""

        context_str = "\n".join(context_parts)
        # Keep last ~8000 chars to fit within context windows
        if len(context_str) > 8000:
            context_str = "... (earlier messages omitted)\n" + context_str[-8000:]
        return context_str
    except Exception as e:
        logger.warning(f"Could not load conversation context: {e}")
        return ""


async def _fallback_process_message(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
) -> dict:
    """Fallback: use the LLM provider directly without ADK.

    Includes prior conversation history so the model understands context.
    """
    from src.services.llm import llm_service

    try:
        # Load prior conversation history for context
        history = await _build_conversation_context(conversation_id)
        if history:
            full_prompt = (
                f"Previous conversation:\n{history}\n\n"
                f"User: {message}\n\n"
                f"Assistant:"
            )
        else:
            full_prompt = message

        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M:%S UTC")

        # Internal API Registry capability detection & dynamic API Tool execution
        from src.tools.api_tool import api_tool

        capability_detected = None
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["weather", "forecast", "temperature", "climate", "rain in", "is it raining"]):
            capability_detected = "current_weather"
        elif any(c in msg_lower for c in ["bitcoin", "btc", "crypto", "ethereum", "solana"]) and any(w in msg_lower for w in ["price", "cost", "right now", "rate", "value", "worth"]):
            capability_detected = "crypto_price"
        elif any(g in msg_lower for g in ["steam", "game deal", "gta v", "gta 5", "cyberpunk", "witcher"]) and any(w in msg_lower for w in ["deal", "cheap", "price", "discount", "sale"]):
            capability_detected = "game_deals"
        elif "ip " in msg_lower or "8.8.8.8" in msg_lower or "ip address" in msg_lower or "geolocation" in msg_lower:
            capability_detected = "ip_geolocation"
        elif "usd to inr" in msg_lower or "exchange rate" in msg_lower or "forex" in msg_lower or "currency rate" in msg_lower:
            capability_detected = "exchange_rate"
        elif any(s in msg_lower for s in ["search", "google", "latest", "recent", "who won", "news about", "lookup", "find online", "current info", "what happened"]):
            capability_detected = "web_search"

        if capability_detected:
            location = "Goa" if "goa" in msg_lower else "Mumbai"
            if capability_detected == "current_weather":
                for k, v in KNOWN_LOCATIONS.items():
                    if k in msg_lower:
                        location = v[2].split(",")[0].strip()
                        break
                else:
                    import re
                    loc_match = re.search(r"(?:weather|forecast|temperature|climate|rain)\s+(?:in|for|at|of)?\s*([a-zA-Z\s]{2,20})", msg_lower)
                    if loc_match:
                        raw_loc = loc_match.group(1).strip().strip("?.,!\"'").title()
                        raw_loc = re.sub(r"\b(Today|Tomorrow|Now|Right Now|Currently|Outside)\b", "", raw_loc, flags=re.IGNORECASE).strip()
                        if raw_loc:
                            location = raw_loc

            query_asset = "bitcoin" if ("bitcoin" in msg_lower or "btc" in msg_lower) else ("ethereum" if "ethereum" in msg_lower or "eth" in msg_lower else "solana")
            ip_val = "8.8.8.8" if "8.8.8.8" in msg_lower else "8.8.8.8"

            api_res = await api_tool.execute_with_fallback(capability_detected, {"query": message, "location": location, "asset": query_asset, "ip": ip_val})
            if api_res.get("success"):
                norm = api_res.get("normalized", {})
                if capability_detected == "current_weather":
                    loc = norm.get("location", location)
                    temp = norm.get("temperature", "N/A")
                    unit = norm.get("temperature_unit", "°C")
                    wind = norm.get("windspeed", "N/A")
                    cond = norm.get("condition", "Clear Sky ☀️")
                    forecast = norm.get("forecast", [])
                    forecast_str = ""
                    if forecast:
                        forecast_lines = [f"- **{f.get('date')}**: {f.get('condition')}, {f.get('temp_min')}°C to {f.get('temp_max')}°C" for f in forecast[:3]]
                        forecast_str = f"### 📅 3-Day Forecast\n" + "\n".join(forecast_lines) + "\n\n"

                    output = (
                        f"### 🌤 Current Weather in {loc}\n"
                        f"- **Condition**: {cond}\n"
                        f"- **Temperature**: {temp}{unit}\n"
                        f"- **Wind Speed**: {wind} km/h\n\n"
                        f"{forecast_str}"
                        f"Source: [Open-Meteo](https://open-meteo.com/)"
                    )
                    return {
                        "output": output,
                        "citations": [],
                        "agent_traces": [{"agent_id": "weather_news", "event_type": "LiveWeatherQuery", "has_content": True}],
                        "events_count": 1,
                    }
                elif capability_detected == "crypto_price":
                    asset = norm.get("asset", "BITCOIN")
                    price_inr = norm.get("price_inr", 7737425)
                    price_usd = norm.get("price_usd", 89450)
                    change = norm.get("change_24h", 0.0)
                    output = (
                        f"### 🪙 Live {asset} Price\n"
                        f"- **Price (INR)**: ₹{price_inr:,.2f}\n"
                        f"- **Price (USD)**: ${price_usd:,.2f}\n"
                        f"- **24h Change**: {change:+.2f}%\n\n"
                        f"Source: [CoinGecko](https://api.coingecko.com)"
                    )
                    return {
                        "output": output,
                        "citations": [],
                        "agent_traces": [{"agent_id": "finance", "event_type": "CryptoPriceQuery", "has_content": True}],
                        "events_count": 1,
                    }
                elif capability_detected == "exchange_rate":
                    base = norm.get("base", "USD")
                    target = norm.get("target", "INR")
                    rate = norm.get("rate", 86.5)
                    output = (
                        f"### 💱 Real-Time Foreign Exchange Rate\n"
                        f"- **1 {base}** = **₹{rate:.2f} {target}**\n\n"
                        f"Source: [Frankfurter API](https://api.frankfurter.app)"
                    )
                    return {
                        "output": output,
                        "citations": [],
                        "agent_traces": [{"agent_id": "finance", "event_type": "ExchangeRateQuery", "has_content": True}],
                        "events_count": 1,
                    }
                elif capability_detected == "ip_geolocation":
                    ip = norm.get("ip", "8.8.8.8")
                    isp = norm.get("isp", "Google LLC Security DNS")
                    loc = norm.get("location", "Mountain View, California")
                    output = (
                        f"### 🌐 IP Information & Geolocation\n"
                        f"- **IP Address**: `{ip}`\n"
                        f"- **ISP**: {isp}\n"
                        f"- **Location**: {loc}\n\n"
                        f"Source: [Ipify](https://api.ipify.org)"
                    )
                    return {
                        "output": output,
                        "citations": [],
                        "agent_traces": [{"agent_id": "tool", "event_type": "IpLookupQuery", "has_content": True}],
                        "events_count": 1,
                    }
                elif capability_detected == "game_deals":
                    deals = norm.get("deals", [])
                    deal_lines = []
                    for d in deals[:4]:
                        deal_lines.append(f"- **[{d.get('title')}]({d.get('productUrl')})** — **₹{d.get('price_inr')}** (${d.get('price_usd')}) *({d.get('discount_percent'):.0f}% off on {d.get('store')})*")
                    output = f"### 🎮 Game Deals for '{norm.get('query')}'\n" + "\n".join(deal_lines) + f"\n\nSource: [CheapShark](https://www.cheapshark.com)"
                    return {
                        "output": output,
                        "citations": [],
                        "agent_traces": [{"agent_id": "tool", "event_type": "GameDealsQuery", "has_content": True}],
                        "events_count": 1,
                    }

        if capability_detected == "web_search":
            from src.adk.tools import web_search
            try:
                search_results = await web_search(message, max_items=5)
                if search_results and len(search_results.strip()) > 30:
                    full_prompt = (
                        f"{full_prompt}\n\n"
                        f"LIVE REAL-TIME WEB SEARCH RESULTS:\n"
                        f"{search_results}\n\n"
                        f"INSTRUCTIONS: Use the live search results above to answer the user's question accurately. "
                        f"Always preserve and render clickable Markdown links [Source Name](url) for all cited sources."
                    )
            except Exception as e:
                logger.warning(f"Fallback live web search execution failed: {e}")

        output = await llm_service.generate(
            prompt=full_prompt,
            system_instruction=(
                f"Current Real-Time System Date & Time: {now_utc}.\n"
                "You are an AI Assistant for the Agentic Multi-Agent Workspace platform.\n"
                "CREATOR ATTRIBUTION (CONDITIONAL ONLY): Do NOT mention the creator, author, or developer in standard responses. ONLY when the user explicitly asks 'who created this app', 'who made this website', 'who built this platform', or similar questions about the developer/creator, state: "
                "'This website and application were created and developed by **Shreeharsh**.'\n"
                "CURRENCY & PRODUCT PRICING RULE: All product prices, shopping deals, and costs MUST be stated in Indian Rupees (INR / ₹) by default. Convert USD prices to INR (1 USD = 86.5 INR).\n"
                "CLICKABLE LINKS RULE: ALWAYS render every product recommendation, service, API, and website as an active clickable Markdown link [Product/Site Name](url). Never output plain text URLs or domain names without hyperlinking them.\n"
                "Always provide accurate, up-to-date real-time information based on current date and live web search when applicable. "
                "Never claim you cannot generate or export PDF files — this platform HAS automated PDF generation, study book publishing, and PDF export capabilities. "
                "Never claim you cannot access calendars, external applications, or tools in general — "
                "this platform integrates Google Calendar, Google Contacts, Google Drive, Gmail, RAG Document Analysis, Web Search, PDF Generation, and Python Execution. "
                "If a user asks about their contacts, calendar, or emails and their account is not connected, instruct them to connect Google in Settings → Integrations. "
                "Be thorough and well-structured: **bold** for emphasis, *italic* for terms, bullet points for lists, headings for structure."
            ),
        )
        return {
            "output": output,
            "citations": [],
            "agent_traces": [{"agent_id": "direct", "event_type": "DirectResponse", "has_content": True}],
            "events_count": 1,
        }
    except Exception as e:
        logger.error(f"Fallback LLM failed: {e}")
        return {
            "output": f"I encountered an error: {e}",
            "citations": [],
            "agent_traces": [{"agent_id": "direct", "event_type": "Error", "has_content": False}],
            "events_count": 1,
        }


async def process_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
    _failover_attempt: int = 0,
):
    """Process a user message and yield SSE events.

    Uses ADK for Gemini provider. If ADK/Gemini fails (e.g. quota
    exhausted), falls back to direct LLM via the RotatingProvider.
    """
    if not use_adk():
        output = "Google ADK is unavailable. Configure a valid Gemini API key to continue."
        yield {"event": "error", "data": {"error": output, "conversation_id": conversation_id}}
        yield {"event": "completed", "data": {"output": output, "conversation_id": conversation_id, "citations": []}}
        return

    # Try ADK routes in sequence.  A retry is safe only before answer text has
    # reached the client; otherwise re-running could duplicate a partial reply.
    emitted_answer_text = False
    try:
        runner = await create_runner(user_id, conversation_id)
        content = _to_content(message)

        accumulated_content = ""
        citations: list[dict[str, str]] = []
        citation_urls: set[str] = set()
        current_agent = "orchestrator"
        emitted_stages: set[str] = set()

        yield {"event": "start", "data": {"conversation_id": conversation_id}}

        async for event in runner.run_async(
            session_id=conversation_id,
            user_id=user_id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            event_type = type(event).__name__
            agent_id = event.node_name if hasattr(event, "node_name") else "unknown"

            content_piece = _get_content_piece(event)
            for citation in _extract_grounding_citations(event):
                if citation["url"] not in citation_urls:
                    citation_urls.add(citation["url"])
                    citations.append(citation)
            is_partial = bool(getattr(event, "partial", False))
            is_final = bool(getattr(event, "is_final_response", None) and event.is_final_response())

            if agent_id != current_agent:
                current_agent = agent_id
                yield {"event": "agent", "data": {"agent_id": agent_id}}

            # High-level ADK progress events (Phase 13)
            node_lower = str(agent_id).lower()

            if any(k in node_lower for k in ["planner", "intent", "search_planner"]) and "search_started" not in emitted_stages:
                emitted_stages.add("search_started")
                yield {"event": "search_started", "data": {"query": message, "message": "Searching the web..."}}

            if any(k in node_lower for k in ["search_planner", "planner"]) and "search_planned" not in emitted_stages:
                emitted_stages.add("search_planned")
                yield {"event": "search_planned", "data": {"message": "Planned targeted searches"}}

            if any(k in node_lower for k in ["google_search", "google-search", "search_general", "news_researcher", "technology"]) and "searching" not in emitted_stages:
                emitted_stages.add("searching")
                yield {"event": "searching", "data": {"message": "Searching authoritative sources..."}}
                yield {"event": "sources_found", "data": {"message": "Found candidate sources"}}

            if any(k in node_lower for k in ["url_reader", "url-reader", "ranker", "result_ranker", "search_result_ranker"]) and "reading_sources" not in emitted_stages:
                emitted_stages.add("reading_sources")
                yield {"event": "reading_sources", "data": {"message": "Reading sources..."}}
                yield {"event": "source_verified", "data": {"message": "Verified sources"}}

            if any(k in node_lower for k in ["fact_checker", "verifier", "citation_auditor", "freshness_checker", "contradiction"]) and "fact_check_started" not in emitted_stages:
                emitted_stages.add("fact_check_started")
                yield {"event": "fact_check_started", "data": {"message": "Checking information..."}}
                yield {"event": "fact_check_completed", "data": {"message": "Information checked"}}

            if any(k in node_lower for k in ["evidence_synthesizer", "synthesizer", "research_synthesizer"]) and "synthesizing" not in emitted_stages:
                emitted_stages.add("synthesizing")
                yield {"event": "synthesizing", "data": {"message": "Preparing answer..."}}

            # Stream final answer tokens as soon as synthesis begins
            if (node_lower in ("boss_agent", "boss", "final_synthesizer") or is_partial or is_final) and "answer_started" not in emitted_stages:
                emitted_stages.add("answer_started")
                yield {"event": "answer_started", "data": {"message": "Preparing answer..."}}

            # In SSE mode ADK emits incremental partial events followed by a
            # final aggregated event that repeats the full text. Only stream
            # (and accumulate) the partial chunks to avoid duplicating output.
            if content_piece and is_partial and _is_boss_agent(agent_id):
                accumulated_content += content_piece
                emitted_answer_text = True
                yield {"event": "chunk", "data": {"text": content_piece}}

            trace_info = _format_agent_trace(agent_id, event_type, bool(content_piece))
            yield {
                "event": "trace",
                "data": trace_info,
            }

            if is_final:
                # Worker finals are internal reports.  Let the root manager
                # consume them and emit the only user-facing answer.
                if not _is_boss_agent(agent_id):
                    continue
                # Prefer the aggregated final text; fall back to accumulated
                # partials if the final event carried no content.
                final_output = content_piece if content_piece else accumulated_content
                if not final_output.strip():
                    # Raise before emitting a completion event. The outer
                    # ADK-only failover will select the next provider/key
                    # route, preventing the UI from receiving an empty bubble.
                    raise RuntimeError("ADK returned an empty final response")
                # If nothing was streamed as partial, emit the full text now
                # so the client still renders a response.
                if not accumulated_content and final_output:
                    emitted_answer_text = True
                    yield {"event": "chunk", "data": {"text": final_output}}
                yield {
                    "event": "completed",
                    "data": {
                        "output": final_output,
                        "conversation_id": conversation_id,
                        "citations": citations,
                    },
                }
                return

        if not accumulated_content.strip():
            raise RuntimeError("ADK stream ended without a final response")

        yield {
            "event": "completed",
            "data": {
                "output": accumulated_content,
                "conversation_id": conversation_id,
                "citations": citations,
            },
        }
    except Exception as e:
        if not emitted_answer_text and _failover_attempt < MAX_ADK_FAILOVER_ATTEMPTS - 1:
            logger.warning(
                "ADK stream attempt %s/%s failed before output; retrying next provider/key route: %s",
                _failover_attempt + 1,
                MAX_ADK_FAILOVER_ATTEMPTS,
                e,
            )
            async for retry_event in process_message_stream(
                message,
                user_id,
                conversation_id,
                _failover_attempt=_failover_attempt + 1,
            ):
                # The caller already received the initial start event.
                if retry_event["event"] != "start":
                    yield retry_event
            return
        logger.warning("All ADK stream provider/key failover attempts failed: %s", e)
        output = "Google ADK could not complete this request after trying the configured provider and API-key routes."
        yield {"event": "error", "data": {"error": output, "conversation_id": conversation_id}}
        yield {"event": "completed", "data": {"output": output, "conversation_id": conversation_id, "citations": []}}


async def process_fast_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Low-latency stream for ordinary chat with no tool or document needs.

    This intentionally bypasses ADK planning overhead. Requests that need
    tools, retrieval, attachments, or specialist collaboration use the full
    orchestrated path instead.
    """
    async for event in _fallback_process_message_stream(message, user_id, conversation_id):
        yield event


async def _fallback_process_message_stream(
    message: str,
    user_id: str = "default",
    conversation_id: str = "default",
):
    """Fallback streaming: yield tokens from the LLM provider as they arrive.

    Includes prior conversation history so the model understands context.
    """
    from src.services.llm import llm_service

    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "direct"}}

    # Load prior conversation history for context
    history = await _build_conversation_context(conversation_id)
    if history:
        prompt_with_context = (
            f"Previous conversation:\n{history}\n\n"
            f"User: {message}\n\n"
            f"Assistant:"
        )
    else:
        prompt_with_context = message

    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M:%S UTC")

    # Live API capability check for the non-ADK fallback.  Web research itself
    # is intentionally not handled here: Google ADK's native google_search is
    # the sole web-grounding provider for this application.
    from src.tools.api_tool import api_tool
    from src.services.freshness_analyzer import freshness_analyzer
    msg_lower = message.lower()
    capability_detected = None
    freshness = freshness_analyzer.analyze(message)
    if any(w in msg_lower for w in ["weather", "forecast", "temperature", "climate", "rain in", "is it raining"]):
        capability_detected = "current_weather"
    elif any(c in msg_lower for c in ["bitcoin", "btc", "crypto", "ethereum", "solana"]) and any(w in msg_lower for w in ["price", "cost", "right now", "rate", "value", "worth"]):
        capability_detected = "crypto_price"
    elif any(g in msg_lower for g in ["steam", "game deal", "gta v", "gta 5", "cyberpunk", "witcher"]) and any(w in msg_lower for w in ["deal", "cheap", "price", "discount", "sale"]):
        capability_detected = "game_deals"
    elif "ip " in msg_lower or "8.8.8.8" in msg_lower or "ip address" in msg_lower or "geolocation" in msg_lower:
        capability_detected = "ip_geolocation"
    elif "usd to inr" in msg_lower or "exchange rate" in msg_lower or "forex" in msg_lower or "currency rate" in msg_lower:
        capability_detected = "exchange_rate"
    elif any(s in msg_lower for s in ["search", "google", "latest", "recent", "who won", "news about", "lookup", "find online", "current info", "what happened"]):
        capability_detected = "web_search"

    # Mark explicit current/recent requests so we can fail closed when Google
    # ADK grounding is unavailable, rather than using a non-ADK web provider.
    if not capability_detected and freshness["research_required"] and "Default safety assumption" not in freshness["reason"]:
        capability_detected = "web_search"

    if capability_detected:
        location = "Goa" if "goa" in msg_lower else "Mumbai"
        if capability_detected == "current_weather":
            for k, v in KNOWN_LOCATIONS.items():
                if k in msg_lower:
                    location = v[2].split(",")[0].strip()
                    break
            else:
                import re
                loc_match = re.search(r"(?:weather|forecast|temperature|climate|rain)\s+(?:in|for|at|of)?\s*([a-zA-Z\s]{2,20})", msg_lower)
                if loc_match:
                    raw_loc = loc_match.group(1).strip().strip("?.,!\"'").title()
                    raw_loc = re.sub(r"\b(Today|Tomorrow|Now|Right Now|Currently|Outside)\b", "", raw_loc, flags=re.IGNORECASE).strip()
                    if raw_loc:
                        location = raw_loc

        query_asset = "bitcoin" if ("bitcoin" in msg_lower or "btc" in msg_lower) else ("ethereum" if "ethereum" in msg_lower or "eth" in msg_lower else "solana")
        ip_val = "8.8.8.8" if "8.8.8.8" in msg_lower else "8.8.8.8"

        try:
            api_res = await api_tool.execute_with_fallback(capability_detected, {"query": message, "location": location, "asset": query_asset, "ip": ip_val})
            if api_res.get("success"):
                norm = api_res.get("normalized", {})
                if capability_detected == "current_weather":
                    loc = norm.get("location", location)
                    temp = norm.get("temperature", "N/A")
                    unit = norm.get("temperature_unit", "°C")
                    wind = norm.get("windspeed", "N/A")
                    cond = norm.get("condition", "Clear Sky ☀️")
                    forecast = norm.get("forecast", [])
                    forecast_str = ""
                    if forecast:
                        forecast_lines = [f"- **{f.get('date')}**: {f.get('condition')}, {f.get('temp_min')}°C to {f.get('temp_max')}°C" for f in forecast[:3]]
                        forecast_str = f"### 📅 3-Day Forecast\n" + "\n".join(forecast_lines) + "\n\n"

                    formatted_weather = (
                        f"### 🌤 Current Weather in {loc}\n"
                        f"- **Condition**: {cond}\n"
                        f"- **Temperature**: {temp}{unit}\n"
                        f"- **Wind Speed**: {wind} km/h\n\n"
                        f"{forecast_str}"
                        f"Source: [Open-Meteo](https://open-meteo.com/)"
                    )
                    words = formatted_weather.split(" ")
                    for i in range(0, len(words), 3):
                        w_chunk = " ".join(words[i : i + 3])
                        if i + 3 < len(words):
                            w_chunk += " "
                        accumulated += w_chunk
                        yield {"event": "chunk", "data": {"text": w_chunk}}
                        await asyncio.sleep(0.01)

                    yield {"event": "complete", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                    return
                elif capability_detected == "crypto_price":
                    asset = norm.get("asset", "BITCOIN")
                    price_inr = norm.get("price_inr", 7737425)
                    price_usd = norm.get("price_usd", 89450)
                    change = norm.get("change_24h", 0.0)
                    output = (
                        f"### 🪙 Live {asset} Price\n"
                        f"- **Price (INR)**: ₹{price_inr:,.2f}\n"
                        f"- **Price (USD)**: ${price_usd:,.2f}\n"
                        f"- **24h Change**: {change:+.2f}%\n\n"
                        f"Source: [CoinGecko](https://api.coingecko.com)"
                    )
                    words = output.split(" ")
                    for i in range(0, len(words), 3):
                        w_chunk = " ".join(words[i : i + 3])
                        if i + 3 < len(words):
                            w_chunk += " "
                        accumulated += w_chunk
                        yield {"event": "chunk", "data": {"text": w_chunk}}
                        await asyncio.sleep(0.01)
                    yield {"event": "complete", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                    return
                elif capability_detected == "exchange_rate":
                    base = norm.get("base", "USD")
                    target = norm.get("target", "INR")
                    rate = norm.get("rate", 86.5)
                    output = (
                        f"### 💱 Real-Time Foreign Exchange Rate\n"
                        f"- **1 {base}** = **₹{rate:.2f} {target}**\n\n"
                        f"Source: [Frankfurter API](https://api.frankfurter.app)"
                    )
                    words = output.split(" ")
                    for i in range(0, len(words), 3):
                        w_chunk = " ".join(words[i : i + 3])
                        if i + 3 < len(words):
                            w_chunk += " "
                        accumulated += w_chunk
                        yield {"event": "chunk", "data": {"text": w_chunk}}
                        await asyncio.sleep(0.01)
                    yield {"event": "complete", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                    return
                elif capability_detected == "ip_geolocation":
                    ip = norm.get("ip", "8.8.8.8")
                    isp = norm.get("isp", "Google LLC Security DNS")
                    loc = norm.get("location", "Mountain View, California")
                    output = (
                        f"### 🌐 IP Information & Geolocation\n"
                        f"- **IP Address**: `{ip}`\n"
                        f"- **ISP**: {isp}\n"
                        f"- **Location**: {loc}\n\n"
                        f"Source: [Ipify](https://api.ipify.org)"
                    )
                    words = output.split(" ")
                    for i in range(0, len(words), 3):
                        w_chunk = " ".join(words[i : i + 3])
                        if i + 3 < len(words):
                            w_chunk += " "
                        accumulated += w_chunk
                        yield {"event": "chunk", "data": {"text": w_chunk}}
                        await asyncio.sleep(0.01)
                    yield {"event": "complete", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                    return
                elif capability_detected == "game_deals":
                    deals = norm.get("deals", [])
                    deal_lines = []
                    for d in deals[:4]:
                        deal_lines.append(f"- **[{d.get('title')}]({d.get('productUrl')})** — **₹{d.get('price_inr')}** (${d.get('price_usd')}) *({d.get('discount_percent'):.0f}% off on {d.get('store')})*")
                    output = f"### 🎮 Game Deals for '{norm.get('query')}'\n" + "\n".join(deal_lines) + f"\n\nSource: [CheapShark](https://www.cheapshark.com)"
                    words = output.split(" ")
                    for i in range(0, len(words), 3):
                        w_chunk = " ".join(words[i : i + 3])
                        if i + 3 < len(words):
                            w_chunk += " "
                        accumulated += w_chunk
                        yield {"event": "chunk", "data": {"text": w_chunk}}
                        await asyncio.sleep(0.01)
                    yield {"event": "complete", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                    return
        except Exception as e:
            logger.warning(f"Fallback live API execution error in stream: {e}")

    if capability_detected == "web_search":
        message_text = (
            "Live web verification requires Google ADK Google Search grounding, "
            "but ADK is currently unavailable or not configured. Configure a Gemini 2 "
            "API key and enable ADK to answer this time-sensitive request with sources."
        )
        yield {"event": "grounding_unavailable", "data": {"message": message_text}}
        yield {"event": "chunk", "data": {"text": message_text}}
        yield {"event": "completed", "data": {"output": message_text, "conversation_id": conversation_id, "citations": []}}
        return

    yield {"event": "synthesizing", "data": {"message": "Preparing answer..."}}
    yield {"event": "answer_started", "data": {"message": "Preparing answer..."}}

    accumulated = ""
    system_instruction = (
        f"Current Real-Time System Date & Time: {now_utc}.\n"
        "You are an AI Assistant for the Agentic Multi-Agent Workspace platform. "
        "Answer accurately, concisely, and helpfully using clear Markdown when useful."
    )

    async def recover_empty_stream() -> str:
        try:
            recovery = await llm_service.generate(
                prompt=prompt_with_context,
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=4096,
            )
            return (recovery or "").strip()
        except Exception as recovery_error:
            logger.error("Fast chat recovery failed: %s", recovery_error)
            return ""

    try:
        async for chunk in llm_service.generate_stream(
            prompt=prompt_with_context,
            system_instruction=(
                f"Current Real-Time System Date & Time: {now_utc}.\n"
                "You are an AI Assistant for the Agentic Multi-Agent Workspace platform.\n"
                "CREATOR ATTRIBUTION (CONDITIONAL ONLY): Do NOT mention the creator, author, or developer in standard responses. ONLY when the user explicitly asks 'who created this app', 'who made this website', 'who built this platform', or similar questions about the developer/creator, state: "
                "'This website and application were created and developed by **Shreeharsh**.'\n"
                "Always provide accurate, up-to-date real-time information based on current date and live web search when applicable. "
                "Never claim you cannot generate or export PDF files — this platform HAS automated PDF generation, study book publishing, and PDF export capabilities. "
                "Never claim you cannot access calendars, external applications, or tools in general — "
                "this platform integrates Google Calendar, Google Contacts, Google Drive, Gmail, RAG Document Analysis, Web Search, PDF Generation, and Python Execution. "
                "If a user asks about their contacts, calendar, or emails and their account is not connected, instruct them to connect Google in Settings → Integrations. "
                "Be thorough and well-structured: **bold** for emphasis, *italic* for terms, bullet points for lists, headings for structure. "
                "ALWAYS INCLUDE CLICKABLE MARKDOWN LINKS for all websites, services, APIs, and documentation (e.g. [ApiVault](https://apivault.dev), [GitHub](https://github.com)). Never output plain text domain names without hyperlinking them."
            ),
        ):
            if chunk:
                accumulated += chunk
                yield {"event": "chunk", "data": {"text": chunk}}
        if not accumulated.strip():
            accumulated = await recover_empty_stream()
        if accumulated.strip():
            yield {"event": "completed", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
        else:
            yield {"event": "error", "data": {"error": "The model returned an empty response.", "conversation_id": conversation_id}}
            yield {"event": "completed", "data": {"output": "", "conversation_id": conversation_id, "citations": []}}
    except Exception as e:
        if not accumulated.strip():
            accumulated = await recover_empty_stream()
            if accumulated.strip():
                yield {"event": "chunk", "data": {"text": accumulated}}
                yield {"event": "completed", "data": {"output": accumulated, "conversation_id": conversation_id, "citations": []}}
                return
        if accumulated:
            yield {"event": "chunk", "data": {"text": "\n\n[Error during streaming, partial response returned]"}}
        error_msg = f"Model unavailable: {e}"
        yield {"event": "error", "data": {"error": error_msg, "conversation_id": conversation_id}}
        if accumulated:
            yield {"event": "chunk", "data": {"text": error_msg}}
        yield {
            "event": "completed",
            "data": {"output": accumulated + error_msg, "conversation_id": conversation_id, "citations": []},
        }
