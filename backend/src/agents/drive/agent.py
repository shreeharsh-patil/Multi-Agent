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

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Drive Agent that helps users manage Google Drive files and folders. "
                "You can list files, upload, download, sync folders, and manage Drive organization. "
                "Explain what you can do and guide the user through Drive operations."
            ),
        )
        return AgentResult(success=True, output=response)
