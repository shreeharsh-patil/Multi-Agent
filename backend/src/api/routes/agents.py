from fastapi import APIRouter
from src.agents.registry import AgentRegistry

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("")
async def list_agents() -> list[dict]:
    manifests = AgentRegistry.get_all_manifests()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "icon": m.icon,
            "version": m.version,
            "capabilities": m.capabilities,
            "enabled": m.enabled,
        }
        for m in manifests
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    agent = AgentRegistry.get_agent(agent_id)
    if not agent:
        return {"error": f"Agent '{agent_id}' not found"}, 404

    m = agent.manifest
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "icon": m.icon,
        "version": m.version,
        "capabilities": m.capabilities,
        "enabled": m.enabled,
    }
