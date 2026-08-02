import base64
import uuid
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.config import settings
from src.models.document import Document
from src.utils.logger import logger


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


async def _generate_pollinations(prompt: str, size: str = "1024x1024", model: str = "flux") -> tuple[bytes, str | None]:
    """Generate image via 100% free Pollinations.ai API."""
    encoded_prompt = urllib.parse.quote(prompt)
    width, height = 1024, 1024
    if "x" in size:
        parts = size.split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            width, height = int(parts[0]), int(parts[1])

    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true"
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        response = await http.get(url)
        response.raise_for_status()
        return response.content, None


async def _generate_cloudflare(prompt: str) -> tuple[bytes, str | None]:
    """Generate image via Cloudflare Workers AI with strict matching Account ID & API Token rotation."""
    account_ids = [a.strip() for a in settings.cloudflare_account_id.split(",") if a.strip()]
    api_tokens = [t.strip() for t in settings.cloudflare_api_token.split(",") if t.strip()]

    if not account_ids or not api_tokens:
        raise ValueError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be configured")

    # Strictly pair Account ID #1 with API Token #1, Account ID #2 with API Token #2, etc.
    pairs = list(zip(account_ids, api_tokens))
    if not pairs:
        raise ValueError("No valid matching Cloudflare (Account ID, API Token) pairs found")

    last_error = None
    for acc_id, token in pairs:
        url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "image/png",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as http:
                response = await http.post(url, headers=headers, json={"prompt": prompt})
                if response.status_code < 400:
                    content_type = response.headers.get("content-type", "").lower()
                    content = response.content
                    if "application/json" in content_type or content.startswith(b"{"):
                        try:
                            data = response.json()
                            if isinstance(data, dict) and "result" in data:
                                res_val = data["result"]
                                if isinstance(res_val, dict) and "image" in res_val:
                                    return base64.b64decode(res_val["image"]), None
                                elif isinstance(res_val, str):
                                    return base64.b64decode(res_val), None
                        except Exception as parse_err:
                            logger.warning(f"Failed to parse Cloudflare JSON response: {parse_err}")
                    return content, None
                logger.warning(f"Cloudflare pair (Account: {acc_id[:6]}...) returned HTTP {response.status_code}, rotating to next matched pair...")
                last_error = f"HTTP {response.status_code}"
        except Exception as err:
            logger.warning(f"Cloudflare request failed for Account {acc_id[:6]}... ({err}), rotating to next matched pair...")
            last_error = str(err)

    raise RuntimeError(f"All configured Cloudflare key pairs failed. Last error: {last_error}")


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
        if settings.cloudflare_account_id and settings.cloudflare_api_token:
            provider = "cloudflare"
        elif settings.openai_api_key:
            provider = "openai"
        elif settings.stability_api_key:
            provider = "stability"
        else:
            provider = "pollinations"

    if provider == "cloudflare":
        try:
            image_bytes, revised_prompt = await _generate_cloudflare(clean_prompt)
        except Exception as e:
            logger.warning(f"Cloudflare Workers AI failed ({e}), falling back to Pollinations.ai")
            image_bytes, revised_prompt = await _generate_pollinations(clean_prompt, size)
            provider = "pollinations"
    elif provider == "openai":
        try:
            image_bytes, revised_prompt = await _generate_openai(clean_prompt, size)
        except Exception as e:
            logger.warning(f"OpenAI image generation failed ({e}), falling back to Pollinations.ai")
            image_bytes, revised_prompt = await _generate_pollinations(clean_prompt, size)
            provider = "pollinations"
    elif provider == "stability":
        try:
            image_bytes, revised_prompt = await _generate_stability(clean_prompt)
        except Exception as e:
            logger.warning(f"Stability AI image generation failed ({e}), falling back to Pollinations.ai")
            image_bytes, revised_prompt = await _generate_pollinations(clean_prompt, size)
            provider = "pollinations"
    else:
        image_bytes, revised_prompt = await _generate_pollinations(clean_prompt, size)
        provider = "pollinations"

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
