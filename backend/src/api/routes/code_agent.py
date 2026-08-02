from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.middleware import resolve_user_id
from src.services.code_agent import stream_code_run


router = APIRouter(prefix="/api/code-agent", tags=["Code Agent"])


class CodeRunRequest(BaseModel):
    prompt: str = Field(min_length=3)
    language: Optional[str] = None


@router.post("/run")
async def run_code_agent(body: CodeRunRequest, request: Request) -> StreamingResponse:
    user_id = resolve_user_id(request)

    async def gen():
        async for chunk in stream_code_run(body.prompt, body.language, user_id):
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
