import asyncio
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings

class TasksService:
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        if not access_token:
            raise ValueError("Google Tasks is not connected.")
        kwargs: dict = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        credentials = Credentials(**kwargs)
        return await asyncio.to_thread(build, "tasks", "v1", credentials=credentials, cache_discovery=False)

    async def list_tasks(self, access_token: str, refresh_token: str = "") -> list[dict]:
        service = await self._get_service(access_token, refresh_token)
        result = await asyncio.to_thread(lambda: service.tasks().list(tasklist='@default').execute())
        items = result.get('items', [])
        return [{"id": t.get("id"), "title": t.get("title"), "status": t.get("status"), "due": t.get("due")} for t in items]

    async def create_task(self, access_token: str, title: str, due: Optional[str] = None, refresh_token: str = "") -> dict:
        service = await self._get_service(access_token, refresh_token)
        body = {"title": title}
        if due:
            body["due"] = due
        task = await asyncio.to_thread(lambda: service.tasks().insert(tasklist='@default', body=body).execute())
        return {"id": task.get("id"), "title": task.get("title"), "status": task.get("status")}

tasks_service = TasksService()
