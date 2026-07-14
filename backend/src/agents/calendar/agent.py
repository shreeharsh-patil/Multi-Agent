import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult


class CalendarAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="calendar",
            name="Calendar Agent",
            description="Lists, creates, reschedules, and checks Google Calendar availability",
            icon="CalendarDays",
            capabilities=["list_events", "create_events", "availability", "reschedule"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.calendar import calendar_service

        token = context.get("google_access_token", "")
        if not token:
            return AgentResult(success=False, output="Connect Google Calendar in Settings before asking me to manage your schedule.", error="missing_google_calendar_token")

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a calendar command parser. Return ONLY valid JSON with keys: action, summary, "
                "start, end, event_id, description, location, attendees, time_min, time_max. "
                "action must be one of list, create, availability, reschedule. Use ISO 8601 UTC date-times. "
                "For list, use the requested range; if absent, use the next 7 days. Infer end as one hour after start when needed."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except (json.JSONDecodeError, AttributeError) as exc:
            return AgentResult(success=False, output="I couldn't understand that calendar request. Try asking to list, create, or reschedule an event.", error=str(exc))

        action = command.get("action", "list")
        try:
            if action == "list":
                events = await calendar_service.list_events(token, command.get("time_min"), command.get("time_max"))
                if not events:
                    return AgentResult(success=True, output="You have no events in that time range.")
                lines = [f"• {e['summary']} — {e['start']} to {e['end']}" for e in events]
                return AgentResult(success=True, output="Upcoming calendar events:\n" + "\n".join(lines))
            if action == "create":
                event = await calendar_service.create_event(token, command["summary"], command["start"], command["end"], command.get("description", ""), command.get("location", ""), command.get("attendees"))
                return AgentResult(success=True, output=f"Created “{event['summary']}” from {event['start']} to {event['end']}.\n{event.get('link', '')}")
            if action == "reschedule":
                event = await calendar_service.reschedule_event(token, command["event_id"], command["start"], command["end"])
                return AgentResult(success=True, output=f"Rescheduled “{event['summary']}” to {event['start']}–{event['end']}.\n{event.get('link', '')}")
            if action == "availability":
                availability = await calendar_service.find_availability(token, command["time_min"], command["time_max"])
                return AgentResult(success=True, output="That window is available." if availability["available"] else f"You already have {len(availability['busy'])} busy block(s) in that window.")
            return AgentResult(success=False, output="I can list, create, reschedule, or check availability for calendar events.", error="unsupported_calendar_action")
        except Exception as exc:
            return AgentResult(success=False, output=f"Calendar action failed: {exc}", error=str(exc))
