from uuid import uuid4
from pathlib import Path
from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.services.study_agent import study_agent_service
from src.services.notes.exporter import publication_exporter
from src.models.document import Document
from src.utils.logger import logger

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class NotesAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="notes",
            name="Notes Agent",
            description="Structured study notes with publication-quality PDF generation and Google Drive sync",
            icon="StickyNote",
            capabilities=["note_taking", "pdf_generation", "summaries", "flashcards", "revision_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        user_id = context.get("user_id", "default")
        workspace_id = context.get("workspace_id")
        drive_access_token = context.get("google_access_token") or context.get("drive_access_token")
        drive_refresh_token = context.get("google_refresh_token") or context.get("drive_refresh_token")

        input_lower = user_input.lower()
        style = "detailed"
        if "exam" in input_lower:
            style = "exam"
        elif "beginner" in input_lower or "simple" in input_lower:
            style = "beginner"
        elif "revision" in input_lower or "summary" in input_lower or "recap" in input_lower:
            style = "revision"
        elif "cheat" in input_lower or "formula" in input_lower:
            style = "cheatsheet"

        try:
            notes_res = await study_agent_service.generate_study_notes(
                topic=user_input,
                user_id=user_id,
                style=style,
                workspace_id=workspace_id,
            )
            title = notes_res.get("title", "Study Notes")
            content = notes_res.get("content", "")
        except Exception as e:
            logger.warning(f"study_agent_service failed, falling back to direct LLM: {e}")
            from src.services.llm import llm_service
            content = await llm_service.generate(
                prompt=user_input,
                system_instruction="You are a Notes Agent. Create structured, publication-quality study notes with headings, formulas, and bullet points.",
            )
            title = f"{user_input[:35].title()} Study Notes"

        output_text = content

        # Generate Publication-Quality PDF
        try:
            pdf_bytes = await publication_exporter.export_pdf(
                title=title,
                content=content,
                scope="complete",
                author="",
                subject="",
            )
            file_name = f"notes-{uuid4().hex[:12]}.pdf"
            file_path = UPLOAD_DIR / file_name
            file_path.write_bytes(pdf_bytes)

            drive_file_id = None
            drive_web_view_link = None
            if drive_access_token:
                try:
                    from src.services.drive.service import DriveService
                    drive = DriveService()
                    drive_result = await drive.upload_file(
                        access_token=drive_access_token,
                        file_path=str(file_path),
                        file_name=file_name,
                        mime_type="application/pdf",
                        refresh_token=drive_refresh_token or "",
                    )
                    drive_file_id = drive_result.get("id")
                    drive_web_view_link = drive_result.get("webViewLink")
                    logger.info(f"PDF notes synced to Google Drive: {file_name} (id={drive_file_id})")
                except Exception as err:
                    logger.warning(f"Failed to sync PDF notes to Drive: {err}")

            doc = Document(
                user_id=user_id,
                file_name=file_name,
                file_type="pdf",
                file_size=len(pdf_bytes),
                file_path=str(file_path),
                status="ready",
                workspace_id=workspace_id,
                drive_file_id=drive_file_id,
                drive_web_view_link=drive_web_view_link,
            )
            await doc.insert()

            download_url = f"/api/documents/{doc.id}/download?download=true"
            output_text += f"\n\n---\n\n📄 **Publication PDF Generated:** [Download PDF Notes]({download_url})"
        except Exception as pdf_err:
            logger.error(f"Failed to compile PDF notes: {pdf_err}", exc_info=True)

        return AgentResult(success=True, output=output_text)
