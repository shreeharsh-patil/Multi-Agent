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
    import json

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try DuckDuckGo-style search via a free API
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                },
            )
            if response.status_code == 200:
                data = response.json()
                results = []

                # Abstract text
                abstract = data.get("AbstractText", "")
                if abstract:
                    results.append(f"Summary: {abstract}")

                # Related topics
                topics = data.get("RelatedTopics", [])
                for topic in topics[:5]:
                    if "Text" in topic:
                        results.append(f"- {topic['Text']}")
                    elif "Topics" in topic:
                        for sub in topic.get("Topics", [])[:3]:
                            if "Text" in sub:
                                results.append(f"- {sub['Text']}")

                if results:
                    return "\n".join(results)

            # Fallback to a simple text message
            return (
                f"Search results for '{query}':\n"
                "1. Check Google for the latest information\n"
                "2. Browse relevant Wikipedia articles\n"
                f"Note: Full web search requires a dedicated API key (Google Custom Search, etc.)"
            )
    except ImportError:
        return f"Web search unavailable: httpx library not installed. Run: pip install httpx"
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Web search encountered an error: {e}. Please try again later."


import json


async def find_user_access_token(user_id: str) -> str:
    """Retrieve the user's Google Drive access token from the database."""
    from src.models.user import User

    user = await User.find_one(User.email == user_id)
    if user and user.access_token:
        return user.access_token

    # Also try by matching user_id to _id or other fields
    user = await User.get(user_id)
    if user and hasattr(user, 'access_token') and user.access_token:
        return user.access_token

    return ""


async def drive_list(user_id: str = "default") -> str:
    """List Google Drive files for the authenticated user.

    Args:
        user_id: The user ID or email

    Returns:
        JSON string of files in Drive
    """
    from src.services.drive.service import drive_service

    try:
        access_token = await find_user_access_token(user_id)
        if not access_token:
            return (
                "You need to connect Google Drive first. "
                "Please ask the user to go to Settings > Integrations > Google Drive "
                "and sign in with Google to grant Drive access."
            )

        files = await drive_service.list_files(access_token=access_token)
        if not files:
            return "Your Google Drive is empty. You can upload files to get started."

        results = []
        for f in files:
            results.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "type": "folder" if f.get("mimeType") == "application/vnd.google-apps.folder" else "file",
                "size": int(f.get("size", 0)),
                "modified": f.get("modifiedTime"),
            })

        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Drive list tool error: {e}")
        return f"Failed to list Drive files: {e}"


async def drive_upload(user_id: str, file_name: str, file_content: str) -> str:
    """Upload content as a file to Google Drive.

    Args:
        user_id: The user identifier
        file_name: The name for the file in Drive
        file_content: Text content to upload

    Returns:
        Confirmation message with file details
    """
    import tempfile
    from src.services.drive.service import drive_service

    try:
        access_token = await find_user_access_token(user_id)
        if not access_token:
            return "Please connect Google Drive first from Settings."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(file_content)
            tmp_path = f.name

        try:
            result = await drive_service.upload_file(
                access_token=access_token,
                file_path=tmp_path,
                file_name=file_name,
                mime_type="text/plain",
            )
            return json.dumps({
                "success": True,
                "file_id": result.get("id"),
                "file_name": result.get("name"),
                "web_link": result.get("webViewLink"),
            }, indent=2)
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Drive upload tool error: {e}")
        return f"Failed to upload to Drive: {e}"


async def drive_delete(user_id: str, file_id: str) -> str:
    """Delete a file from Google Drive.

    Args:
        user_id: The user identifier
        file_id: The ID of the file to delete

    Returns:
        Confirmation message
    """
    from src.services.drive.service import drive_service

    try:
        access_token = await find_user_access_token(user_id)
        if not access_token:
            return "Please connect Google Drive first from Settings."

        await drive_service.delete_file(access_token=access_token, file_id=file_id)
        return json.dumps({"success": True, "message": f"File {file_id} deleted from Drive"})
    except Exception as e:
        logger.error(f"Drive delete tool error: {e}")
        return f"Failed to delete Drive file: {e}"


# Export all tools as FunctionTool instances for ADK agents
knowledge_search_tool = FunctionTool(func=knowledge_search)
memory_store_tool = FunctionTool(func=memory_store)
memory_search_tool = FunctionTool(func=memory_search)
calculator_tool = FunctionTool(func=calculator)
web_search_tool = FunctionTool(func=web_search)
drive_list_tool = FunctionTool(func=drive_list)
drive_upload_tool = FunctionTool(func=drive_upload)
drive_delete_tool = FunctionTool(func=drive_delete)
