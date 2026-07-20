import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult

class GmailAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="gmail",
            name="Gmail Agent",
            description="Reads and manages your Gmail inbox",
            icon="Mail",
            capabilities=["list_emails"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.gmail.service import gmail_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            token = await find_user_access_token(context["user_id"])

        if not token:
            return AgentResult(success=False, output="Connect Gmail in Settings before asking me to read your emails.", error="missing_gmail_token")

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Gmail command parser. Return ONLY valid JSON with keys: action, query. "
                "action must be list. If the user asks for specific emails (e.g. 'unread', 'from john'), "
                "formulate a standard Gmail search query in the 'query' field."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except Exception:
            command = {"action": "list", "query": ""}

        action = command.get("action", "list")
        try:
            if action == "list":
                emails = await gmail_service.list_emails(token, refresh_token=refresh_token, query=command.get("query", ""), max_results=5)
                if not emails:
                    return AgentResult(success=True, output="You have no emails matching that query.")
                
                lines = ["### Recent Emails\n"]
                for e in emails:
                    lines.append(f"- **{e['subject']}**\n  *From: {e['from']} ({e['date']})*\n  >{e['snippet']}...\n")
                
                return AgentResult(success=True, output="\n".join(lines))
            return AgentResult(success=False, output="I can list emails right now.", error="unsupported_gmail_action")
        except Exception as exc:
            return AgentResult(success=False, output=f"Gmail action failed: {exc}", error=str(exc))
