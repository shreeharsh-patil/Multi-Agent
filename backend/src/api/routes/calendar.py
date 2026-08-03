from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from src.services.calendar.service import calendar_service
from src.adk.tools import find_user_access_token
from src.utils.logger import logger

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CreateEventRequest(BaseModel):
    summary: str = Field(..., description="Event title")
    start: str = Field(..., description="Start time ISO timestamp")
    end: Optional[str] = Field(None, description="End time ISO timestamp")
    description: Optional[str] = ""
    location: Optional[str] = ""
    attendees: Optional[List[str]] = []
    generate_meet_link: Optional[bool] = False


async def _resolve_token(
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    access_token: Optional[str] = Header(None, alias="X-Google-Access-Token"),
    refresh_token: Optional[str] = Header(None, alias="X-Google-Refresh-Token"),
) -> tuple[str, str]:
    token = access_token or ""
    r_token = refresh_token or ""
    if not token and user_id:
        token = await find_user_access_token(user_id)
    return token, r_token


@router.get("/events")
async def list_calendar_events(
    time_min: Optional[str] = Query(None),
    time_max: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        events = await calendar_service.list_events(
            access_token=token,
            time_min=time_min,
            time_max=time_max,
            limit=limit,
            query=query,
            refresh_token=refresh_token,
        )
        return {"events": events, "count": len(events)}
    except Exception as exc:
        logger.error(f"Error listing calendar events: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/events")
async def create_calendar_event(
    body: CreateEventRequest,
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        event = await calendar_service.create_event(
            access_token=token,
            summary=body.summary,
            start=body.start,
            end=body.end or body.start,
            description=body.description or "",
            location=body.location or "",
            attendees=body.attendees,
            generate_meet_link=body.generate_meet_link or False,
            refresh_token=refresh_token,
        )
        return {"event": event, "success": True}
    except Exception as exc:
        logger.error(f"Error creating calendar event: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        await calendar_service.delete_event(
            access_token=token,
            event_id=event_id,
            refresh_token=refresh_token,
        )
        return {"success": True, "message": f"Event {event_id} deleted"}
    except Exception as exc:
        logger.error(f"Error deleting calendar event: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/availability")
async def check_calendar_availability(
    time_min: str = Query(...),
    time_max: str = Query(...),
    user_id: str = Query("default"),
    token_data: tuple[str, str] = Depends(_resolve_token),
):
    token, refresh_token = token_data
    if not token and user_id:
        token = await find_user_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar is not connected. Reconnect Google in Settings > Integrations."
        )

    try:
        result = await calendar_service.find_availability(
            access_token=token,
            time_min=time_min,
            time_max=time_max,
            refresh_token=refresh_token,
        )
        return result
    except Exception as exc:
        logger.error(f"Error checking calendar availability: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
