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

# Shared httpx client for Firecrawl to reuse TCP connections across requests.
_firecrawl_client: httpx.AsyncClient | None = None


def _get_firecrawl_client() -> httpx.AsyncClient:
    global _firecrawl_client
    if _firecrawl_client is None:
        _firecrawl_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
    return _firecrawl_client


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
                client = _get_firecrawl_client()
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

    Priority Order:
    1. Free Jina AI Search API (s.jina.ai)
    2. Free SearXNG Meta-Search API
    3. Free Wikipedia API Academic Search
    4. Free ArXiv Scientific Papers Search
    5. Free DuckDuckGo Search (duckduckgo_search / DDGS)
    6. Firecrawl Search API (Last Fallback, used only if configured & free search yields no results)
    """
    max_items = 5 if for_research else 3

    # 1. Free Jina AI Search API (https://s.jina.ai/)
    try:
        jina_res = await _jina_search(query, max_items)
        if jina_res and len(jina_res.strip()) > 30:
            logger.info(f"Successfully retrieved search results via Jina AI Search: {query}")
            return jina_res
    except Exception as e:
        logger.warning(f"Jina AI Search failed: {e}")

    # 2. Free SearXNG Meta-Search API
    try:
        searx_res = await _searxng_search(query, max_items)
        if searx_res and len(searx_res.strip()) > 30:
            logger.info(f"Successfully retrieved search results via SearXNG: {query}")
            return searx_res
    except Exception as e:
        logger.warning(f"SearXNG search failed: {e}")

    # 3. Free Wikipedia API Search
    try:
        wiki_res = await _wikipedia_search(query)
        if wiki_res and len(wiki_res.strip()) > 30:
            logger.info(f"Successfully retrieved search results via Wikipedia API: {query}")
            return wiki_res
    except Exception as e:
        logger.warning(f"Wikipedia search failed: {e}")

    # 4. Free ArXiv Academic Papers Search
    try:
        arxiv_res = await _arxiv_search(query)
        if arxiv_res and len(arxiv_res.strip()) > 30:
            logger.info(f"Successfully retrieved search results via ArXiv API: {query}")
            return arxiv_res
    except Exception as e:
        logger.warning(f"ArXiv search failed: {e}")

    # 5. 100% Free Live Web Search via DuckDuckGo
    try:
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_items))
                for item in ddg_results:
                    title = item.get("title", "No Title")
                    url = item.get("href", "No URL")
                    snippet = item.get("body", "No Snippet")
                    results.append(f"### {title}\nURL: {url}\n{snippet}\n")
        except Exception as ddg_err:
            logger.warning(f"duckduckgo_search package failed ({ddg_err}), trying HTTP DDG fallback")

        if results:
            return "\n".join(results)

        # HTTP Fallback search via DuckDuckGo Instant API
        client = _get_firecrawl_client()
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )
        if response.status_code == 200:
            data = response.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(f"Summary: {abstract}")
            topics = data.get("RelatedTopics", [])
            for topic in topics[:5]:
                if "Text" in topic:
                    results.append(f"- {topic['Text']}")
            if results:
                return "\n".join(results)
    except Exception as e:
        logger.warning(f"Free DuckDuckGo search failed: {e}")

    # 6. Firecrawl Search API (LAST FALLBACK)
    if settings.firecrawl_api_key:
        try:
            logger.info(f"Free engines yielded no results, using Firecrawl fallback search for query: {query}")
            response = await firecrawl_rotator.execute_request(
                "POST",
                "/search",
                json={"query": query, "limit": max_items, "lang": "en", "scrapeOptions": {"formats": ["markdown"]}}
            )
            data = response.get("data", []) or response.get("results", [])
            if data:
                results = []
                for item in data[:max_items]:
                    title = item.get("title", "No Title")
                    url = item.get("url", "No URL")
                    snippet = item.get("markdown", "")[:1000] if for_research else item.get("description", "")[:300]
                    results.append(f"### {title}\nURL: {url}\n{snippet}\n")
                return "\n".join(results)
        except Exception as e:
            logger.error(f"Firecrawl search fallback failed: {e}")

    return f"No search results found for '{query}'."


async def _jina_search(query: str, max_items: int = 5) -> str:
    """Free Jina AI Search API (https://s.jina.ai/). Returns clean Markdown search results."""
    import urllib.parse
    client = _get_firecrawl_client()
    url = f"https://s.jina.ai/{urllib.parse.quote(query)}"
    headers = {"Accept": "application/json", "X-No-Cache": "true"}
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            data = resp.json()
            items = data.get("data", [])
            results = []
            for item in items[:max_items]:
                title = item.get("title", "No Title")
                item_url = item.get("url", "No URL")
                content = item.get("content", "") or item.get("description", "")
                results.append(f"### {title}\nURL: {item_url}\n{content[:1500]}\n")
            if results:
                return "\n".join(results)
        except Exception:
            text = resp.text
            if text and len(text) > 50:
                return text[:10000]
    return ""


async def _searxng_search(query: str, max_items: int = 5) -> str:
    """SearXNG Meta-Search API (Self-hosted or Public instance)."""
    import os
    searxng_url = os.getenv("SEARXNG_URL", "https://searx.be").rstrip("/")
    client = _get_firecrawl_client()
    try:
        resp = await client.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json", "language": "en"},
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("results", [])
            results = []
            for item in items[:max_items]:
                title = item.get("title", "No Title")
                item_url = item.get("url", "No URL")
                snippet = item.get("content", "")
                results.append(f"### {title}\nURL: {item_url}\n{snippet}\n")
            if results:
                return "\n".join(results)
    except Exception as err:
        logger.warning(f"SearXNG search failed: {err}")
    return ""


async def scrape_page(url: str) -> str:
    """Scrape a web page and convert it into clean markdown format.

    Priority Order:
    1. Free Jina AI Reader API (r.jina.ai)
    2. Free Readability Article Content Scanner
    3. Free Crawl4AI / Playwright Headless Browser
    4. Free Google Web Cache Text-Only Proxy Scanner
    5. Free Rotated User-Agent Browser Scanner (Chrome/Safari/Firefox headers)
    6. Free BeautifulSoup & Markdownify Semantic HTML Parser
    7. Firecrawl Scrape API (Last Fallback, used only if configured & free scrapers fail)
    """
    # 1. Free Jina AI Reader API (https://r.jina.ai/{url})
    try:
        client = _get_firecrawl_client()
        jina_url = f"https://r.jina.ai/{url}"
        resp = await client.get(jina_url, headers={"X-No-Cache": "true"})
        if resp.status_code == 200 and resp.text and len(resp.text) > 50:
            logger.info(f"Successfully scraped URL via Jina Reader: {url}")
            return resp.text[:15000]
    except Exception as e:
        logger.warning(f"Jina Reader scrape failed for {url}: {e}")

    # 2. Free Readability Article Content Scanner
    try:
        readability_text = await _readability_scrape(url)
        if readability_text and len(readability_text.strip()) > 50:
            logger.info(f"Successfully scraped URL via Readability Scanner: {url}")
            return readability_text[:15000]
    except Exception as e:
        logger.warning(f"Readability scrape failed for {url}: {e}")

    # 3. Crawl4AI / Playwright Headless Browser for JS rendering
    try:
        crawl_text = await _crawl4ai_scrape(url)
        if crawl_text and len(crawl_text.strip()) > 50:
            logger.info(f"Successfully scraped URL via Crawl4AI / Playwright: {url}")
            return crawl_text[:15000]
    except Exception as e:
        logger.warning(f"Crawl4AI / Playwright scrape failed for {url}: {e}")

    # 4. Free Google Web Cache Text-Only Proxy Scanner
    try:
        cache_text = await _google_cache_scrape(url)
        if cache_text and len(cache_text.strip()) > 50:
            logger.info(f"Successfully scraped URL via Google Cache Scanner: {url}")
            return cache_text[:15000]
    except Exception as e:
        logger.warning(f"Google Cache scrape failed for {url}: {e}")

    # 5. Free Rotated User-Agent Browser Scanner
    try:
        browser_text = await _rotated_user_agent_scrape(url)
        if browser_text and len(browser_text.strip()) > 50:
            logger.info(f"Successfully scraped URL via Rotated User-Agent Scanner: {url}")
            return browser_text[:15000]
    except Exception as e:
        logger.warning(f"Rotated User-Agent scrape failed for {url}: {e}")

    # 6. Free Wayback Machine Archive Proxy Scanner
    try:
        archive_text = await _wayback_archive_scrape(url)
        if archive_text and len(archive_text.strip()) > 50:
            logger.info(f"Successfully scraped URL via Wayback Archive Scanner: {url}")
            return archive_text[:15000]
    except Exception as e:
        logger.warning(f"Wayback Archive scrape failed for {url}: {e}")

    # 6. Free BeautifulSoup & Markdownify Semantic HTML Parser Fallback
    try:
        client = _get_firecrawl_client()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "svg", "noscript", "iframe"]):
                tag.decompose()
            main = soup.find("main") or soup.find("article") or soup.body or soup
            paragraphs = []
            for element in main.find_all(["h1", "h2", "h3", "p", "li"]):
                txt = element.get_text(strip=True)
                if len(txt) > 20:
                    if element.name in ["h1", "h2", "h3"]:
                        paragraphs.append(f"\n### {txt}\n")
                    elif element.name == "li":
                        paragraphs.append(f"- {txt}")
                    else:
                        paragraphs.append(txt)
            clean_text = "\n\n".join(paragraphs).strip()
            if clean_text and len(clean_text) > 50:
                logger.info(f"Successfully scraped URL via BeautifulSoup: {url}")
                return clean_text[:15000]
    except Exception as e:
        logger.warning(f"BeautifulSoup scrape failed for {url}: {e}")

    # 7. Firecrawl Scrape API (LAST FALLBACK)
    if settings.firecrawl_api_key:
        try:
            logger.info(f"Free scrapers failed, using Firecrawl fallback to scrape URL: {url}")
            response = await firecrawl_rotator.execute_request(
                "POST",
                "/scrape",
                json={"url": url, "formats": ["markdown"], "onlyMainContent": True}
            )
            markdown = response.get("data", {}).get("markdown", "")
            if markdown:
                return markdown[:15000]
        except Exception as e:
            logger.error(f"Firecrawl fallback scrape failed for {url}: {e}")

    return "Error: Could not scrape page content."


async def _crawl4ai_scrape(url: str) -> str:
    """Scrape JS-rendered web pages using Crawl4AI or Playwright headless browser."""
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler(verbose=False) as crawler:
            res = await crawler.arun(url=url)
            if res and hasattr(res, "markdown") and res.markdown:
                return res.markdown[:15000]
    except Exception as e:
        logger.warning(f"Crawl4AI failed: {e}")

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            text = await page.inner_text("body")
            await browser.close()
            if text:
                return text[:15000]
    except Exception as e:
        logger.warning(f"Stealth Playwright failed: {e}")

    # Fallback to free CORS Proxy anti-bot bypasser
    try:
        proxy_text = await _cors_proxy_scrape(url)
        if proxy_text and len(proxy_text.strip()) > 50:
            logger.info(f"Successfully bypassed anti-bot via CORS Proxy: {url}")
            return proxy_text[:15000]
    except Exception as e:
        logger.warning(f"CORS proxy bypass failed for {url}: {e}")

    return ""


async def _readability_scrape(url: str) -> Optional[str]:
    """Extract clean main body content using Readability algorithm."""
    try:
        client = _get_firecrawl_client()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code == 200 and resp.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
                element.decompose()
            article = soup.find("article") or soup.find("main") or soup.find("div", class_=lambda c: c and ("content" in c or "body" in c or "post" in c))
            target = article if article else soup.body
            if target:
                text_blocks = [p.get_text(strip=True) for p in target.find_all(["p", "h1", "h2", "h3", "li"]) if len(p.get_text(strip=True)) > 25]
                if text_blocks:
                    return "\n\n".join(text_blocks)
    except Exception as e:
        logger.warning(f"Readability extractor error: {e}")
    return None


async def _google_cache_scrape(url: str) -> Optional[str]:
    """Fetch text-only cached version from Google Web Cache proxy."""
    try:
        client = _get_firecrawl_client()
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}&strip=1"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = await client.get(cache_url, headers=headers, follow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 100:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.warning(f"Google cache scraper error: {e}")
    return None


async def _rotated_user_agent_scrape(url: str) -> Optional[str]:
    """Scrape web pages using rotated desktop/mobile user-agents and browser headers."""
    import random
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    ]
    ua = random.choice(user_agents)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Referer": "https://www.google.com/",
    }
    try:
        client = _get_firecrawl_client()
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code == 200 and resp.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for el in soup(["script", "style", "nav", "footer", "header", "svg", "noscript", "iframe", "form"]):
                el.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.splitlines() if len(l.strip()) > 15]
            if lines:
                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Rotated UA scraper error: {e}")
    return None


async def _wikipedia_search(query: str) -> Optional[str]:
    """Search Wikipedia API for structured encyclopedic data."""
    try:
        client = _get_firecrawl_client()
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": 3,
        }
        resp = await client.get(url, params=params, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            search_items = data.get("query", {}).get("search", [])
            if search_items:
                results = []
                for item in search_items:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                    page_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    results.append(f"### [Wikipedia] {title}\nURL: {page_url}\n{snippet}...\n")
                return "\n".join(results)
    except Exception as e:
        logger.warning(f"Wikipedia API search error: {e}")
    return None


async def _arxiv_search(query: str) -> Optional[str]:
    """Search ArXiv API for scientific & academic research papers."""
    try:
        client = _get_firecrawl_client()
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 3,
        }
        resp = await client.get(url, params=params, follow_redirects=True)
        if resp.status_code == 200 and "<entry>" in resp.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "xml")
            entries = soup.find_all("entry")
            results = []
            for entry in entries:
                title_tag = entry.find("title")
                summary_tag = entry.find("summary")
                id_tag = entry.find("id")
                title = title_tag.get_text(strip=True) if title_tag else "Paper"
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                paper_url = id_tag.get_text(strip=True) if id_tag else ""
                results.append(f"### [ArXiv Paper] {title}\nURL: {paper_url}\n{summary[:400]}...\n")
            if results:
                return "\n".join(results)
    except Exception as e:
        logger.warning(f"ArXiv API search error: {e}")
    return None


async def _wayback_archive_scrape(url: str) -> Optional[str]:
    """Scrape web page from Wayback Machine Archive (Archive.org) snapshot."""
    try:
        client = _get_firecrawl_client()
        api_url = f"https://archive.org/wayback/available?url={url}"
        resp = await client.get(api_url)
        if resp.status_code == 200:
            data = resp.json()
            snapshots = data.get("archived_snapshots", {})
            closest = snapshots.get("closest", {})
            snapshot_url = closest.get("url")
            if snapshot_url:
                page_resp = await client.get(snapshot_url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
                if page_resp.status_code == 200 and page_resp.text:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(page_resp.text, "html.parser")
                    for el in soup(["script", "style", "nav", "footer", "header"]):
                        el.decompose()
                    return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.warning(f"Wayback Archive scrape error: {e}")
    return None


async def _cors_proxy_scrape(url: str) -> Optional[str]:
    """Bypass Cloudflare / Anti-Bot protection using free CORS proxy bridges."""
    import urllib.parse
    client = _get_firecrawl_client()
    encoded = urllib.parse.quote(url, safe="")
    proxies = [
        f"https://corsproxy.io/?{encoded}",
        f"https://api.allorigins.win/raw?url={encoded}",
    ]
    for proxy_url in proxies:
        try:
            resp = await client.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=12.0)
            if resp.status_code == 200 and resp.text and len(resp.text) > 100:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for el in soup(["script", "style", "nav", "footer", "header", "svg", "noscript", "iframe", "form"]):
                    el.decompose()
                text = soup.get_text(separator="\n", strip=True)
                if text and len(text) > 50:
                    return text[:15000]
        except Exception as err:
            logger.warning(f"CORS proxy scraper error ({proxy_url}): {err}")
    return None



async def find_user_access_token(user_id: str) -> str:
    """Retrieve the user's Google Drive access token from the database.

    Tries by MongoDB ObjectId first, then by email as fallback.
    The ADK receives user_id as an ObjectId string from the session.
    """
    from src.models.user import User

    # Try by MongoDB _id first (most common case)
    try:
        from beanie import PydanticObjectId
        PydanticObjectId(user_id)
        user = await User.get(user_id)
        if user and user.access_token:
            return user.access_token
    except Exception:
        pass

    # Fallback: try by email
    try:
        user = await User.find_one(User.email == user_id)
        if user and user.access_token:
            return user.access_token
    except Exception:
        pass

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


async def drive_read_file(user_id: str = "default", file_id_or_name: str = "") -> str:
    """Read the full content of a Google Drive file by ID or name to inspect, analyze, or summarize it.

    Args:
        user_id: The user ID or email
        file_id_or_name: The file ID, file name, or search keyword for the file in Drive

    Returns:
        Extracted text content of the file or message
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

        files = await drive_service.list_files(access_token=access_token, page_size=100)
        if not files:
            return "Your Google Drive is empty."

        target_file = None
        clean_target = (file_id_or_name or "").strip()

        # 1. Exact ID match
        for f in files:
            if f.get("id") == clean_target:
                target_file = f
                break

        # 2. Exact name match
        if not target_file and clean_target:
            for f in files:
                if (f.get("name") or "").casefold() == clean_target.casefold():
                    target_file = f
                    break

        # 3. Substring name match
        if not target_file and clean_target:
            for f in files:
                if clean_target.casefold() in (f.get("name") or "").casefold():
                    target_file = f
                    break

        if not target_file:
            file_names = [f"• {f.get('name')} (ID: {f.get('id')})" for f in files[:20]]
            return (
                f"Could not find file matching '{file_id_or_name}' in Google Drive.\n"
                f"Available files in Drive:\n" + "\n".join(file_names)
            )

        file_id = target_file.get("id")
        file_name = target_file.get("name", "Untitled")

        text, info = await drive_service.read_and_parse_file_content(access_token=access_token, file_id=file_id)

        if not text.strip():
            return f"File '{file_name}' was found, but no readable text content could be extracted."

        MAX_CHARS = 30000
        truncated = False
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
            truncated = True

        result = (
            f"=== Google Drive File Content ===\n"
            f"Name: {file_name}\n"
            f"ID: {file_id}\n"
            f"Type: {info.get('mimeType', 'unknown')}\n\n"
            f"--- Content ---\n"
            f"{text}"
        )
        if truncated:
            result += "\n\n[Note: Content was truncated to fit context limits.]"

        return result
    except Exception as e:
        logger.error(f"Drive read tool error: {e}")
        return f"Failed to read Drive file: {e}"


async def contacts_list(user_id: str = "default", query: str = "") -> str:
    """List or search Google Contacts for the authenticated user.

    Args:
        user_id: The user ID or email
        query: Optional search keyword for contact name, email, or phone

    Returns:
        JSON string of matching contacts
    """
    from src.services.contacts.service import contacts_service

    try:
        access_token = await find_user_access_token(user_id)
        if not access_token:
            return (
                "You need to connect your Google account first. "
                "Please go to Settings > Integrations and sign in with Google to grant contacts access."
            )

        contacts = await contacts_service.list_contacts(access_token=access_token, query=query)
        if not contacts:
            return f'No contacts found matching "{query}".' if query else "Your Google Contacts list is empty."

        return json.dumps(contacts, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Contacts list tool error: {e}")
        return f"Failed to list contacts: {e}"


# Export all tools as FunctionTool instances for ADK agents
knowledge_search_tool = FunctionTool(func=knowledge_search)
memory_store_tool = FunctionTool(func=memory_store)
memory_search_tool = FunctionTool(func=memory_search)
calculator_tool = FunctionTool(func=calculator)
web_search_tool = FunctionTool(func=web_search)
scrape_page_tool = FunctionTool(func=scrape_page)
drive_list_tool = FunctionTool(func=drive_list)
drive_read_tool = FunctionTool(func=drive_read_file)
drive_upload_tool = FunctionTool(func=drive_upload)
drive_delete_tool = FunctionTool(func=drive_delete)
contacts_list_tool = FunctionTool(func=contacts_list)

