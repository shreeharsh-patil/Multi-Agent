from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.services.image_generation import generate_and_store_image


router = APIRouter(prefix="/api/images", tags=["Images"])


class GenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    size: str = "1024x1024"
    workspace_id: str | None = None


@router.post("/generate")
async def generate_image(request: Request, body: GenerateImageRequest) -> dict:
    user = getattr(request.state, "user", None) or {}
    user_id = user.get("sub", "default")
    try:
        image = await generate_and_store_image(
            prompt=body.prompt,
            user_id=user_id,
            workspace_id=body.workspace_id,
            size=body.size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc

    return {
        "documentId": image.document_id,
        "fileName": image.file_name,
        "imageUrl": image.download_url,
        "provider": image.provider,
        "revisedPrompt": image.revised_prompt,
    }
