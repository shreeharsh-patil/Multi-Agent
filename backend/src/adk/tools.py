"""ADK tool definitions for all agents.

Each tool wraps a service call as a Google ADK FunctionTool
so agents can invoke them via function calling.
"""

import json
import asyncio
import httpx
from google.adk.tools import FunctionTool
from src.utils.logger import logger
from src.config import settings

class FirecrawlRotator:
    def __init__(self):
        self._current_idx = 0
        self._lock = asyncio.Lock()

    def get_keys(self):
        raw_keys = settings.firecrawl_api_key or ""
        return [k.strip() for k in raw_keys.split(",") if k.strip()]

    async def execute_request(self, method: str, endpoint: str, **kwargs) -> dict:
        keys = self.get_keys()
        if not keys:
            raise ValueError("FIRECRAWL_API_KEY is not configured in .env.")
        
        attempts = len(keys)
        async with self._lock:
            start_idx = self._current_idx

        last_error = None
        for i in range(attempts):
            idx = (start_idx + i) % attempts
            key = keys[idx]
            masked_key = f"...{key[-4:]}" if len(key) > 4 else "..."
            
            # Copy kwargs to prevent mutation between retries
            req_kwargs = kwargs.copy()
            headers = req_kwargs.pop("headers", {})
            headers = headers.copy() if headers else {}
            headers["Authorization"] = f"Bearer {key}"
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"https://api.firecrawl.dev/v1{endpoint}"
                    if method.upper() == "POST":
                        response = await client.post(url, headers=headers, **req_kwargs)
                    else:
                        response = await client.get(url, headers=headers, **req_kwargs)
                    
                    if response.status_code == 429:
                        raise Exception("Rate limit reached (429)")
                    elif response.status_code in (401, 403):
                        raise Exception(f"Authentication failure ({response.status_code})")
                    elif response.status_code != 200:
                        raise Exception(f"Request failed with status {response.status_code}: {response.text}")
                    
                    # Update index to the successful key
                    async with self._lock:
                        self._current_idx = idx
                        
                    return response.json()
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Firecrawl API key rotation: Key {masked_key} failed. "
                    f"Error: {e}. Retrying with next key..."
                )
        
        logger.error(f"All {attempts} Firecrawl keys failed.")
        raise last_error

firecrawl_rotator = FirecrawlRotator()



async def knowledge_search(query: str, user_id: str = "default") -> str:
    """Search the knowledge base for relevant document chunks.

    Args:
        query: The search query
        user_id: The user ID

    Returns:
        JSON string of search results with content and citations
    """
    from src.services.rag.opendocuments_client import should_use_opendocuments, opendocuments_client
    if await should_use_opendocuments(user_id):
        try:
            res = await opendocuments_client.query_rag(query, top_k=5)
            results = []
            for doc in res.get("results", []):
                meta = doc.get("metadata", {})
                results.append(
                    {
                        "content": doc.get("content", ""),
                        "file_name": meta.get("file_name", "Unknown"),
                        "page_number": meta.get("page_number"),
                        "score": round(doc.get("score", 0), 4),
                    }
                )
            if not results:
                return "No relevant documents found in OpenDocuments knowledge base."
            return json.dumps(results, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"OpenDocuments search tool error: {e}")
            return f"Search failed: {e}"

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
        return json.dumps(memories, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Memory search failed: {e}"


async def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Uses AST validation to allow only numeric expressions and math functions.

    Args:
        expression: The math expression (e.g. '2 + 2', 'sqrt(16)', '3 * 7')

    Returns:
        The calculated result
    """
    import ast
    import math
    safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    safe_dict.update({"abs": abs, "min": min, "max": max, "round": round, "sum": sum})
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        allowed = (ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
                   ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
                   ast.USub, ast.Mod, ast.FloorDiv, ast.Name, ast.Call, ast.List, ast.Tuple)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in safe_dict:
                    raise ValueError(f"Unknown variable: {node.id}")
            elif isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ValueError("Only named functions allowed")
                if node.func.id not in safe_dict:
                    raise ValueError(f"Unknown function: {node.func.id}")
            elif not isinstance(node, allowed):
                raise ValueError(f"Unsupported syntax: {type(node).__name__}")
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"Result: {result}"
    except Exception as e:
        exc = str(e)
        if "Unsupported syntax" in exc or "Unknown" in exc:
            return f"Calculation error: {e}"
        return f"Calculation error: {e}"


async def web_search(query: str, for_research: bool = False) -> str:
    """Search the internet for current information.

    Args:
        query: The search query
        for_research: If True, returns more results with full markdown content
                       (used by the Research Agent for deep research)

    Returns:
        Search result summary
    """
    # If Firecrawl is configured, use it for rich web search!
    if settings.firecrawl_api_key:
        try:
            logger.info(f"Using Firecrawl search for query: {query}")
            max_items = 5 if for_research else 3
            response = await firecrawl_rotator.execute_request(
                "POST",
                "/search",
                json={"query": query, "limit": max_items, "lang": "en",
                      "scrapeOptions": {"formats": ["markdown"]}}
            )
            # v2 returns results at top-level key "data" (list of objects)
            data = response.get("data", []) or response.get("results", [])
            if not data:
                return f"No results found on Firecrawl for query: '{query}'"

            results = []
            for item in data[:max_items]:
                title = item.get("title", "No Title")
                url = item.get("url", "No URL")
                # For research, include full markdown content when available
                if for_research:
                    content = item.get("markdown", "") or item.get("content", "") or item.get("description", "")
                    snippet = content[:2000] if content else "No content extracted"
                else:
                    snippet = (
                        item.get("description", "")
                        or item.get("markdown", "")[:300]
                        or item.get("content", "")[:300]
                    )
                results.append(f"### {title}\nURL: {url}\n{snippet}\n")
            return "\n".join(results)
        except Exception as e:
            logger.error(f"Firecrawl search failed, falling back to DuckDuckGo: {e}")

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


async def scrape_page(url: str) -> str:
    """Scrape a web page and convert it into clean markdown format.

    Uses Firecrawl when the API key is configured (recommended), otherwise
    falls back to a basic HTTP fetch + HTML-to-text extraction so the
    Research Agent can always gather source content.

    Args:
        url: The URL of the web page to scrape.

    Returns:
        The page content in markdown format.
    """
    # Try Firecrawl first when configured
    if settings.firecrawl_api_key:
        try:
            logger.info(f"Using Firecrawl to scrape URL: {url}")
            response = await firecrawl_rotator.execute_request(
                "POST",
                "/scrape",
                json={"url": url, "formats": ["markdown"], "onlyMainContent": True}
            )
            markdown = response.get("data", {}).get("markdown", "")
            if markdown:
                return markdown[:15000]  # Limit to prevent prompt/context window issues
        except Exception as e:
            logger.warning(f"Firecrawl scrape failed, falling back to HTTP fetch: {e}")

    # Basic fallback: fetch HTML and strip tags
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                import re
                html = resp.text
                # Remove script/style tags and their content
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                # Strip remaining HTML tags
                text = re.sub(r'<[^>]+>', '', html)
                # Collapse whitespace
                text = re.sub(r'\n\s*\n', '\n\n', text)
                text = re.sub(r' {2,}', ' ', text)
                text = text.strip()[:15000]
                if text:
                    logger.info(f"Successfully scraped URL via HTTP fallback: {url}")
                    return text
    except Exception as e:
        logger.warning(f"HTTP fallback scrape failed for {url}: {e}")

    return "Error: Could not scrape page content."



async def find_user_access_token(user_id: str) -> str:
    """Retrieve the user's Google Drive access token from the database.

    Tries by MongoDB ObjectId first, then by email as fallback.
    The ADK receives user_id as an ObjectId string from the session.
    """
    from src.models.user import User

    # Try by MongoDB _id first (most common case)
    user = await User.get(user_id)
    if user and user.access_token:
        return user.access_token

    # Fallback: try by email
    user = await User.find_one(User.email == user_id)
    if user and user.access_token:
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
scrape_page_tool = FunctionTool(func=scrape_page)
drive_list_tool = FunctionTool(func=drive_list)
drive_upload_tool = FunctionTool(func=drive_upload)
drive_delete_tool = FunctionTool(func=drive_delete)

