import json
import re

from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger


class DriveAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="drive",
            name="Drive Agent",
            description="Google Drive uploads, downloads, sync, and folder management",
            icon="Brain",
            capabilities=["drive_list", "drive_upload", "drive_download", "drive_sync", "folder_management"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.drive import drive_service

        access_token = context.get("google_access_token", "")
        refresh_token = context.get("google_refresh_token", "")
        if not access_token and context.get("user_id"):
            from src.adk.tools import find_user_access_token
            access_token = await find_user_access_token(context["user_id"])

        if not access_token:
            return AgentResult(
                success=False,
                output="Connect Google Drive in Settings before asking me to access your files.",
                error="missing_google_drive_token",
            )

        extraction = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Google Drive command parser. Return ONLY valid JSON with keys "
                "action, query, folder_name, parent_id. action must be one of list, search, "
                "create_folder. Use list when the user asks what is in Drive. Use search only "
                "when they provide a file-name search term. Do not include markdown."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except (json.JSONDecodeError, AttributeError) as exc:
            return AgentResult(
                success=False,
                output="I couldn't understand that Drive request. Try asking me to list or search your files.",
                error=str(exc),
            )

        action = command.get("action", "list")
        try:
            if action in {"list", "search"}:
                query = (command.get("query") or "").strip() if action == "search" else ""
                files = await drive_service.list_files(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    page_size=100,
                    name_query=query or None,
                )
                if not files:
                    message = f'No Drive files matched "{query}".' if query else "Your Google Drive is empty."
                    return AgentResult(success=True, output=message)

                lines = []
                for item in files:
                    item_type = "Folder" if item.get("mimeType") == "application/vnd.google-apps.folder" else "File"
                    modified = item.get("modifiedTime") or "unknown date"
                    link = item.get("webViewLink") or ""
                    lines.append(f"- **{item.get('name', 'Untitled')}** ({item_type}, modified {modified}){f' - {link}' if link else ''}")
                suffix = "\n\nShowing the first 100 matching items." if len(files) == 100 else ""
                return AgentResult(success=True, output="Google Drive files:\n" + "\n".join(lines) + suffix)

            if action == "create_folder":
                folder_name = (command.get("folder_name") or "").strip()
                if not folder_name:
                    return AgentResult(success=False, output="Tell me the name of the folder to create.", error="missing_folder_name")
                folder = await drive_service.create_folder(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    folder_name=folder_name,
                    parent_id=command.get("parent_id") or None,
                )
                return AgentResult(success=True, output=f"Created the Drive folder **{folder.get('name', folder_name)}**.")

            return AgentResult(success=False, output="I can list, search, or create Google Drive folders.", error="unsupported_drive_action")
        except Exception as exc:
            logger.error(f"Drive agent action failed: {exc}")
            return AgentResult(success=False, output=f"Drive action failed: {exc}", error=str(exc))
