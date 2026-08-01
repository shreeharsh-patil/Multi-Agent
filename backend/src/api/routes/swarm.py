from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.services.swarm_service import stream_swarm_collaboration, SWARM_AGENTS
from src.utils.logger import logger

router = APIRouter(prefix="/api/swarm", tags=["Multi-Agent Swarm"])


class SwarmRequest(BaseModel):
    prompt: str


@router.get("/agents")
async def get_swarm_agents():
    """Return manifest of agents participating in Swarm collaboration."""
    return {"agents": SWARM_AGENTS}


@router.post("/stream")
async def execute_swarm_stream(req: SwarmRequest):
    """Execute multi-agent debate and collaboration with real-time SSE streaming."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    logger.info(f"Starting Multi-Agent Swarm for prompt: {req.prompt[:100]}")
    return StreamingResponse(
        stream_swarm_collaboration(req.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
