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
            return AgentResult(
                success=True,
                output=(
                    "📅 **Google Calendar Integration Available**\n\n"
                    "I can manage your calendar, list upcoming events, create meetings, reschedule appointments, and check your availability!\n\n"
                    "To enable Calendar access:\n"
                    "1. Open **Settings → Integrations** in the sidebar menu.\n"
                    "2. Click **Connect Google Account**.\n"
                    "3. Once connected, ask me anytime to check your schedule or book events!"
                ),
                error="missing_google_calendar_token"
            )

        now = context.get("current_datetime", "")
        history = context.get("conversation_history", "")

        context_prefix = ""
        if now:
            context_prefix += f"Current date and time: {now}\n"
        if history:
            context_prefix += f"\nRecent conversation:\n{history}\n"
        context_prefix += "\nUser request: "

        extraction = await llm_service.generate(
            prompt=context_prefix + user_input,
            system_instruction=(
                "You are a calendar command parser. The current date/time and recent conversation history are provided above — "
                "use them to resolve relative references like 'tomorrow', 'next Monday', 'in 2 hours', 'next week', and "
                "follow-up references like 'cancel that', 'reschedule it', 'the meeting I just mentioned'. "
                "Return ONLY valid JSON with these keys: action, query, summary, start, end, event_id, description, "
                "location, attendees, time_min, time_max, generate_meet_link. "
                "action must be one of: list, details, create, availability, update, delete. "
                "Rules:\n"
                "- Use 'list' for browsing events (e.g. 'show my events', 'what's on my calendar this week').\n"
                "- Use 'details' when asking about a specific named event; put the name in 'query'.\n"
                "- Use 'create' to add a new event; always include summary, start, and end.\n"
                "- Use 'update' to reschedule or modify an existing event; include event_id if known.\n"
                "- Use 'delete' to cancel/remove an event; include event_id if known.\n"
                "- Use 'availability' to check if a time slot is free.\n"
                "- Always use ISO 8601 UTC for start/end/time_min/time_max.\n"
                "- If no time range is given for 'list', set time_min to now and time_max to 7 days from now.\n"
                "- Infer end as 1 hour after start when not specified.\n"
                "- Set generate_meet_link to true if user asks for a video/meet/zoom link.\n"
                "Return only the JSON object, no explanation."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except (json.JSONDecodeError, AttributeError) as exc:
            return AgentResult(success=False, output="I couldn't understand that calendar request. Try asking to list, create, or reschedule an event.", error=str(exc))

        action = command.get("action", "list")
        query = (command.get("query") or command.get("summary") or "").strip()

        # Fallback check if user input asks about a specific event or topic
        if not query and any(w in user_input.lower() for w in ["meeting", "appointment", "call", "with", "event"]):
            # Try to extract search topic from user input
            topic_match = re.search(r"(?:meeting|appointment|call|event|with)\s+([a-zA-Z0-9_\- ]+)", user_input, re.IGNORECASE)
            if topic_match:
                query = topic_match.group(1).strip()

        try:
            if action in {"list", "details"}:
                list_kwargs = {"limit": 10, "query": query or None}
                if refresh_token:
                    list_kwargs["refresh_token"] = refresh_token
                events = await calendar_service.list_events(
                    token,
                    command.get("time_min"),
                    command.get("time_max"),
                    **list_kwargs,
                )
                if not events:
                    # Check if query or user_input asks for contact details (phone, number, email, contact name)
                    target_query = query or user_input
                    if any(w in user_input.lower() for w in ["phone", "number", "email", "contact", "who is", "mobile", "address"]):
                        try:
                            from src.services.contacts.service import contacts_service
                            clean_q = re.sub(r"(?i)\b(find|get|what|is|the|phone|number|of|for|contact|details)\b", "", target_query).strip()
                            contacts = await contacts_service.list_contacts(token, refresh_token=refresh_token, query=clean_q or target_query)
                            if contacts:
                                heading = f'I didn\'t find a calendar event for "{query or clean_q}", but I found matching Google Contacts:\n'
                                lines = [heading]
                                for c in contacts:
                                    details = [f"- **{c['name']}**"]
                                    if c.get("email"):
                                        details.append(f"  - **Email:** `{c['email']}`")
                                    if c.get("phone"):
                                        details.append(f"  - **Phone:** `{c['phone']}`")
                                    if c.get("company"):
                                        details.append(f"  - **Company:** {c['company']}")
                                    lines.append("\n".join(details))
                                return AgentResult(success=True, output="\n\n".join(lines))
                        except Exception as c_err:
                            logger.warning(f"Cross-agent contacts lookup failed: {c_err}")

                    message = f'I could not find a calendar event matching "{query}".' if query else "You have no events in that time range."
                    return AgentResult(success=True, output=message)
                heading = f'Matching event details for "{query}":' if (action == "details" or query) else "Upcoming calendar events:"
                return AgentResult(
                    success=True,
                    output=heading + "\n\n" + "\n\n".join(self._format_event(event) for event in events),
                )
            if action == "create":
                summary = command.get("summary") or "New Event"
                start = command.get("start")
                end = command.get("end")
                if not start or not end:
                    return AgentResult(success=False, output="Please specify a valid start and end time for the event.", error="missing_time")
                event = await calendar_service.create_event(token, summary, start, end, command.get("description", ""), command.get("location", ""), command.get("attendees"), command.get("generate_meet_link", False), refresh_token=refresh_token)
                msg = f"Created “{event.get('summary', summary)}” from {event.get('start', start)} to {event.get('end', end)}.\n{event.get('link', '')}"
                if event.get("meeting_link"):
                    msg += f"\nMeeting Link: {event['meeting_link']}"
                return AgentResult(success=True, output=msg)
            if action in {"update", "reschedule"}:
                event_id = command.get("event_id")
                search_q = query or command.get("summary") or user_input
                if not event_id:
                    matching = await calendar_service.list_events(token, query=search_q, limit=5, refresh_token=refresh_token)
                    if matching:
                        event_id = matching[0]["id"]
                    else:
                        return AgentResult(success=False, output=f"I couldn't find an event matching '{search_q}' to update.", error="event_not_found")
                event = await calendar_service.update_event(token, event_id, command.get("summary"), command.get("start"), command.get("end"), command.get("description"), command.get("location"), command.get("attendees"), refresh_token=refresh_token)
                return AgentResult(success=True, output=f"Updated “{event.get('summary', 'event')}”.\n{event.get('link', '')}")
            if action == "delete":
                event_id = command.get("event_id")
                search_q = query or command.get("summary") or user_input
                matched_title = "event"
                if not event_id:
                    matching = await calendar_service.list_events(token, query=search_q, limit=5, refresh_token=refresh_token)
                    if matching:
                        event_id = matching[0]["id"]
                        matched_title = matching[0].get("summary", "event")
                    else:
                        return AgentResult(success=False, output=f"I couldn't find an event matching '{search_q}' to cancel.", error="event_not_found")
                await calendar_service.delete_event(token, event_id, refresh_token=refresh_token)
                return AgentResult(success=True, output=f"Cancelled event “{matched_title}” successfully.")

            if action == "availability":
                time_min = command.get("time_min")
                time_max = command.get("time_max")
                if not time_min or not time_max:
                    return AgentResult(success=False, output="Please specify time_min and time_max to check availability.", error="missing_time_range")
                availability = await calendar_service.find_availability(token, time_min, time_max, refresh_token=refresh_token)
                return AgentResult(success=True, output="That window is available." if availability.get("available") else f"You already have {len(availability.get('busy', []))} busy block(s) in that window.")
            return AgentResult(success=False, output="I can list, create, update, delete, or check availability for calendar events.", error="unsupported_calendar_action")
        except Exception as exc:
            return AgentResult(success=False, output=f"Calendar action failed: {exc}", error=str(exc))
