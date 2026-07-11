from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.models.research import ResearchReport
from src.utils.logger import logger

router = APIRouter(prefix="/api/research", tags=["Research"])


class CreateReportRequest(BaseModel):
    query: str
    content: str
    user_id: str = "default"


class ReportResponse(BaseModel):
    id: str
    query: str
    content: str
    createdAt: str


@router.get("")
async def list_reports(user_id: str = "default") -> list[ReportResponse]:
    """List all research reports for a user, newest first."""
    reports = await ResearchReport.find(
        ResearchReport.user_id == user_id
    ).sort(-ResearchReport.created_at).to_list()

    return [
        ReportResponse(
            id=str(r.id),
            query=r.query,
            content=r.content,
            createdAt=r.created_at.isoformat(),
        )
        for r in reports
    ]


@router.get("/{report_id}")
async def get_report(report_id: str) -> ReportResponse:
    """Get a single research report."""
    report = await ResearchReport.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found")

    return ReportResponse(
        id=str(report.id),
        query=report.query,
        content=report.content,
        createdAt=report.created_at.isoformat(),
    )


@router.post("", status_code=201)
async def create_report(body: CreateReportRequest) -> ReportResponse:
    """Create a new research report."""
    report = ResearchReport(
        user_id=body.user_id,
        query=body.query,
        content=body.content,
    )
    await report.insert()

    return ReportResponse(
        id=str(report.id),
        query=report.query,
        content=report.content,
        createdAt=report.created_at.isoformat(),
    )


@router.delete("/{report_id}")
async def delete_report(report_id: str) -> dict:
    """Delete a research report."""
    report = await ResearchReport.get(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    await report.delete()
    return {"success": True, "message": "Report deleted"}
