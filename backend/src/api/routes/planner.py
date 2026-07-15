from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from src.models.planner import PlannerPlan
from src.api.middleware import resolve_user_id
from src.utils.logger import logger

router = APIRouter(prefix="/api/planner", tags=["Planner"])


class CreatePlanRequest(BaseModel):
    title: str
    content: str
    user_id: str = "default"


class PlanResponse(BaseModel):
    id: str
    title: str
    content: str
    createdAt: str


@router.get("")
async def list_plans(http_request: Request, user_id: str = "default") -> list[PlanResponse]:
    """List all planner plans for a user, newest first."""
    user_id = resolve_user_id(http_request, user_id)
    plans = await PlannerPlan.find(
        PlannerPlan.user_id == user_id
    ).sort(-PlannerPlan.created_at).to_list()

    return [
        PlanResponse(
            id=str(p.id),
            title=p.title,
            content=p.content,
            createdAt=p.created_at.isoformat(),
        )
        for p in plans
    ]


@router.get("/{plan_id}")
async def get_plan(plan_id: str, http_request: Request) -> PlanResponse:
    """Get a single planner plan."""
    user_id = resolve_user_id(http_request)
    plan = await PlannerPlan.get(plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(404, "Plan not found")

    return PlanResponse(
        id=str(plan.id),
        title=plan.title,
        content=plan.content,
        createdAt=plan.created_at.isoformat(),
    )


@router.post("", status_code=201)
async def create_plan(body: CreatePlanRequest, http_request: Request) -> PlanResponse:
    """Create a new planner plan."""
    plan = PlannerPlan(
        user_id=resolve_user_id(http_request, body.user_id),
        title=body.title,
        content=body.content,
    )
    await plan.insert()

    return PlanResponse(
        id=str(plan.id),
        title=plan.title,
        content=plan.content,
        createdAt=plan.created_at.isoformat(),
    )


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str, http_request: Request) -> dict:
    """Delete a planner plan."""
    user_id = resolve_user_id(http_request)
    plan = await PlannerPlan.get(plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(404, "Plan not found")
    await plan.delete()
    return {"success": True, "message": "Plan deleted"}
