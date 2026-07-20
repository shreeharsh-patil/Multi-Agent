from unittest.mock import AsyncMock, patch

import pytest

from src.agents.calendar.agent import CalendarAgent


@pytest.mark.asyncio
async def test_calendar_list_includes_available_event_details():
    events = [
        {
            "summary": "Project review",
            "start": "2026-07-21T10:00:00Z",
            "end": "2026-07-21T11:00:00Z",
            "description": "Review the launch checklist.",
            "location": "Conference room 2",
            "calendar_name": "Work",
            "attendees": [
                {"email": "alex@example.com", "name": "Alex", "response": "accepted", "self": False},
            ],
            "organizer": {"email": "owner@example.com", "name": "Owner", "self": True},
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "link": "https://calendar.google.com/event?id=event-1",
        }
    ]

    with (
        patch("src.services.llm.llm_service.generate", new=AsyncMock(return_value='{"action":"list","time_min":null,"time_max":null}')),
        patch("src.services.calendar.calendar_service.list_events", new=AsyncMock(return_value=events)) as list_events,
    ):
        result = await CalendarAgent().execute("tell me about my calendar", {"google_access_token": "token"})

    assert result.success is True
    assert "Project review" in result.output
    assert "Review the launch checklist." in result.output
    assert "Conference room 2" in result.output
    assert "**Calendar:** Work" in result.output
    assert "Alex (accepted)" in result.output
    assert "https://meet.google.com/abc-defg-hij" in result.output
    list_events.assert_awaited_once_with("token", None, None, limit=10, query=None)


@pytest.mark.asyncio
async def test_calendar_details_searches_by_event_title():
    with (
        patch(
            "src.services.llm.llm_service.generate",
            new=AsyncMock(return_value='{"action":"details","query":"dentist","time_min":null,"time_max":null}'),
        ),
        patch("src.services.calendar.calendar_service.list_events", new=AsyncMock(return_value=[])) as list_events,
    ):
        result = await CalendarAgent().execute("give me details of my dentist event", {"google_access_token": "token"})

    assert result.success is True
    assert 'matching "dentist"' in result.output
    list_events.assert_awaited_once_with("token", None, None, limit=10, query="dentist")


def test_calendar_formats_birthdays_with_their_source_calendar():
    output = CalendarAgent._format_event(
        {
            "summary": "Sam's birthday",
            "start": "2026-08-03",
            "end": "2026-08-04",
            "event_type": "birthday",
            "calendar_name": "Birthdays",
        }
    )

    assert "**Type:** Birthday" in output
    assert "**Calendar:** Birthdays" in output
