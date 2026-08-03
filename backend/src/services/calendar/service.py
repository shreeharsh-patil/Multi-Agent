import asyncio
from datetime import datetime, timezone
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import settings
from src.utils.logger import logger


def normalize_rfc3339(dt_val: Optional[str], default_dt: Optional[datetime] = None) -> Optional[str]:
    """Convert arbitrary date/time strings into clean RFC3339 ISO timestamps for Google Calendar."""
    if not dt_val or not isinstance(dt_val, str) or not dt_val.strip():
        return default_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if default_dt else None

    dt_str = dt_val.strip()
    try:
        from dateutil import parser
        parsed = parser.parse(dt_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as exc:
        logger.warning("Could not parse date string %r: %s", dt_str, exc)

    if default_dt:
        return default_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt_str


class CalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_URI = "https://oauth2.googleapis.com/token"


    async def _get_service(self, access_token: str, refresh_token: str = ""):
        """Build a Google Calendar service authenticated with the given access token."""
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
                "Refresh token provided but GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not configured."
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

        t_min = normalize_rfc3339(time_min, default_dt=now)
        t_max = normalize_rfc3339(time_max) if time_max else None

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
                timeMin=t_min,
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime",
            )
            if t_max:
                request_params["timeMax"] = t_max
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

    async def create_event(
        self,
        access_token: str,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        attendees: Optional[list[str]] = None,
        generate_meet_link: bool = False,
        refresh_token: str = "",
    ) -> dict:
        service = await self._get_service(access_token, refresh_token)
        now = datetime.now(timezone.utc)

        start_rfc = normalize_rfc3339(start, default_dt=now)
        end_rfc = normalize_rfc3339(end)
        if not end_rfc or end_rfc <= start_rfc:
            # Default end to 1 hour after start
            try:
                from dateutil import parser
                from datetime import timedelta
                st_dt = parser.parse(start_rfc)
                end_rfc = (st_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                end_rfc = start_rfc

        body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_rfc, "timeZone": "UTC"},
            "end": {"dateTime": end_rfc, "timeZone": "UTC"},
        }
        if attendees:
            body["attendees"] = [{"email": email} for email in attendees if email and "@" in email]

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
        return {
            "id": event.get("id"),
            "summary": event.get("summary", summary),
            "start": start_rfc,
            "end": end_rfc,
            "link": event.get("htmlLink"),
            "meeting_link": event.get("hangoutLink", ""),
        }

    async def update_event(
        self,
        access_token: str,
        event_id: str,
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None,
        refresh_token: str = "",
    ) -> dict:
        service = await self._get_service(access_token, refresh_token)
        existing = await asyncio.to_thread(lambda: service.events().get(calendarId="primary", eventId=event_id).execute())

        if summary is not None:
            existing["summary"] = summary
        if start is not None:
            st_rfc = normalize_rfc3339(start)
            existing["start"] = {"dateTime": st_rfc, "timeZone": "UTC"}
        if end is not None:
            en_rfc = normalize_rfc3339(end)
            existing["end"] = {"dateTime": en_rfc, "timeZone": "UTC"}
        if description is not None:
            existing["description"] = description
        if location is not None:
            existing["location"] = location
        if attendees is not None:
            existing["attendees"] = [{"email": email} for email in attendees if email and "@" in email]

        updated = await asyncio.to_thread(lambda: service.events().update(calendarId="primary", eventId=event_id, body=existing, sendUpdates="all").execute())
        return {
            "id": updated.get("id"),
            "summary": updated.get("summary"),
            "start": updated.get("start", {}).get("dateTime"),
            "end": updated.get("end", {}).get("dateTime"),
            "link": updated.get("htmlLink"),
        }

    async def delete_event(self, access_token: str, event_id: str, refresh_token: str = "") -> bool:
        service = await self._get_service(access_token, refresh_token)
        await asyncio.to_thread(lambda: service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute())
        return True

    async def find_availability(self, access_token: str, time_min: str, time_max: str, refresh_token: str = "") -> dict:
        service = await self._get_service(access_token, refresh_token)
        now = datetime.now(timezone.utc)
        t_min = normalize_rfc3339(time_min, default_dt=now)
        t_max = normalize_rfc3339(time_max)
        request = service.freebusy().query(body={"timeMin": t_min, "timeMax": t_max, "items": [{"id": "primary"}]})
        result = await asyncio.to_thread(request.execute)
        busy = result.get("calendars", {}).get("primary", {}).get("busy", [])
        return {"timeMin": t_min, "timeMax": t_max, "busy": busy, "available": not busy}


calendar_service = CalendarService()

