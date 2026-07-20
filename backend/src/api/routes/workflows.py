"""Workflow DAG CRUD and SSE execution routes."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, Field

from src.agents.base import AgentResult
from src.models.workflow import WorkflowDAG, WorkflowRun, WorkflowNodeModel, WorkflowEdgeModel
from src.utils.logger import logger

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


# ── Helpers ────────────────────────────────────────────────────────────────


def _resolved_user(request: Request) -> str:
    auth_user = getattr(request.state, "user", None)
    return (auth_user.get("sub") if auth_user else None) or "default"


def _topo_sort(nodes: list[WorkflowNodeModel], edges: list[WorkflowEdgeModel]) -> list[str]:
    """Kahn's algorithm — returns node ids in topological order.
    Falls back to insertion order if there are no edges."""
    node_ids = [n.id for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("Workflow node IDs must be unique.")
    if not edges:
        return node_ids

    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    edge_pairs: set[tuple[str, str]] = set()
    for e in edges:
        if e.source not in adjacency or e.target not in in_degree:
            raise ValueError("Every workflow edge must connect existing nodes.")
        if e.source == e.target:
            raise ValueError("A workflow node cannot connect to itself.")
        pair = (e.source, e.target)
        if pair in edge_pairs:
            raise ValueError("Duplicate workflow edges are not allowed.")
        edge_pairs.add(pair)
        adjacency[e.source].append(e.target)
        in_degree[e.target] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for neighbour in adjacency[nid]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(order) != len(node_ids):
        raise ValueError("Workflow contains a cycle. Remove the circular connection before saving.")
    return order


def _serialize(wf: WorkflowDAG) -> dict:
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "prompt": wf.prompt,
        "nodes": [{"id": n.id, "agentId": n.agent_id, "label": n.label, "x": n.x, "y": n.y} for n in wf.nodes],
        "edges": [e.model_dump() for e in wf.edges],
        "createdAt": wf.created_at.isoformat(),
        "updatedAt": wf.updated_at.isoformat(),
    }


# ── Request schemas ────────────────────────────────────────────────────────


class NodeIn(BaseModel):
    id: str
    agent_id: str = Field(validation_alias=AliasChoices("agent_id", "agentId"))
    label: str
    x: float = 0.0
    y: float = 0.0


class EdgeIn(BaseModel):
    id: str
    source: str
    target: str


class WorkflowIn(BaseModel):
    name: str = "Untitled Workflow"
    description: str = ""
    prompt: str = ""
    nodes: list[NodeIn] = []
    edges: list[EdgeIn] = []


class RunRequest(BaseModel):
    prompt: Optional[str] = None
    user_id: Optional[str] = "default"


# ── Routes ─────────────────────────────────────────────────────────────────


@router.get("")
async def list_workflows(request: Request) -> list[dict]:
    user_id = _resolved_user(request)
    workflows = await WorkflowDAG.find(WorkflowDAG.user_id == user_id).sort(-WorkflowDAG.updated_at).to_list()
    return [_serialize(wf) for wf in workflows]


@router.post("")
async def create_workflow(request: Request, body: WorkflowIn) -> dict:
    user_id = _resolved_user(request)
    nodes = [WorkflowNodeModel(**n.model_dump()) for n in body.nodes]
    edges = [WorkflowEdgeModel(**e.model_dump()) for e in body.edges]
    try:
        _topo_sort(nodes, edges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    wf = WorkflowDAG(
        user_id=user_id,
        name=body.name.strip() or "Untitled Workflow",
        description=body.description.strip(),
        prompt=body.prompt,
        nodes=nodes,
        edges=edges,
    )
    await wf.insert()
    return _serialize(wf)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request) -> dict:
    user_id = _resolved_user(request)
    try:
        from beanie import PydanticObjectId
        wf = await WorkflowDAG.get(PydanticObjectId(workflow_id))
    except Exception:
        wf = None
    if not wf or wf.user_id != user_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _serialize(wf)


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: Request, body: WorkflowIn) -> dict:
    user_id = _resolved_user(request)
    try:
        from beanie import PydanticObjectId
        wf = await WorkflowDAG.get(PydanticObjectId(workflow_id))
    except Exception:
        wf = None
    if not wf or wf.user_id != user_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    nodes = [WorkflowNodeModel(**n.model_dump()) for n in body.nodes]
    edges = [WorkflowEdgeModel(**e.model_dump()) for e in body.edges]
    try:
        _topo_sort(nodes, edges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    wf.name = body.name.strip() or wf.name
    wf.description = body.description.strip()
    wf.prompt = body.prompt
    wf.nodes = nodes
    wf.edges = edges
    wf.updated_at = datetime.now(timezone.utc)
    await wf.save()
    return _serialize(wf)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, request: Request) -> dict:
    user_id = _resolved_user(request)
    try:
        from beanie import PydanticObjectId
        wf = await WorkflowDAG.get(PydanticObjectId(workflow_id))
    except Exception:
        wf = None
    if not wf or wf.user_id != user_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await wf.delete()
    return {"success": True}


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, request: Request, body: RunRequest) -> StreamingResponse:
    """Execute the workflow DAG and stream SSE events per node."""
    user_id = _resolved_user(request)
    try:
        from beanie import PydanticObjectId
        wf = await WorkflowDAG.get(PydanticObjectId(workflow_id))
    except Exception:
        wf = None
    if not wf or wf.user_id != user_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    prompt = (body.prompt or wf.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided for this workflow run.")

    nodes_map = {n.id: n for n in wf.nodes}
    try:
        exec_order = _topo_sort(wf.nodes, wf.edges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def _event_stream():
        from src.agents.registry import AgentRegistry

        run = WorkflowRun(
            workflow_id=workflow_id,
            user_id=user_id,
            prompt=prompt,
            status="running",
        )
        await run.insert()

        yield f"data: {json.dumps({'event': 'start', 'runId': str(run.id), 'nodeCount': len(exec_order)})}\n\n"

        handoff = prompt
        final_output = ""
        had_error = False

        for step_idx, node_id in enumerate(exec_order):
            node = nodes_map.get(node_id)
            if not node:
                continue

            yield f"data: {json.dumps({'event': 'node_start', 'nodeId': node_id, 'agentId': node.agent_id, 'step': step_idx})}\n\n"

            agent = AgentRegistry.get_agent(node.agent_id)
            if not agent and node.agent_id != "image":
                err_msg = f"Agent '{node.agent_id}' not found."
                yield f"data: {json.dumps({'event': 'node_error', 'nodeId': node_id, 'error': err_msg})}\n\n"
                run.node_results.append({"nodeId": node_id, "agentId": node.agent_id, "success": False, "error": err_msg})
                had_error = True
                continue

            try:
                ctx = {
                    "user_id": user_id,
                    "workflow_id": workflow_id,
                    "step": step_idx,
                    "google_access_token": request.headers.get("X-Google-Access-Token", ""),
                }
                if node.agent_id == "image":
                    from src.services.image_generation import generate_and_store_image

                    image = await generate_and_store_image(handoff, user_id, None)
                    result = AgentResult(
                        success=True,
                        output=f"![Generated image]({image.download_url})\n\n[Download image]({image.download_url})",
                    )
                else:
                    result = await agent.execute(handoff, ctx)

                run.node_results.append({
                    "nodeId": node_id,
                    "agentId": node.agent_id,
                    "success": result.success,
                    "output": result.output[:2000],
                    "error": result.error,
                })

                final_output = result.output

                yield f"data: {json.dumps({'event': 'node_complete', 'nodeId': node_id, 'agentId': node.agent_id, 'output': result.output[:1500], 'step': step_idx})}\n\n"

                if result.success:
                    handoff = (
                        f"Original task: {prompt}\n\n"
                        f"Output from previous agent ({node.agent_id}):\n{result.output}\n\n"
                        "Continue as the next specialist in the pipeline."
                    )
                else:
                    had_error = True
                    yield f"data: {json.dumps({'event': 'node_error', 'nodeId': node_id, 'error': result.error or 'Unknown error'})}\n\n"

            except Exception as exc:
                had_error = True
                logger.error("Workflow node error: %s", exc)
                yield f"data: {json.dumps({'event': 'node_error', 'nodeId': node_id, 'error': str(exc)})}\n\n"
                run.node_results.append({"nodeId": node_id, "agentId": node.agent_id, "success": False, "error": str(exc)})

        run.status = "error" if had_error else "complete"
        run.final_output = final_output
        run.completed_at = datetime.now(timezone.utc)
        await run.save()

        yield f"data: {json.dumps({'event': 'complete', 'runId': str(run.id), 'status': run.status, 'output': final_output[:3000]})}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{workflow_id}/runs")
async def list_runs(workflow_id: str, request: Request) -> list[dict]:
    user_id = _resolved_user(request)
    runs = await WorkflowRun.find(WorkflowRun.workflow_id == workflow_id, WorkflowRun.user_id == user_id).sort(-WorkflowRun.started_at).to_list(10)
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "prompt": r.prompt[:120],
            "nodeCount": len(r.node_results),
            "startedAt": r.started_at.isoformat(),
        }
        for r in runs
    ]
