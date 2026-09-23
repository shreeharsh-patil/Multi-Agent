import base64
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from src.config import settings
from src.models.document import Document
from src.utils.logger import logger


UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Cloudflare Workers AI image models.
MODEL_FLUX_2_KLEIN_9B = "@cf/black-forest-labs/flux-2-klein-9b"
MODEL_FLUX_2_KLEIN_4B = "@cf/black-forest-labs/flux-2-klein-4b"
MODEL_FLUX_1_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
MODEL_SDXL_LIGHTNING = "@cf/bytedance/stable-diffusion-xl-lightning"
_FLUX2_MULTIPART_MODELS = {MODEL_FLUX_2_KLEIN_9B, MODEL_FLUX_2_KLEIN_4B}
_SUPPORTED_IMAGE_PROVIDERS = {"auto", "cloudflare", "openai", "stability", "pollinations"}


@dataclass
class GeneratedImage:
    document_id: str
    file_name: str
    download_url: str
    provider: str
    model: str
    revised_prompt: str | None = None
    drive_file_id: str | None = None
    drive_web_view_link: str | None = None


def _parse_size(size: str) -> tuple[int, int]:
    width, height = 1024, 1024
    if "x" in size:
        parts = size.lower().split("x", 1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            width, height = int(parts[0]), int(parts[1])
    # Keep provider requests within Cloudflare's documented dimensions and
    # avoid accidentally allocating extremely large buffers from user input.
    return max(256, min(width, 1920)), max(256, min(height, 1920))


def _detect_image_format(image_bytes: bytes) -> tuple[str, str]:
    """Validate provider output and return (extension, mime type)."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp", "image/webp"
    raise RuntimeError("Image provider returned data that is not a supported PNG, JPEG, or WebP image")


def _decode_base64_image(value: str) -> bytes:
    raw = value.strip()
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise RuntimeError("Image provider returned invalid base64 image data") from exc
    _detect_image_format(image_bytes)
    return image_bytes


def _extract_cloudflare_image(response: httpx.Response) -> bytes:
    content_type = response.headers.get("content-type", "").lower()
    content = response.content

    if "application/json" in content_type or content.lstrip().startswith(b"{"):
        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError("Cloudflare returned malformed JSON") from exc
        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, dict) and isinstance(result.get("image"), str):
            return _decode_base64_image(result["image"])
        if isinstance(result, str):
            return _decode_base64_image(result)
        raise RuntimeError("Cloudflare returned no image in the response")

    if content_type.startswith("image/") and content:
        _detect_image_format(content)
        return content
    raise RuntimeError(f"Cloudflare returned an unexpected content type: {content_type or 'unknown'}")


class ImageGenerationService:
    """Cloudflare Workers AI image generation with model/key fallback.

    FLUX.2 Klein 9B/4B require multipart form data. Older Workers AI image
    models still accept JSON, so request encoding is chosen per model.
    """

    def __init__(self):
        self.account_ids = [a.strip() for a in settings.cloudflare_account_id.split(",") if a.strip()]
        self.api_tokens = [t.strip() for t in settings.cloudflare_api_token.split(",") if t.strip()]
        self.key_pairs = list(zip(self.account_ids, self.api_tokens))

    async def _call_cloudflare_model(
        self,
        account_id: str,
        token: str,
        model: str,
        prompt: str,
        width: int,
        height: int,
        seed: Optional[int],
        input_images: Optional[list],
    ) -> bytes:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        auth_headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=75, follow_redirects=True) as http:
            if model in _FLUX2_MULTIPART_MODELS:
                multipart: list[tuple[str, tuple]] = [
                    ("prompt", (None, prompt)),
                    ("width", (None, str(width))),
                    ("height", (None, str(height))),
                ]
                if seed is not None:
                    multipart.append(("seed", (None, str(seed))))
                for index, image in enumerate((input_images or [])[:4]):
                    if isinstance(image, str):
                        image_bytes = _decode_base64_image(image)
                    elif isinstance(image, (bytes, bytearray)):
                        image_bytes = bytes(image)
                        _detect_image_format(image_bytes)
                    else:
                        continue
                    multipart.append(
                        (f"input_image_{index}", (f"input-{index}.png", image_bytes, "image/png"))
                    )
                response = await http.post(
                    url,
                    headers={**auth_headers, "Accept": "application/json"},
                    files=multipart,
                )
            else:
                payload: dict[str, Any] = {"prompt": prompt, "width": width, "height": height}
                if seed is not None:
                    payload["seed"] = seed
                if input_images:
                    payload["image"] = input_images[0]
                response = await http.post(
                    url,
                    headers={
                        **auth_headers,
                        "Content-Type": "application/json",
                        "Accept": "image/png, application/json",
                    },
                    json=payload,
                )

        if response.status_code >= 400:
            detail = ""
            try:
                payload = response.json()
                errors = payload.get("errors") if isinstance(payload, dict) else None
                if isinstance(errors, list) and errors:
                    detail = str(errors[0].get("message") or "") if isinstance(errors[0], dict) else str(errors[0])
            except Exception:
                pass
            suffix = f": {detail[:200]}" if detail else ""
            raise RuntimeError(f"Cloudflare image model {model} failed with HTTP {response.status_code}{suffix}")

        return _extract_cloudflare_image(response)

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        aspect_ratio: str = "1:1",
        seed: Optional[int] = None,
        input_images: Optional[list] = None,
        allow_public_fallback: bool = True,
    ) -> dict[str, Any]:
        """Generate through Cloudflare, optionally falling back to Pollinations."""
        del aspect_ratio  # width/height are the provider inputs used today.
        start_t = time.time()
        target_model = model or MODEL_FLUX_2_KLEIN_9B
        fallback_models = [
            target_model,
            MODEL_FLUX_2_KLEIN_9B,
            MODEL_FLUX_2_KLEIN_4B,
            MODEL_FLUX_1_SCHNELL,
            MODEL_SDXL_LIGHTNING,
        ]
        models_to_try: list[str] = []
        for candidate in fallback_models:
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        if not self.key_pairs:
            if allow_public_fallback:
                return await self._generate_pollinations_fallback(prompt, width, height, start_t)
            raise ValueError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are not configured")

        last_error: Exception | None = None
        for current_model in models_to_try:
            for account_id, token in self.key_pairs:
                try:
                    image_bytes = await self._call_cloudflare_model(
                        account_id,
                        token,
                        current_model,
                        prompt,
                        width,
                        height,
                        seed,
                        input_images,
                    )
                    elapsed_ms = round((time.time() - start_t) * 1000, 2)
                    logger.info(
                        "image_generation_complete",
                        extra={"provider": "cloudflare", "model": current_model, "elapsed_ms": elapsed_ms},
                    )
                    return {
                        "success": True,
                        "provider": "cloudflare",
                        "model": current_model,
                        "prompt": prompt,
                        "image": base64.b64encode(image_bytes).decode("utf-8"),
                        "width": width,
                        "height": height,
                        "generationTime": f"{elapsed_ms}ms",
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                    }
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Cloudflare image model failed; trying next route",
                        extra={"model": current_model, "error": str(exc)[:300]},
                    )

        if allow_public_fallback:
            logger.warning("All Cloudflare image routes failed; trying Pollinations", extra={"error": str(last_error)[:300]})
            return await self._generate_pollinations_fallback(prompt, width, height, start_t)
        raise RuntimeError(f"All configured Cloudflare image routes failed: {last_error}")

    async def _generate_pollinations_fallback(
        self,
        prompt: str,
        width: int,
        height: int,
        start_t: float,
    ) -> dict[str, Any]:
        image_bytes = await _generate_pollinations(prompt, width, height)
        elapsed_ms = round((time.time() - start_t) * 1000, 2)
        return {
            "success": True,
            "provider": "pollinations",
            "model": "flux",
            "prompt": prompt,
            "image": base64.b64encode(image_bytes).decode("utf-8"),
            "width": width,
            "height": height,
            "generationTime": f"{elapsed_ms}ms",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }


image_generation_service = ImageGenerationService()


def _openai_options(size: str) -> tuple[str, str]:
    model = settings.openai_image_model
    if model.startswith("dall-e"):
        allowed = {"1024x1024", "1792x1024", "1024x1792"}
        quality = settings.openai_image_quality if settings.openai_image_quality in {"standard", "hd"} else "standard"
    else:
        allowed = {"1024x1024", "1536x1024", "1024x1536"}
        quality = settings.openai_image_quality or "medium"
    return (size if size in allowed else "1024x1024"), quality


async def _generate_openai(prompt: str, size: str) -> tuple[bytes, str | None, str]:
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
    if not result.data:
        raise RuntimeError("OpenAI returned no image data")
    image = result.data[0]
    if image.b64_json:
        image_bytes = _decode_base64_image(image.b64_json)
    elif image.url:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as http:
            response = await http.get(image.url)
            response.raise_for_status()
            image_bytes = response.content
            _detect_image_format(image_bytes)
    else:
        raise RuntimeError("OpenAI returned no image payload")
    return image_bytes, image.revised_prompt, settings.openai_image_model


async def _generate_stability(prompt: str) -> tuple[bytes, str | None, str]:
    if not settings.stability_api_key:
        raise ValueError("STABILITY_API_KEY is not configured")

    headers = {"Authorization": f"Bearer {settings.stability_api_key}", "Accept": "image/*"}
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers=headers,
            files={"none": ("", b"")},
            data={"prompt": prompt, "output_format": "png"},
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Stability AI image generation failed ({response.status_code})")
    _detect_image_format(response.content)
    return response.content, None, "stable-image-core"


async def _generate_pollinations(prompt: str, width: int, height: int) -> bytes:
    encoded_prompt = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&model=flux&nologo=true"
    )
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as http:
        response = await http.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if not content_type.startswith("image/"):
        raise RuntimeError(f"Pollinations returned an unexpected content type: {content_type or 'unknown'}")
    _detect_image_format(response.content)
    return response.content


async def _enhance_image_prompt(prompt: str) -> str:
    """Transform a user request into a richer visual prompt when text LLMs are available."""
    clean = prompt.strip()
    try:
        from src.services.llm import llm_service

        expanded = await llm_service.generate(
            prompt=(
                f"Transform this user request into an elite, detailed image generation prompt: '{clean}'.\n"
                "Incorporate subject, environment, composition, lighting, camera perspective, "
                "textures, mood, atmosphere, and visual hierarchy."
            ),
            system_instruction=(
                "You are an expert AI Prompt Engineer. Output ONLY the enhanced visual prompt string "
                "with no quotes or conversation."
            ),
            max_output_tokens=150,
        )
        expanded_clean = expanded.strip().strip('"\'`')
        if len(expanded_clean) > 10:
            return expanded_clean
    except Exception as exc:
        # Image generation must remain usable even when the text provider is down.
        logger.warning("Image prompt enhancement failed; using original prompt", extra={"error": str(exc)[:300]})
    return clean


def _provider_order() -> list[str]:
    configured = (settings.image_provider or "auto").strip().lower()
    if configured not in _SUPPORTED_IMAGE_PROVIDERS:
        logger.warning("Unknown IMAGE_PROVIDER=%s; using auto", configured)
        configured = "auto"

    order: list[str] = []

    def add(name: str) -> None:
        if name not in order:
            order.append(name)

    if configured != "auto":
        add(configured)
    if settings.cloudflare_account_id and settings.cloudflare_api_token:
        add("cloudflare")
    if settings.openai_api_key:
        add("openai")
    if settings.stability_api_key:
        add("stability")
    add("pollinations")
    return order


async def _generate_from_provider(
    provider: str,
    prompt: str,
    size: str,
    width: int,
    height: int,
    model: Optional[str],
) -> tuple[bytes, str | None, str]:
    if provider == "cloudflare":
        result = await image_generation_service.generate_image(
            prompt=prompt,
            model=model or MODEL_FLUX_2_KLEIN_9B,
            width=width,
            height=height,
            allow_public_fallback=False,
        )
        return _decode_base64_image(result["image"]), None, str(result.get("model") or MODEL_FLUX_2_KLEIN_9B)
    if provider == "openai":
        return await _generate_openai(prompt, size)
    if provider == "stability":
        return await _generate_stability(prompt)
    if provider == "pollinations":
        return await _generate_pollinations(prompt, width, height), None, "flux"
    raise ValueError(f"Unsupported image provider: {provider}")


async def generate_and_store_image(
    prompt: str,
    user_id: str,
    workspace_id: Optional[str] = None,
    size: str = "1024x1024",
    model: Optional[str] = None,
    drive_access_token: Optional[str] = None,
    drive_refresh_token: Optional[str] = None,
) -> GeneratedImage:
    raw_prompt = prompt.strip()
    if not raw_prompt:
        raise ValueError("An image prompt is required")
    if len(raw_prompt) > 4000:
        raise ValueError("Image prompts are limited to 4000 characters")

    clean_prompt = await _enhance_image_prompt(raw_prompt)
    width, height = _parse_size(size)

    image_bytes: bytes | None = None
    revised_prompt: str | None = clean_prompt if clean_prompt != raw_prompt else None
    selected_provider = ""
    selected_model = ""
    failures: list[str] = []

    for provider in _provider_order():
        try:
            image_bytes, provider_revised_prompt, selected_model = await _generate_from_provider(
                provider,
                clean_prompt,
                size,
                width,
                height,
                model,
            )
            _detect_image_format(image_bytes)
            selected_provider = provider
            if provider_revised_prompt:
                revised_prompt = provider_revised_prompt
            break
        except Exception as exc:
            failures.append(f"{provider}: {type(exc).__name__}: {str(exc)[:180]}")
            logger.warning("Image provider failed; trying fallback", extra={"provider": provider, "error": str(exc)[:300]})

    if image_bytes is None:
        raise RuntimeError("All image providers failed. " + " | ".join(failures))

    extension, mime_type = _detect_image_format(image_bytes)
    file_name = f"generated-{uuid.uuid4().hex[:12]}.{extension}"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(image_bytes)

    drive_file_id = None
    drive_web_view_link = None
    if drive_access_token:
        try:
            from src.services.drive.service import DriveService

            drive = DriveService()
            drive_result = await drive.upload_file(
                access_token=drive_access_token,
                file_path=str(file_path),
                file_name=file_name,
                mime_type=mime_type,
                refresh_token=drive_refresh_token or "",
            )
            if isinstance(drive_result, dict):
                drive_file_id = drive_result.get("id")
                drive_web_view_link = drive_result.get("webViewLink")
        except Exception as exc:
            logger.warning("Failed to upload generated image to Drive", extra={"error": str(exc)[:300]})

    base64_payload = base64.b64encode(image_bytes).decode("utf-8") if len(image_bytes) <= 12 * 1024 * 1024 else None
    document = Document(
        user_id=user_id,
        file_name=file_name,
        file_type=extension,
        file_size=len(image_bytes),
        file_path=str(file_path),
        file_data_base64=base64_payload,
        status="ready",
        workspace_id=workspace_id,
        drive_file_id=drive_file_id,
        drive_web_view_link=drive_web_view_link,
    )
    await document.insert()
    document_id = str(document.id)

    return GeneratedImage(
        document_id=document_id,
        file_name=file_name,
        download_url=f"/api/documents/{document_id}/file",
        provider=selected_provider,
        model=selected_model,
        revised_prompt=revised_prompt,
        drive_file_id=drive_file_id,
        drive_web_view_link=drive_web_view_link,
    )
