from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.services.task_runner import stream_task_run
from src.utils.logger import logger

router = APIRouter(prefix="/api/task", tags=["Task Runner"])


class TaskRequest(BaseModel):
    prompt: str


@router.post("/run")
async def run_task(req: TaskRequest, http_request: Request):
    """Execute a multi-step task (plan -> execute -> verify) with SSE streaming."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    auth_user = getattr(http_request.state, "user", None)
    user_id = (auth_user.get("sub") if auth_user else None) or "default"

    logger.info(f"Starting multi-step task run: {req.prompt[:100]}")
    return StreamingResponse(
        stream_task_run(req.prompt, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
