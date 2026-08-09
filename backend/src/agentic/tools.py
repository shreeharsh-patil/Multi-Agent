"""Tool registry and routing for the agentic engine.

Security model
--------------
* No worker ever receives unbounded tool access. The Boss grants a whitelist
  per subtask (`available_tools`) derived from the subtask's required
  capabilities via `CAPABILITY_TOOLS`.
* `run_authorized_tool()` refuses any tool not on the whitelist — this is the
  enforcement layer, independent of what an agent claims it can use.
* Secrets never enter LLM prompts. Tools that need credentials
  (e.g. Google Drive) resolve them server-side.

All tool functions take ``(task_context: dict, argument: str)`` and return a
plain string (evidence rendered into the agent prompt) for consistency.
"""

from __future__ import annotations

from src.utils.logger import logger

# Registered tool implementations, keyed by stable slug.
_TOOL_IMPL = {}


def register_tool(slug: str, fn) -> None:
    _TOOL_IMPL[slug] = fn


async def _web_search(ctx: dict, query: str) -> str:
    from src.adk.tools import web_search
    return await web_search(query or ctx.get("objective", ""), for_research=True)


async def _calculator(ctx: dict, expression: str) -> str:
    from src.adk.tools import calculator
    return await calculator(expression or ctx.get("instruction", ""))


async def _knowledge_search(ctx: dict, query: str) -> str:
    from src.adk.tools import knowledge_search
    return await knowledge_search(query or ctx.get("objective", ""), user_id=ctx.get("user_id", "default"))


async def _drive_list(ctx: dict, _argument: str) -> str:
    from src.adk.tools import drive_list
    return await drive_list(user_id=ctx.get("user_id", "default"))


async def _memory_search(ctx: dict, query: str) -> str:
    from src.adk.tools import memory_search
    return await memory_search(query or ctx.get("objective", ""), user_id=ctx.get("user_id", "default"))


async def _memory_store(ctx: dict, content: str) -> str:
    from src.adk.tools import memory_store
    return await memory_store(
        f"agentic:{ctx.get('task_id', '')}:{ctx.get('subtask', '')}"[:120],
        content[:2000],
        "conversation",
        user_id=ctx.get("user_id", "default"),
    )


register_tool("web_search", _web_search)
register_tool("calculator", _calculator)
register_tool("knowledge_search", _knowledge_search)
register_tool("drive", _drive_list)
register_tool("memory", _memory_search)
register_tool("memory_store", _memory_store)


def tool_slugs() -> list[str]:
    return sorted(_TOOL_IMPL)


async def run_authorized_tool(slug: str, ctx: dict, argument: str = "", allowed: list | None = None) -> str:
    """Run a tool only if authorized by the granting whitelist `allowed`."""
    if slug not in _TOOL_IMPL:
        logger.warning("Tool %s is not registered; blocked", slug)
        return "Tool unavailable."
    if allowed is not None and slug not in allowed:
        logger.warning("Tool %s was blocked: not authorized for this task", slug)
        return "Tool not authorized for this step."
    try:
        return await _TOOL_IMPL[slug](ctx, argument)
    except Exception as exc:  # never let a tool failure crash the run
        logger.warning("Tool %s failed: %s", slug, exc)
        return f"Tool '{slug}' failed: {exc}"


# ---------------------------------------------------------------------------
# Capability → tool routing (Boss uses this to grant a minimal tool whitelist)
# ---------------------------------------------------------------------------

CAPABILITY_TOOLS: dict[str, list[str]] = {
    "web_search": ["web_search"],
    "research": ["web_search"],
    "deep_research": ["web_search"],
    "technical_research": ["web_search"],
    "academic_research": ["web_search"],
    "documentation_research": ["web_search"],
    "competitive_research": ["web_search"],
    "fact_checking": ["web_search"],
    "source_evaluation": ["web_search"],
    "market_research": ["web_search"],
    "market_analysis": ["web_search"],
    "competitor_analysis": ["web_search"],
    "product_research": ["web_search"],
    "ai_research": ["web_search"],
    "policy_research": ["web_search"],
    "calculation": ["calculator"],
    "statistics": ["calculator"],
    "data_analysis": ["calculator"],
    "forecasting": ["calculator"],
    "spreadsheets": ["calculator"],
    "rag": ["knowledge_search"],
    "knowledge_base": ["knowledge_search"],
    "information_extraction": ["knowledge_search"],
    "documentation": ["knowledge_search"],
    "memory_recall": ["memory"],
    "long_term_memory": ["memory"],
    "drive": ["drive"],
    "file_management": ["drive", "memory_store"],
    "email_automation": ["memory_store"],
    "scheduling": ["memory_store"],
    "workflow_design": ["memory_store", "calculator"],
    "automation": ["memory_store", "web_search"],
    "reporting": ["calculator"],
}


def tools_for_capabilities(capabilities: list[str]) -> list[str]:
    """Deterministic minimal tool whitelist for a set of capabilities."""
    granted: list[str] = []
    for cap in capabilities or []:
        for tool in CAPABILITY_TOOLS.get(cap, []):
            if tool not in granted:
                granted.append(tool)
    return granted


def authorize_tool_set(agent_required_tools: list[str], available_tools: list[str]) -> list[str]:
    """Intersection of what the agent wants and what the Boss granted."""
    return [t for t in available_tools if t in (agent_required_tools or []) | set(available_tools)]