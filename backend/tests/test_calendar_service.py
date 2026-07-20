from unittest.mock import MagicMock, patch

import pytest

from src.services.calendar.service import CalendarService


@pytest.mark.asyncio
async def test_list_events_combines_visible_calendars_and_sorts_globally():
    service = MagicMock()
    service.calendarList.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "primary", "summary": "Personal", "primary": True},
            {"id": "birthdays", "summary": "Birthdays"},
        ]
    }

    def list_events(**params):
        request = MagicMock()
        if params["calendarId"] == "primary":
            request.execute.return_value = {
                "items": [{"id": "meeting", "summary": "Meeting", "start": {"dateTime": "2026-08-04T10:00:00Z"}}]
            }
        else:
            request.execute.return_value = {
                "items": [
                    {
                        "id": "birthday",
                        "summary": "Sam's birthday",
                        "eventType": "birthday",
                        "birthdayProperties": {"type": "birthday"},
                        "start": {"date": "2026-08-03"},
                    }
                ]
            }
        return request

    service.events.return_value.list.side_effect = list_events
    calendar_service = CalendarService()

    with patch.object(calendar_service, "_get_service", return_value=service):
        events = await calendar_service.list_events("token", time_min="2026-08-01T00:00:00Z")

    assert [event["id"] for event in events] == ["birthday", "meeting"]
    assert events[0]["event_type"] == "birthday"
    assert events[0]["calendar_name"] == "Birthdays"
    service.calendarList.return_value.list.assert_called_once_with(maxResults=250, showHidden=False)
    assert service.events.return_value.list.call_count == 2
