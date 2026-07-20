import asyncio
from datetime import datetime, timezone
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings
from src.utils.logger import logger


class CalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    async def _get_service(self, access_token: str, refresh_token: str = ""):
        """Build a Google Calendar service authenticated with the given access token.

        When *refresh_token* is provided together with the OAuth client credentials
        the credentials can auto-refresh after expiry, avoiding 401 → crash cycles.
        """
        if not access_token:
            raise ValueError("Google Calendar is not connected. Reconnect Google with Calendar access enabled.")
        kwargs: dict = {"token": access_token}
        if refresh_token and settings.google_client_id and settings.google_client_secret:
            kwargs.update(
                refresh_token=refresh_token,
                token_uri=self.TOKEN_URI,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
        elif refresh_token and not (settings.google_client_id and settings.google_client_secret):
            logger.warning(
                "Refresh token provided but GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not configured. "
                "The Calendar access token will not be refreshed when it expires. "
                "Set these environment variables to enable automatic token refresh."
            )
        credentials = Credentials(**kwargs)
        return await asyncio.to_thread(build, "calendar", "v3", credentials=credentials, cache_discovery=False)

    async def list_events(
        self,
        access_token: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        limit: int = 10,
        query: Optional[str] = None,
        refresh_token: str = "",
    ) -> list[dict]:
        service = await self._get_service(access_token, refresh_token)
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

    async def create_event(self, access_token: str, summary: str, start: str, end: str, description: str = "", location: str = "", attendees: Optional[list[str]] = None, generate_meet_link: bool = False, refresh_token: str = "") -> dict:
        service = await self._get_service(access_token, refresh_token)
        body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }
        if attendees:
            body["attendees"] = [{"email": email} for email in attendees]
            
        if generate_meet_link:
            import uuid
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
            request = service.events().insert(calendarId="primary", body=body, sendUpdates="all", conferenceDataVersion=1)
        else:
            request = service.events().insert(calendarId="primary", body=body, sendUpdates="all")
            
        event = await asyncio.to_thread(request.execute)
        return {"id": event.get("id"), "summary": event.get("summary"), "start": start, "end": end, "link": event.get("htmlLink"), "meeting_link": event.get("hangoutLink", "")}

    async def update_event(self, access_token: str, event_id: str, summary: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None, attendees: Optional[list[str]] = None, refresh_token: str = "") -> dict:
        service = await self._get_service(access_token, refresh_token)
        existing = await asyncio.to_thread(lambda: service.events().get(calendarId="primary", eventId=event_id).execute())
        
        if summary is not None:
            existing["summary"] = summary
        if start is not None:
            existing["start"] = {"dateTime": start, "timeZone": "UTC"}
        if end is not None:
            existing["end"] = {"dateTime": end, "timeZone": "UTC"}
        if description is not None:
            existing["description"] = description
        if location is not None:
            existing["location"] = location
        if attendees is not None:
            existing["attendees"] = [{"email": email} for email in attendees]
            
        updated = await asyncio.to_thread(lambda: service.events().update(calendarId="primary", eventId=event_id, body=existing, sendUpdates="all").execute())
        return {"id": updated.get("id"), "summary": updated.get("summary"), "start": updated.get("start", {}).get("dateTime"), "end": updated.get("end", {}).get("dateTime"), "link": updated.get("htmlLink")}

    async def delete_event(self, access_token: str, event_id: str, refresh_token: str = "") -> bool:
        service = await self._get_service(access_token, refresh_token)
        await asyncio.to_thread(lambda: service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute())
        return True

    async def find_availability(self, access_token: str, time_min: str, time_max: str, refresh_token: str = "") -> dict:
        service = await self._get_service(access_token, refresh_token)
        request = service.freebusy().query(body={"timeMin": time_min, "timeMax": time_max, "items": [{"id": "primary"}]})
        result = await asyncio.to_thread(request.execute)
        busy = result.get("calendars", {}).get("primary", {}).get("busy", [])
        return {"timeMin": time_min, "timeMax": time_max, "busy": busy, "available": not busy}


calendar_service = CalendarService()
