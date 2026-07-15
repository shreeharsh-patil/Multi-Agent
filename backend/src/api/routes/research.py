from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from src.models.research import ResearchReport
from src.api.middleware import resolve_user_id
from src.utils.logger import logger
from src.agents.research.agent import ResearchAgent

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


class DeepResearchRequest(BaseModel):
    query: str
    user_id: str = "default"


@router.get("")
async def list_reports(http_request: Request, user_id: str = "default") -> list[ReportResponse]:
    """List all research reports for a user, newest first."""
    user_id = resolve_user_id(http_request, user_id)
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
async def get_report(report_id: str, http_request: Request) -> ReportResponse:
    """Get a single research report."""
    user_id = resolve_user_id(http_request)
    report = await ResearchReport.get(report_id)
    if not report or report.user_id != user_id:
        raise HTTPException(404, "Report not found")

    return ReportResponse(
        id=str(report.id),
        query=report.query,
        content=report.content,
        createdAt=report.created_at.isoformat(),
    )


@router.post("", status_code=201)
async def create_report(body: CreateReportRequest, http_request: Request) -> ReportResponse:
    """Create a new research report."""
    report = ResearchReport(
        user_id=resolve_user_id(http_request, body.user_id),
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


@router.post("/deep", status_code=201)
async def deep_research(body: DeepResearchRequest, http_request: Request) -> dict:
    if not body.query.strip():
        raise HTTPException(400, "Research query is required")
    try:
        result = await ResearchAgent().deep_research(body.query.strip())
        report = ResearchReport(user_id=resolve_user_id(http_request, body.user_id), query=body.query.strip(), content=result["output"])
        await report.insert()
        return {
            "id": str(report.id), "query": report.query, "content": report.content,
            "createdAt": report.created_at.isoformat(), "stages": result["stages"], "sources": result["sources"],
        }
    except Exception as exc:
        logger.error(f"Deep research failed: {exc}", exc_info=True)
        raise HTTPException(503, f"Deep research failed: {exc}")


@router.delete("/{report_id}")
async def delete_report(report_id: str, http_request: Request) -> dict:
    """Delete a research report."""
    user_id = resolve_user_id(http_request)
    report = await ResearchReport.get(report_id)
    if not report or report.user_id != user_id:
        raise HTTPException(404, "Report not found")
    await report.delete()
    return {"success": True, "message": "Report deleted"}
