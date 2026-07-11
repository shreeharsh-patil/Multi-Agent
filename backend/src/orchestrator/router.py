import re
from typing import Optional
from src.utils.logger import logger


class AgentRouter:
    def __init__(self):
        self.routing_rules = [
            (r"(?i)\b(summarize|summarise|summary|extract|what is|explain|tell me about|find|search)\b.*\b(document|pdf|file|knowledge|upload|note|article|paper)\b", "knowledge"),
            (r"(?i)\b(drive|google drive|upload|download|sync|folder|file)\b.*\b(document|file|folder|upload|download)\b", "drive"),
            (r"(?i)\b(note|notes|flashcard|revision|study note|anki)\b", "notes"),
            (r"(?i)\b(quiz|mcq|multiple choice|exam|practice question|test)\b", "quiz"),
            (r"(?i)\b(plan|schedule|deadline|task|todo|remind|calendar)\b", "planner"),
            (r"(?i)\b(research|search internet|web search|find online|report on|investigate)\b", "research"),
            (r"(?i)\b(write code|code|program|debug|function|class|algorithm|implement)\b", "coding"),
            (r"(?i)\b(remember|memory|recall|what did i|my name|my preference)\b", "memory"),
            (r"(?i)\b(calculate|math|calendar|gmail|email|api|integration)\b", "tool"),
        ]

    def route(self, user_input: str) -> Optional[str]:
        for pattern, agent_id in self.routing_rules:
            if re.search(pattern, user_input):
                logger.info(f"Routed to agent: {agent_id}", extra={"input": user_input[:100]})
                return agent_id
        return None
