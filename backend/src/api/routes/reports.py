import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.middleware import resolve_user_id
from src.models.document import Document
from src.services.llm import llm_service
from src.services.notes.exporter import notes_exporter


router = APIRouter(prefix="/api/reports", tags=["Reports"])
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ReportInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=100000)
    polish: bool = True
    workspace_id: str | None = None


@router.post("")
async def generate_report(request: Request, body: ReportInput) -> dict:
    user_id = resolve_user_id(request)
    content = body.content
    if body.polish:
        prompt = (
            "Rewrite the following agent output as a publication-ready Markdown report. Preserve facts, "
            "citations, code, and uncertainty. Use a concise executive summary, clear section headings, "
            "findings, and a conclusion. Do not invent sources or claims.\n\n"
            f"TITLE: {body.title}\n\nSOURCE CONTENT:\n{body.content}"
        )
        content = await llm_service.generate(prompt, temperature=0.2, max_output_tokens=8000)
    try:
        pdf_bytes = await notes_exporter.export_pdf(body.title, content)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}") from exc
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", body.title).strip("-")[:80] or "agent-report"
    file_name = f"{stem}-{uuid.uuid4().hex[:8]}.pdf"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(pdf_bytes)
    document = Document(
        user_id=user_id, file_name=file_name, file_type="pdf", file_size=len(pdf_bytes),
        file_path=str(file_path), status="ready", workspace_id=body.workspace_id,
    )
    await document.insert()
    return {
        "documentId": str(document.id), "fileName": file_name,
        "downloadUrl": f"/api/documents/{document.id}/download", "content": content,
    }

