import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult


class CalendarAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="calendar",
            name="Calendar Agent",
            description="Lists, creates, updates, deletes, and checks Google Calendar availability",
            icon="CalendarDays",
            capabilities=["list_events", "event_details", "create_events", "availability", "update_events", "delete_events"],
        )

    @staticmethod
    def _format_event(event: dict) -> str:
        lines = [
            f"### {event.get('summary') or 'Untitled event'}",
            f"- **When:** {event.get('start') or 'Unknown'} to {event.get('end') or 'Unknown'}",
        ]
        if event.get("event_type") == "birthday":
            lines.append("- **Type:** Birthday")
        if event.get("calendar_name"):
            lines.append(f"- **Calendar:** {event['calendar_name']}")
        if event.get("location"):
            lines.append(f"- **Location:** {event['location']}")
        if event.get("description"):
            lines.append(f"- **Description:** {event['description']}")

        organizer = event.get("organizer") or {}
        organizer_label = organizer.get("name") or organizer.get("email")
        if organizer_label and not organizer.get("self"):
            lines.append(f"- **Organizer:** {organizer_label}")

        attendees = []
        for attendee in event.get("attendees") or []:
            if isinstance(attendee, str):
                attendees.append(attendee)
                continue
            if attendee.get("self"):
                continue
            label = attendee.get("name") or attendee.get("email")
            if label:
                response = (attendee.get("response") or "needsAction").replace("needsAction", "awaiting response")
                attendees.append(f"{label} ({response})")
        if attendees:
            lines.append(f"- **Attendees:** {', '.join(attendees)}")

        meeting_link = event.get("meeting_link")
        if meeting_link:
            lines.append(f"- **Meeting:** {meeting_link}")
        if event.get("link"):
            lines.append(f"- **Open event:** {event['link']}")
        return "\n".join(lines)

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.calendar import calendar_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            token = await find_user_access_token(context["user_id"])

        if not token:
            return AgentResult(success=False, output="Connect Google Calendar in Settings before asking me to manage your schedule.", error="missing_google_calendar_token")

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a calendar command parser. Return ONLY valid JSON with keys: action, query, summary, "
                "start, end, event_id, description, location, attendees, time_min, time_max, generate_meet_link. "
                "action must be one of list, details, create, availability, update, delete. Use details when the "
                "user asks about one named event and put its title or identifying words in query. Use update to reschedule, "
                "change title, description, or location. Use delete to cancel an event. Use ISO 8601 "
                "UTC date-times. Calendar listings include primary, birthday, holiday, shared, and subscribed "
                "calendars. For list or details, use the requested range; when absent, leave time_min and time_max "
                "null. Infer end as one hour after start when needed. Set generate_meet_link to true if the user asks for a video or meet link."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except (json.JSONDecodeError, AttributeError) as exc:
            return AgentResult(success=False, output="I couldn't understand that calendar request. Try asking to list, create, or reschedule an event.", error=str(exc))

        action = command.get("action", "list")
        try:
            if action in {"list", "details"}:
                query = (command.get("query") or "").strip() if action == "details" else None
                events = await calendar_service.list_events(
                    token,
                    command.get("time_min"),
                    command.get("time_max"),
                    limit=10,
                    query=query or None,
                    refresh_token=refresh_token,
                )
                if not events:
                    message = f'I could not find a calendar event matching "{query}".' if query else "You have no events in that time range."
                    return AgentResult(success=True, output=message)
                heading = "Matching event details:" if action == "details" else "Upcoming calendar events:"
                return AgentResult(
                    success=True,
                    output=heading + "\n\n" + "\n\n".join(self._format_event(event) for event in events),
                )
            if action == "create":
                event = await calendar_service.create_event(token, command["summary"], command["start"], command["end"], command.get("description", ""), command.get("location", ""), command.get("attendees"), command.get("generate_meet_link", False), refresh_token=refresh_token)
                msg = f"Created “{event['summary']}” from {event['start']} to {event['end']}.\n{event.get('link', '')}"
                if event.get("meeting_link"):
                    msg += f"\nMeeting Link: {event['meeting_link']}"
                return AgentResult(success=True, output=msg)
            if action in {"update", "reschedule"}:
                event = await calendar_service.update_event(token, command["event_id"], command.get("summary"), command.get("start"), command.get("end"), command.get("description"), command.get("location"), command.get("attendees"), refresh_token=refresh_token)
                return AgentResult(success=True, output=f"Updated “{event['summary']}”.\n{event.get('link', '')}")
            if action == "delete":
                await calendar_service.delete_event(token, command["event_id"], refresh_token=refresh_token)
                return AgentResult(success=True, output="Event cancelled successfully.")
            if action == "availability":
                availability = await calendar_service.find_availability(token, command["time_min"], command["time_max"], refresh_token=refresh_token)
                return AgentResult(success=True, output="That window is available." if availability["available"] else f"You already have {len(availability['busy'])} busy block(s) in that window.")
            return AgentResult(success=False, output="I can list, create, update, delete, or check availability for calendar events.", error="unsupported_calendar_action")
        except Exception as exc:
            return AgentResult(success=False, output=f"Calendar action failed: {exc}", error=str(exc))
