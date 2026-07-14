import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.utils.logger import logger


class CalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    async def _get_service(self, access_token: str):
        if not access_token:
            raise ValueError("Google Calendar is not connected. Reconnect Google with Calendar access enabled.")
        credentials = Credentials(token=access_token)
        return await asyncio.to_thread(build, "calendar", "v3", credentials=credentials, cache_discovery=False)

    async def list_events(self, access_token: str, time_min: Optional[str] = None, time_max: Optional[str] = None, limit: int = 10) -> list[dict]:
        service = await self._get_service(access_token)
        now = datetime.now(timezone.utc)
        request = service.events().list(
            calendarId="primary",
            timeMin=time_min or now.isoformat(),
            timeMax=time_max,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime",
        )
        result = await asyncio.to_thread(request.execute)
        return [
            {
                "id": event.get("id"),
                "summary": event.get("summary", "Untitled event"),
                "description": event.get("description", ""),
                "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
                "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
                "location": event.get("location", ""),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
                "link": event.get("htmlLink"),
            }
            for event in result.get("items", [])
        ]

    async def create_event(self, access_token: str, summary: str, start: str, end: str, description: str = "", location: str = "", attendees: Optional[list[str]] = None) -> dict:
        service = await self._get_service(access_token)
        body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }
        if attendees:
            body["attendees"] = [{"email": email} for email in attendees]
        request = service.events().insert(calendarId="primary", body=body, sendUpdates="all")
        event = await asyncio.to_thread(request.execute)
        return {"id": event.get("id"), "summary": event.get("summary"), "start": start, "end": end, "link": event.get("htmlLink")}

    async def reschedule_event(self, access_token: str, event_id: str, start: str, end: str) -> dict:
        service = await self._get_service(access_token)
        existing = await asyncio.to_thread(lambda: service.events().get(calendarId="primary", eventId=event_id).execute())
        existing["start"] = {"dateTime": start, "timeZone": "UTC"}
        existing["end"] = {"dateTime": end, "timeZone": "UTC"}
        updated = await asyncio.to_thread(lambda: service.events().update(calendarId="primary", eventId=event_id, body=existing, sendUpdates="all").execute())
        return {"id": updated.get("id"), "summary": updated.get("summary"), "start": start, "end": end, "link": updated.get("htmlLink")}

    async def find_availability(self, access_token: str, time_min: str, time_max: str) -> dict:
        service = await self._get_service(access_token)
        request = service.freebusy().query(body={"timeMin": time_min, "timeMax": time_max, "items": [{"id": "primary"}]})
        result = await asyncio.to_thread(request.execute)
        busy = result.get("calendars", {}).get("primary", {}).get("busy", [])
        return {"timeMin": time_min, "timeMax": time_max, "busy": busy, "available": not busy}


calendar_service = CalendarService()
