"""Image generation with OpenAI and Stability AI backends."""

import base64
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.config import settings
from src.models.document import Document


UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class GeneratedImage:
    document_id: str
    file_name: str
    download_url: str
    provider: str
    revised_prompt: str | None = None


def _openai_options(size: str) -> tuple[str, str]:
    model = settings.openai_image_model
    if model.startswith("dall-e"):
        allowed = {"1024x1024", "1792x1024", "1024x1792"}
        quality = settings.openai_image_quality if settings.openai_image_quality in {"standard", "hd"} else "standard"
    else:
        allowed = {"1024x1024", "1536x1024", "1024x1536"}
        quality = settings.openai_image_quality
    return (size if size in allowed else "1024x1024"), quality


async def _generate_openai(prompt: str, size: str) -> tuple[bytes, str | None]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resolved_size, quality = _openai_options(size)
    result = await client.images.generate(
        model=settings.openai_image_model,
        prompt=prompt,
        size=resolved_size,
        quality=quality,
        n=1,
    )
    image = result.data[0]
    if image.b64_json:
        return base64.b64decode(image.b64_json), image.revised_prompt
    if image.url:
        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.get(image.url)
            response.raise_for_status()
            return response.content, image.revised_prompt
    raise RuntimeError("The image provider returned no image data")


async def _generate_stability(prompt: str) -> tuple[bytes, str | None]:
    if not settings.stability_api_key:
        raise ValueError("STABILITY_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.stability_api_key}",
        "Accept": "image/*",
    }
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers=headers,
            files={"none": ("", b"")},
            data={"prompt": prompt, "output_format": "png"},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Stability AI image generation failed ({response.status_code})")
        return response.content, None


async def generate_and_store_image(
    prompt: str,
    user_id: str,
    workspace_id: str | None = None,
    size: str = "1024x1024",
) -> GeneratedImage:
    clean_prompt = prompt.strip()
    if not clean_prompt:
        raise ValueError("An image prompt is required")
    if len(clean_prompt) > 4000:
        raise ValueError("Image prompts are limited to 4000 characters")

    provider = settings.image_provider.lower()
    if provider == "auto":
        if settings.openai_api_key:
            provider = "openai"
        elif settings.stability_api_key:
            provider = "stability"
        else:
            raise ValueError("Configure OPENAI_API_KEY or STABILITY_API_KEY for image generation")

    if provider == "openai":
        image_bytes, revised_prompt = await _generate_openai(clean_prompt, size)
    elif provider == "stability":
        image_bytes, revised_prompt = await _generate_stability(clean_prompt)
    else:
        raise ValueError("IMAGE_PROVIDER must be auto, openai, or stability")

    file_name = f"generated-{uuid.uuid4().hex[:12]}.png"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(image_bytes)
    document = Document(
        user_id=user_id,
        file_name=file_name,
        file_type="png",
        file_size=len(image_bytes),
        file_path=str(file_path),
        status="ready",
        workspace_id=workspace_id,
    )
    await document.insert()
    document_id = str(document.id)
    return GeneratedImage(
        document_id=document_id,
        file_name=file_name,
        download_url=f"/api/documents/{document_id}/download",
        provider=provider,
        revised_prompt=revised_prompt,
    )
