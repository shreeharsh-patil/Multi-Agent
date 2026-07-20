import asyncio
from datetime import datetime, timezone
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

    async def list_events(
        self,
        access_token: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        limit: int = 10,
        query: Optional[str] = None,
    ) -> list[dict]:
        service = await self._get_service(access_token)
        now = datetime.now(timezone.utc)
        calendar_request = service.calendarList().list(maxResults=250, showHidden=False)
        calendar_result = await asyncio.to_thread(calendar_request.execute)
        calendars = calendar_result.get("items", [])
        if not calendars:
            calendars = [{"id": "primary", "summary": "Primary", "primary": True}]

        events = []
        failed_calendars = []
        for calendar in calendars:
            calendar_id = calendar.get("id")
            if not calendar_id:
                continue
            request_params = dict(
                calendarId=calendar_id,
                timeMin=time_min or now.isoformat(),
                timeMax=time_max,
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime",
            )
            if query:
                request_params["q"] = query
            try:
                result = await asyncio.to_thread(service.events().list(**request_params).execute)
            except Exception as exc:
                failed_calendars.append(exc)
                logger.warning("Could not read Google Calendar %s: %s", calendar_id, exc)
                continue

            for event in result.get("items", []):
                events.append(
                    {
                        "id": event.get("id"),
                        "summary": event.get("summary", "Untitled event"),
                        "description": event.get("description", ""),
                        "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
                        "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
                        "location": event.get("location", ""),
                        "attendees": [
                            {
                                "email": attendee.get("email", ""),
                                "name": attendee.get("displayName", ""),
                                "response": attendee.get("responseStatus", "needsAction"),
                                "self": attendee.get("self", False),
                            }
                            for attendee in event.get("attendees", [])
                        ],
                        "organizer": {
                            "email": event.get("organizer", {}).get("email", ""),
                            "name": event.get("organizer", {}).get("displayName", ""),
                            "self": event.get("organizer", {}).get("self", False),
                        },
                        "status": event.get("status", "confirmed"),
                        "event_type": event.get("eventType", "default"),
                        "birthday": event.get("birthdayProperties", {}),
                        "calendar_id": calendar_id,
                        "calendar_name": calendar.get("summaryOverride") or calendar.get("summary") or "Calendar",
                        "calendar_color": calendar.get("backgroundColor", ""),
                        "meeting_link": event.get("hangoutLink", ""),
                        "link": event.get("htmlLink"),
                    }
                )

        if not events and failed_calendars and len(failed_calendars) == len(calendars):
            raise failed_calendars[0]
        events.sort(key=lambda event: event.get("start") or "9999-12-31")
        return events[:limit]

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
