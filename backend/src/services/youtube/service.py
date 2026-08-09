import asyncio
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings
from src.utils.logger import logger


class YouTubeService:
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        kwargs: dict = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        credentials = Credentials(**kwargs)
        return await asyncio.to_thread(build, "youtube", "v3", credentials=credentials, cache_discovery=False)

    async def _search_with_api_key(self, query: str, max_results: int = 5) -> list[dict]:
        api_key = next((k.strip() for k in (settings.gemini_api_key or "").split(",") if k.strip()), "")
        if not api_key:
            return []
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?q={query}&part=snippet&type=video&maxResults={max_results}&key={api_key}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get('items', [])
                    return [{
                        "id": item['id']['videoId'],
                        "title": item['snippet']['title'],
                        "channel": item['snippet']['channelTitle'],
                        "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                    } for item in items if 'id' in item and 'videoId' in item['id']]
        except Exception as err:
            logger.warning(f"YouTube API Key search fallback failed: {err}")
        return []

    async def search_videos(self, access_token: str, query: str, max_results: int = 5, refresh_token: str = "") -> list[dict]:
        if access_token:
            try:
                service = await self._get_service(access_token, refresh_token)
                result = await asyncio.to_thread(lambda: service.search().list(q=query, part='snippet', type='video', maxResults=max_results).execute())
                items = result.get('items', [])
                return [{
                    "id": item['id']['videoId'],
                    "title": item['snippet']['title'],
                    "channel": item['snippet']['channelTitle'],
                    "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                } for item in items if 'id' in item and 'videoId' in item['id']]
            except Exception as oauth_err:
                logger.warning(f"YouTube OAuth search failed ({oauth_err}), attempting API Key fallback...")

        return await self._search_with_api_key(query, max_results)


youtube_service = YouTubeService()
