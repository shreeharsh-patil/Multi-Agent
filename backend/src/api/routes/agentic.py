"""REST + SSE endpoints for the Agentic Boss (multi-agent orchestration engine)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agentic.agents import ExecutiveRegistry
from src.agentic.boss import BossAgent, BossConfig
from src.agentic.core import TaskState
from src.agentic.store import store
from src.api.middleware import resolve_user_id
from src.config import settings
from src.utils.logger import logger

router = APIRouter(prefix="/api/agentic", tags=["Agentic Boss"])


class TaskRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=8000)
    context: dict = Field(default_factory=dict)


def _get_boss() -> BossAgent:
    return BossAgent(config=BossConfig())


def _snapshot(record) -> dict:
    return {
        "task_id": record.id,
        "user_id": record.user_id,
        "request": record.request,
        "objective": record.objective,
        "complexity": record.complexity,
        "intent_type": getattr(record, "intent_type", ""),
        "state": record.state,
        "selected_agents": record.selected_agents,
        "subtask_count": len(record.subtasks),
        "waves": record.waves or [],
        "final_output": record.final_output,
        "agent_calls": record.agent_calls,
        "replan_count": record.replan_count,
        "error": record.error,
        "latency_ms": round((getattr(record, "completed_at", 0) or 0) - (getattr(record, "created_at", 0) or 0)) if getattr(record, "completed_at", None) else 0,
        "events_filtered": [e for e in record.events if e.get("type") in {"task_start", "understand", "decompose", "selected", "graph", "evaluate", "replan", "task_complete", "task_error", "task_cancelled"}],
    }


async def _persist(record) -> None:
    """Best-effort snapshot into Mongo (never fails a request)."""
    try:
        from src.models.agentic_task import AgenticTask
        snap = _snapshot(record)
        doc = await AgenticTask.find_one(AgenticTask.task_id == record.id)
        if doc is None:
            doc = AgenticTask(task_id=record.id)
        doc.user_id = record.user_id
        doc.request = record.request
        doc.objective = record.objective
        doc.complexity = record.complexity
        doc.state = record.state
        doc.department_counts = {}
        doc.selected_agents = record.selected_agents
        doc.subtask_count = len(record.subtasks)
        doc.waves = record.waves or []
        doc.final_output = record.final_output
        doc.agent_calls = record.agent_calls
        doc.replan_count = record.replan_count
        doc.events = record.events[-300:]
        doc.latency_ms = snap["latency_ms"]
        await doc.save()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Agentic snapshot persist failed: %s", exc)


# ---------------------------------------------------------------------------
# Catalog endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config() -> dict:
    cfg = BossConfig()
    return {
        "enabled": cfg.enabled,
        "max_agents": cfg.max_agents,
        "max_waves": cfg.max_waves,
        "max_retries": cfg.max_retries,
        "max_alternates": cfg.max_alternates,
        "max_replan_rounds": cfg.max_replan_rounds,
        "agent_timeout_seconds": cfg.agent_timeout_seconds,
        "include_reviewers": cfg.include_reviewers,
        "auto_evaluate": cfg.auto_evaluate,
        "strong_synthesis": cfg.strong_synthesis,
    }


@router.get("/agents")
async def list_agents() -> dict:
    registry = ExecutiveRegistry.get()
    manifests = [m.to_brief() for m in registry.get_manifests()]
    departments: dict[str, int] = {}
    for m in manifests:
        departments[m["department"]] = departments.get(m["department"], 0) + 1
    return {
        "count": len(manifests),
        "departments": departments,
        "agents": manifests,
    }


@router.get("/agents/{slug}")
async def agent_detail(slug: str) -> dict:
    agent = ExecutiveRegistry.get().get_agent(slug)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found")
    manifest = agent.manifest
    return {
        **manifest.to_brief(),
        "description": manifest.description,
        "optional_tools": manifest.optional_tools,
        "cost_weight": manifest.cost_weight,
        "avg_latency_ms": manifest.avg_latency_ms,
    }


@router.get("/departments")
async def list_departments() -> dict:
    registry = ExecutiveRegistry.get()
    groups = []
    for dept in registry.departments():
        agents = [a.manifest.to_brief() for a in registry.agents_in_department(dept)]
        groups.append({"department": dept, "count": len(agents), "agents": agents})
    return {"departments": groups, "count": len(groups)}


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def create_plan(body: TaskRequest, request: Request) -> dict:
    user_id = resolve_user_id(request)
    boss = _get_boss()
    record = await boss.plan(body.request, user_id=user_id, context=body.context)
    store.put(record)
    if record.state != TaskState.BLOCKED:
        await _persist(record)
    return _snapshot(record)


@router.get("/tasks")
async def list_tasks() -> dict:
    records = store.list()
    return {"tasks": [_snapshot(r) for r in records], "count": len(records)}


@router.get("/tasks/{task_id}")
async def task_detail(task_id: str) -> dict:
    record = store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found (not planned this session)")
    snap = _snapshot(record)
    snap["subtasks"] = [s.to_dict() for s in record.subtasks]
    snap["events"] = record.events
    return snap


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str) -> dict:
    record = store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "events": record.events}


@router.get("/tasks/{task_id}/result")
async def task_result(task_id: str) -> dict:
    record = store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    subtask_outputs = []
    for s in record.subtasks:
        if s.result and s.result.success:
            subtask_outputs.append({
                "subtask_id": s.id, "title": s.title,
                "agent": s.agent_slug, "result": s.result.result,
                "confidence": s.result.confidence,
            })
    return {
        "task_id": task_id,
        "state": record.state,
        "objective": record.objective,
        "final_output": record.final_output,
        "subtask_outputs": subtask_outputs,
        "agent_calls": record.agent_calls,
        "replan_count": record.replan_count,
        "latency_ms": _snapshot(record)["latency_ms"],
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict:
    if store.request_cancel(task_id):
        return {"task_id": task_id, "cancellation_requested": True}
    raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

@router.post("/execute")
async def execute_once(body: TaskRequest, request: Request) -> dict:
    """One-shot create + plan + execute (no streaming); returns final result."""
    user_id = resolve_user_id(request)
    boss = _get_boss()
    record = await boss.run(body.request, user_id=user_id, context=body.context)
    store.put(record)
    await _persist(record)
    if record.state == TaskState.COMPLETED:
        return _snapshot(record)
    raise HTTPException(status_code=502, detail=record.error or "Agentic run failed")


async def _sse_stream(task_id: str) -> AsyncIterator[str]:
    """Run the task and stream every Boss event as SSE server-sent events."""
    record = store.get(task_id)
    if record is None:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Task not found'}})}\n\n"
        return

    queue: asyncio.Queue = asyncio.Queue()

    def on_event(e_type: str, data: dict) -> None:
        queue.put_nowait({"type": e_type, "data": data})

    yield f"data: {json.dumps({'type': 'stream_start', 'data': {'task_id': task_id}})}\n\n"

    async def runner() -> None:
        try:
            await _get_boss().run(
                record.request, user_id=record.user_id, context=None,
                on_event=on_event, record=record, should_cancel=lambda: store.is_cancelled(task_id),
            )
        except Exception as exc:  # noqa: BLE001
            on_event("task_error", {"error": str(exc)[:800]})
        finally:
            await _persist(record)
            queue.put_nowait(None)  # sentinel

    task = asyncio.create_task(runner())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        store.request_cancel(task_id)
        task.cancel()
        raise


@router.post("/tasks/{task_id}/stream")
async def stream_task(task_id: str) -> StreamingResponse:
    if store.get(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    store.clear_cancel(task_id)
    return StreamingResponse(
        _sse_stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str) -> dict:
    record = store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    boss = _get_boss()
    await boss.run(
        record.request, user_id=record.user_id, context=None,
        record=record, should_cancel=lambda: store.is_cancelled(task_id),
    )
    await _persist(record)
    return _snapshot(record)