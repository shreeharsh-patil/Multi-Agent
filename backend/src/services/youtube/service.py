import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings

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

    async def search_videos(self, access_token: str, query: str, max_results: int = 5, refresh_token: str = "") -> list[dict]:
        service = await self._get_service(access_token, refresh_token)
        result = await asyncio.to_thread(lambda: service.search().list(q=query, part='snippet', type='video', maxResults=max_results).execute())
        items = result.get('items', [])
        return [{
            "id": item['id']['videoId'],
            "title": item['snippet']['title'],
            "channel": item['snippet']['channelTitle'],
            "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        } for item in items]

youtube_service = YouTubeService()
