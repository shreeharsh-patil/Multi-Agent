"""ADK tool definitions for all agents.

Each tool wraps a service call as a Google ADK FunctionTool
so agents can invoke them via function calling.
"""

from google.adk.tools import FunctionTool
from src.utils.logger import logger


async def knowledge_search(query: str, user_id: str = "default") -> str:
    """Search the knowledge base for relevant document chunks.

    Args:
        query: The search query
        user_id: The user ID

    Returns:
        JSON string of search results with content and citations
    """
    from src.services.rag.retriever import get_retriever

    try:
        docs = await get_retriever().retrieve(query, user_id=user_id, top_k=5)
        if not docs:
            return "No relevant documents found in knowledge base."

        results = []
        for doc in docs:
            meta = doc.get("metadata", {})
            results.append(
                {
                    "content": doc.get("content", ""),
                    "file_name": meta.get("file_name", "Unknown"),
                    "page_number": meta.get("page_number"),
                    "score": round(doc.get("score", 0), 4),
                }
            )
        import json
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Knowledge search tool error: {e}")
        return f"Search failed: {e}"


async def memory_store(key: str, content: str, type: str = "conversation", user_id: str = "default") -> str:
    """Store a memory for the user.

    Args:
        key: Memory key (e.g. 'user_name', 'preference_language')
        content: Memory content
        type: Memory type (conversation, preference, fact, semantic)
        user_id: The user ID

    Returns:
        Confirmation message
    """
    from src.services.memory.service import memory_service

    try:
        await memory_service.store(user_id, key, content, type)
        logger.info(f"Memory stored: {key}")
        return f"Memory stored: {key}"
    except Exception as e:
        return f"Failed to store memory: {e}"


async def memory_search(query: str, user_id: str = "default") -> str:
    """Search the user's long-term memory for relevant information.

    Args:
        query: What to search for in memories
        user_id: The user ID

    Returns:
        JSON string of relevant memories
    """
    from src.services.memory.service import memory_service

    try:
        memories = await memory_service.search(user_id, query)
        if not memories:
            return "No relevant memories found."
        import json
        return json.dumps(memories, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Memory search failed: {e}"


async def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: The math expression (e.g. '2 + 2', 'sqrt(16)', '3 * 7')

    Returns:
        The calculated result
    """
    import math
    safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    safe_dict.update({"abs": abs, "min": min, "max": max, "round": round, "sum": sum})
    try:
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {e}"


async def web_search(query: str) -> str:
    """Search the internet for current information.

    Args:
        query: The search query

    Returns:
        Search result summary
    """
    return (
        f"Search request: '{query}'. "
        "Web search requires a configured search API (Google Search, etc.). "
        "Please set up the search API key in settings."
    )


async def drive_list(user_id: str = "default") -> str:
    """List Google Drive files.

    Args:
        user_id: The user ID

    Returns:
        List of Drive files
    """
    return (
        "Google Drive integration is configured. "
        "To access files, the user needs to authenticate with Google OAuth. "
        "Please ask the user to connect their Google Drive in Settings."
    )


# Export all tools as FunctionTool instances for ADK agents
knowledge_search_tool = FunctionTool(func=knowledge_search)
memory_store_tool = FunctionTool(func=memory_store)
memory_search_tool = FunctionTool(func=memory_search)
calculator_tool = FunctionTool(func=calculator)
web_search_tool = FunctionTool(func=web_search)
drive_list_tool = FunctionTool(func=drive_list)
