import json
import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult

class TasksAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="tasks",
            name="Google Tasks Agent",
            description="Manages your Google Tasks and to-do lists",
            icon="CheckSquare",
            capabilities=["list_tasks", "create_task"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.tasks.service import tasks_service

        token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            token = await find_user_access_token(context["user_id"])

        if not token:
            return AgentResult(success=False, output="Connect Google Tasks in Settings first.", error="missing_tasks_token")

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Google Tasks command parser. Return ONLY valid JSON with keys: action, title, due. "
                "action must be list or create. Use ISO 8601 UTC date-time for due if specified."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except Exception:
            command = {"action": "list"}

        action = command.get("action", "list")
        try:
            if action == "list":
                tasks = await tasks_service.list_tasks(token, refresh_token=refresh_token)
                if not tasks:
                    return AgentResult(success=True, output="You have no tasks in your list.")
                lines = ["### Your Google Tasks\n"]
                for t in tasks:
                    status = "✅" if t["status"] == "completed" else "⏳"
                    lines.append(f"- {status} **{t['title']}**")
                return AgentResult(success=True, output="\n".join(lines))

            if action == "create":
                task = await tasks_service.create_task(token, command.get("title", "New Task"), command.get("due"), refresh_token=refresh_token)
                return AgentResult(success=True, output=f"Created task: **{task['title']}**")
            return AgentResult(success=False, output="I can list or create tasks.", error="unsupported_tasks_action")
        except Exception as exc:
            return AgentResult(success=False, output=f"Tasks action failed: {exc}", error=str(exc))
