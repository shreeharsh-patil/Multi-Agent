from typing import Optional, Any
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from src.agents.registry import AgentRegistry
from src.agents.metadata import AgentDepartment
from src.orchestrator.boss import get_boss_agent
from src.utils.logger import logger

router = APIRouter(prefix="/api/agent-platform", tags=["Agent Platform"])


class TaskPlanRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "user_default"


class TaskExecuteRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "user_default"
    task_id: Optional[str] = None


@router.get("/agents")
async def list_registered_agents(
    department: Optional[str] = Query(None, description="Filter agents by department"),
    capability: Optional[str] = Query(None, description="Filter agents by capability"),
    query: Optional[str] = Query(None, description="Search query across name/desc/dept/capabilities"),
):
    """Retrieves all registered agents in the platform with department & metadata."""
    if query:
        return {"success": True, "count": len(AgentRegistry.search(query)), "data": AgentRegistry.search(query)}

    if department:
        agents = AgentRegistry.get_by_department(department)
        metadata_list = [
            AgentRegistry.get_metadata(a.manifest.id) for a in agents
            if AgentRegistry.get_metadata(a.manifest.id)
        ]
        return {
            "success": True,
            "department": department,
            "count": len(metadata_list),
            "data": [
                {
                    "id": m.id,
                    "name": m.name,
                    "department": m.department.value,
                    "description": m.description,
                    "capabilities": m.capabilities,
                    "responsibilities": m.responsibilities,
                    "required_tools": m.required_tools,
                    "optional_tools": m.optional_tools,
                    "icon": m.icon,
                }
                for m in metadata_list
            ],
        }

    if capability:
        agents = AgentRegistry.get_by_capability(capability)
        metadata_list = [
            AgentRegistry.get_metadata(a.manifest.id) for a in agents
            if AgentRegistry.get_metadata(a.manifest.id)
        ]
        return {
            "success": True,
            "capability": capability,
            "count": len(metadata_list),
            "data": [
                {
                    "id": m.id,
                    "name": m.name,
                    "department": m.department.value,
                    "description": m.description,
                    "capabilities": m.capabilities,
                    "responsibilities": m.responsibilities,
                    "required_tools": m.required_tools,
                    "optional_tools": m.optional_tools,
                    "icon": m.icon,
                }
                for m in metadata_list
            ],
        }

    # Default: Return metadata for all 100 registered agents
    all_metadata = AgentRegistry.get_all_metadata()
    return {
        "success": True,
        "total_agents": len(all_metadata),
        "departments": [d.value for d in AgentDepartment],
        "data": [
            {
                "id": m.id,
                "name": m.name,
                "department": m.department.value,
                "description": m.description,
                "capabilities": m.capabilities,
                "responsibilities": m.responsibilities,
                "required_tools": m.required_tools,
                "optional_tools": m.optional_tools,
                "priority": m.priority,
                "icon": m.icon,
            }
            for m in all_metadata
        ],
    }


@router.post("/plan")
async def plan_task(payload: TaskPlanRequest):
    """Boss Agent task planning preview."""
    boss = get_boss_agent()
    intent = await boss._analyze_intent(payload.prompt)
    graph = await boss._build_execution_graph("plan_preview", payload.prompt, intent)

    return {
        "success": True,
        "complexity": graph.complexity,
        "intent": intent,
        "nodes_count": len(graph.nodes),
        "execution_graph": [
            {
                "id": node.id,
                "title": node.title,
                "agent_id": node.agent_id,
                "objective": node.objective,
                "dependencies": node.dependencies,
            }
            for node in graph.nodes.values()
        ],
    }


@router.post("/execute")
async def execute_task(payload: TaskExecuteRequest):
    """Executes a task through the Boss Agent multi-step orchestration loop."""
    boss = get_boss_agent()
    result = await boss.execute_task(
        user_request=payload.prompt,
        user_id=payload.user_id or "user_default",
        task_id=payload.task_id,
    )
    return {"success": True, "data": result}
