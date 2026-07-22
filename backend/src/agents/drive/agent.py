import json
import re

from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger


class DriveAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="drive",
            name="Drive Agent",
            description="Google Drive uploads, downloads, content inspection, document summarization, and folder management",
            icon="Brain",
            capabilities=["drive_list", "drive_read", "drive_summarize", "drive_upload", "drive_download", "drive_sync", "folder_management"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.drive.service import drive_service

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
                "action, query, file_id_or_name, folder_name, parent_id. "
                "action must be one of: list, search, read, summarize, create_folder. "
                "Use list when the user asks what files are in Drive. "
                "Use search when searching files by keyword. "
                "Use read or summarize when the user asks what is inside a file, asks to read/inspect it, "
                "asks a question about its contents, or asks to summarize a file in Drive. "
                "Set file_id_or_name to the file name or file ID mentioned by the user (if any). "
                "Do not include markdown."
            ),
        )
        try:
            match = re.search(r"\{.*\}", extraction, re.DOTALL)
            command = json.loads(match.group(0) if match else extraction)
        except (json.JSONDecodeError, AttributeError) as exc:
            command = {"action": "list"}

        action = command.get("action", "list")
        file_target = (command.get("file_id_or_name") or command.get("query") or "").strip()

        # Fallback check if user input explicitly asks to read/summarize/inspect
        lower_input = user_input.lower()
        if any(w in lower_input for w in ["summarize", "summarise", "summary", "whats inside", "what is inside", "read", "explain", "contents of"]):
            if action in {"list", "search"}:
                action = "read"

        try:
            if action in {"read", "summarize"}:
                # If file_target is empty, try to resolve from conversation history
                if not file_target and context.get("conversation_history"):
                    hist_matches = re.findall(r"([a-zA-Z0-9_\- ]+\.(?:pdf|docx|pptx|txt|md|csv|png|jpg|xlsx))", context["conversation_history"], re.IGNORECASE)
                    if hist_matches:
                        file_target = hist_matches[-1].strip()

                clean_target = file_target.strip()
                files = await drive_service.list_files(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    page_size=100,
                    name_query=clean_target if clean_target else None,
                )
                if not files and clean_target:
                    # Retry without name_query filter in case file name has special formatting
                    files = await drive_service.list_files(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        page_size=100,
                    )

                if not files:
                    return AgentResult(success=True, output="Your Google Drive is empty or no files were found.")

                target_file = None
                if clean_target:
                    # 1. Exact ID
                    for f in files:
                        if f.get("id") == clean_target:
                            target_file = f
                            break
                    # 2. Exact Name
                    if not target_file:
                        for f in files:
                            if (f.get("name") or "").casefold() == clean_target.casefold():
                                target_file = f
                                break
                    # 3. Partial Name
                    if not target_file:
                        for f in files:
                            if clean_target.casefold() in (f.get("name") or "").casefold():
                                target_file = f
                                break
                elif len(files) == 1:
                    target_file = files[0]

                if not target_file:
                    if clean_target:
                        return AgentResult(
                            success=True,
                            output=f"Could not find a file matching **{clean_target}** in your Google Drive. Please check the file name.",
                        )
                    else:
                        file_list = "\n".join(f"- **{f.get('name')}**" for f in files[:10])
                        msg = (
                            f"Please specify which file you would like me to read/summarize. Available files:\n{file_list}"
                        )
                        return AgentResult(success=True, output=msg)

                file_id = target_file.get("id")
                file_name = target_file.get("name", "Untitled")

                text, info = await drive_service.read_and_parse_file_content(
                    access_token=access_token,
                    file_id=file_id,
                    refresh_token=refresh_token,
                )

                if not text.strip():
                    return AgentResult(
                        success=True,
                        output=f"File **{file_name}** was found, but no readable text content could be extracted.",
                    )

                sys_prompt = (
                    f"You are an AI assistant helping a user with their Google Drive file.\n"
                    f"File Name: {file_name}\n"
                    f"MIME Type: {info.get('mimeType', 'unknown')}\n\n"
                    f"Extracted File Content:\n"
                    f"\"\"\"\n{text[:30000]}\n\"\"\"\n\n"
                    f"Answer the user's request thoroughly based on the file content above. "
                    f"If they asked for a summary, provide a comprehensive summary with main key points and takeaways."
                )

                answer = await llm_service.generate(prompt=user_input, system_instruction=sys_prompt)
                return AgentResult(success=True, output=answer)

            if action in {"list", "search"}:
                query = file_target or (command.get("query") or "").strip()
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
                heading = f'Google Drive search results for "{query}":' if query else "Google Drive files:"
                suffix = "\n\nShowing the first 100 matching items." if len(files) == 100 else ""
                return AgentResult(success=True, output=heading + "\n" + "\n".join(lines) + suffix)

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

            return AgentResult(success=False, output="I can list, search, read, summarize, or create Google Drive folders.", error="unsupported_drive_action")
        except Exception as exc:
            logger.error(f"Drive agent action failed: {exc}")
            return AgentResult(success=False, output=f"Drive action failed: {exc}", error=str(exc))
