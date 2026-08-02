import re
from typing import Optional
from src.utils.logger import logger


class AgentRouter:
    def __init__(self):
        self.routing_rules = [
            (r"(?i)\b(generate|create|draw|make|design|render|paint|show|produce)\b.*\b(image|picture|photo|photograph|illustration|drawing|artwork|poster|logo|icon|graphic|banner|vector|avatar)\b", "image"),
            (r"(?i)\b(image|picture|photo|drawing|illustration)\b\s+(of|for|with|showing|featuring)\b", "image"),
            (r"(?i)\b(logo|icon|avatar)\b\s+(for|of|with|showing|featuring)\b", "image"),
            # Contacts: catch explicit contact/phone/email lookups before calendar
            (r"(?i)\b(contact|contacts|phone\s*book|address\s*book|phone\s*number|cell\s*number|mobile\s*number|email\s*address|who\s+is\s+in\s+my\s+contacts|find\s+contact|get\s+number|contact\s+info)\b", "contacts"),
            (r"(?i)\b(number\s+of|phone\s+of|mobile\s+of|email\s+of|contact\s+details|number\s+for|phone\s+for)\b", "contacts"),
            # Calendar: catch all natural calendar/scheduling requests
            (r"(?i)\b(calendar|calender|calander)\b", "calendar"),
            (r"(?i)\b(meeting|appointment|event|availability|free\s*time|reschedule|book\s+(a\s+)?(slot|time|meeting)|add\s+to\s+(my\s+)?calendar|what.s\s+on\s+my|my\s+agenda|my\s+schedule|upcoming\s+events?|today.s\s+events?|tomorrow.s\s+events?|check\s+(my\s+)?schedule|show\s+(my\s+)?events?|list\s+(my\s+)?events?|delete\s+(the\s+)?(event|meeting|appointment)|cancel\s+(the\s+)?(event|meeting|appointment)|create\s+(a\s+)?(meeting|event|appointment)|schedule\s+(a\s+)?(meeting|call|event|appointment))\b", "calendar"),
            (r"(?i)\b(summarize|summarise|summary|extract|what is|explain|tell me about|find|search)\b.*\b(document|pdf|file|knowledge|upload|note|article|paper)\b", "knowledge"),
            (r"(?i)\b(google\s+drive|gdrive|drive)\b", "drive"),
            (r"(?i)\b(drive|google drive|upload|download|sync|folder|file)\b.*\b(document|file|folder|upload|download)\b", "drive"),
            (r"(?i)\b(note|notes|flashcards?|revision|study note|anki)\b", "notes"),
            (r"(?i)\b(quiz|mcq|multiple choice|exam|practice question|test)\b", "quiz"),
            (r"(?i)\b(google\s+task|google\s+tasks|tasks|to-do list|checklist)\b", "tasks"),
            (r"(?i)\b(plan|deadline|remind|task\s+list)\b", "planner"),
            (r"(?i)\b(research|search\s+(the\s+)?internet|web\s+search|find\s+online|report\s+on|investigate)\b", "research"),
            (r"(?i)\b(write code|code|program|debug|function|class|algorithm|implement)\b", "coding"),
            (r"(?i)\b(remember|memory|recall|what did i|my name|my preference)\b", "memory"),
            (r"(?i)\b(gmail|email|inbox|mail|message|messages)\b", "gmail"),
            (r"(?i)\b(youtube|video|videos|yt)\b", "youtube"),
            (r"(?i)\b(calculate|math|calculator|api|integration)\b", "tool"),
        ]

    def route(self, user_input: str) -> Optional[str]:
        for pattern, agent_id in self.routing_rules:
            if re.search(pattern, user_input):
                logger.info(f"Routed to agent: {agent_id}", extra={"input": user_input[:100]})
                return agent_id
        return None

    def route_smart(self, user_input: str, requested_agent_id: Optional[str] = None) -> str:
        """Dynamically select the best agent for a user prompt, auto-correcting misaligned dropdown selections."""
        # 1. Pattern rule match takes priority for specific actions (images, calendar, contacts, etc.)
        matched = self.route(user_input)
        if matched:
            return matched

        input_lower = user_input.lower().strip()

        # 2. If requested_agent_id is provided, validate it against the prompt nature
        if requested_agent_id and requested_agent_id != "auto":
            if requested_agent_id == "coding":
                coding_keywords = ["code", "script", "python", "javascript", "typescript", "html", "css", "sql", "java", "c++", "c#", "rust", "go", "function", "class", "algorithm", "debug", "error", "exception", "bug", "program", "api", "refactor", "syntax"]
                if not any(k in input_lower for k in coding_keywords):
                    # Query is general explanation/concept, route to knowledge agent
                    return "knowledge"
            return requested_agent_id

        # 3. For general explanations, questions, or concepts, default to knowledge agent
        explanation_keywords = ["explain", "what is", "define", "how does", "why", "tell me about", "concept", "meaning", "overview", "difference between"]
        if any(k in input_lower for k in explanation_keywords):
            return "knowledge"

        return "auto"
