import base64
import uuid
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any

import httpx

from src.config import settings
from src.models.document import Document
from src.utils.logger import logger


UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Cloudflare Workers AI FLUX Model Strategy Constants
MODEL_FLUX_2_KLEIN_9B = "@cf/black-forest-labs/flux-2-klein-9b"
MODEL_FLUX_2_KLEIN_4B = "@cf/black-forest-labs/flux-2-klein-4b"
MODEL_FLUX_1_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
MODEL_SDXL_LIGHTNING = "@cf/bytedance/stable-diffusion-xl-lightning"


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


class ImageGenerationService:
    """Production-quality ImageGenerationService supporting Cloudflare Workers AI models:
    - Primary High-Quality Model: @cf/black-forest-labs/flux-2-klein-9b
    - Fast / Low-Cost Model: @cf/black-forest-labs/flux-2-klein-4b
    - Fallback Model: @cf/black-forest-labs/flux-1-schnell
    """

    def __init__(self):
        self.account_ids = [a.strip() for a in settings.cloudflare_account_id.split(",") if a.strip()]
        self.api_tokens = [t.strip() for t in settings.cloudflare_api_token.split(",") if t.strip()]
        self.key_pairs = list(zip(self.account_ids, self.api_tokens))

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        aspect_ratio: str = "1:1",
        seed: Optional[int] = None,
        input_images: Optional[list] = None,
    ) -> dict[str, Any]:
        """Generates an image via Cloudflare Workers AI with model routing & automatic fallback sequence."""
        start_t = time.time()
        target_model = model or MODEL_FLUX_2_KLEIN_9B

        # Model Fallback Order
        fallback_models = [
            target_model,
            MODEL_FLUX_2_KLEIN_9B,
            MODEL_FLUX_2_KLEIN_4B,
            MODEL_FLUX_1_SCHNELL,
            MODEL_SDXL_LIGHTNING,
        ]
        # Deduplicate while preserving order
        models_to_try = []
        for m in fallback_models:
            if m not in models_to_try:
                models_to_try.append(m)

        if not self.key_pairs:
            logger.warning("Cloudflare credentials missing, attempting Pollinations.ai fallback")
            return await self._generate_pollinations_fallback(prompt, width, height, start_t)

        last_error = None
        for current_model in models_to_try:
            for acc_id, token in self.key_pairs:
                url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/ai/run/{current_model}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "image/png",
                }
                payload: dict[str, Any] = {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                }
                if seed is not None:
                    payload["seed"] = seed
                if input_images:
                    payload["image"] = input_images[0]

                try:
                    async with httpx.AsyncClient(timeout=60) as http:
                        response = await http.post(url, headers=headers, json=payload)
                        if response.status_code < 400:
                            content_type = response.headers.get("content-type", "").lower()
                            content = response.content
                            img_b64 = None

                            if "application/json" in content_type or content.startswith(b"{"):
                                try:
                                    data = response.json()
                                    if isinstance(data, dict) and "result" in data:
                                        res_val = data["result"]
                                        if isinstance(res_val, dict) and "image" in res_val:
                                            img_b64 = res_val["image"]
                                        elif isinstance(res_val, str):
                                            img_b64 = res_val
                                except Exception as json_err:
                                    logger.warning(f"Failed to parse Cloudflare JSON: {json_err}")

                            if not img_b64 and content:
                                img_b64 = base64.b64encode(content).decode("utf-8")

                            if img_b64:
                                elapsed_ms = round((time.time() - start_t) * 1000, 2)
                                logger.info(f"Successfully generated image via Cloudflare model {current_model} in {elapsed_ms}ms")
                                return {
                                    "success": True,
                                    "model": current_model,
                                    "prompt": prompt,
                                    "image": img_b64,
                                    "width": width,
                                    "height": height,
                                    "generationTime": f"{elapsed_ms}ms",
                                    "createdAt": datetime.now(timezone.utc).isoformat(),
                                }

                        logger.warning(f"Model {current_model} returned HTTP {response.status_code}, trying fallback model...")
                        last_error = f"HTTP {response.status_code} on model {current_model}"
                except Exception as err:
                    logger.warning(f"Cloudflare model {current_model} call failed ({err}), trying fallback...")
                    last_error = str(err)

        logger.warning(f"All Cloudflare Workers AI models failed ({last_error}), switching to Pollinations.ai fallback")
        return await self._generate_pollinations_fallback(prompt, width, height, start_t)

    async def _generate_pollinations_fallback(self, prompt: str, width: int, height: int, start_t: float) -> dict[str, Any]:
        """Fallback to free Pollinations.ai API if Cloudflare is unreachable."""
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
            response = await http.get(url)
            response.raise_for_status()
            img_b64 = base64.b64encode(response.content).decode("utf-8")
            elapsed_ms = round((time.time() - start_t) * 1000, 2)
            return {
                "success": True,
                "model": "pollinations-flux-fallback",
                "prompt": prompt,
                "image": img_b64,
                "width": width,
                "height": height,
                "generationTime": f"{elapsed_ms}ms",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }


image_generation_service = ImageGenerationService()


async def _enhance_image_prompt(prompt: str) -> str:
    """Intelligently transforms user image request into a high-quality visual prompt."""
    raw = prompt.strip()
    clean = raw

    # Expand short prompts into cinematic visual descriptions
    try:
        from src.services.llm import llm_service
        expanded = await llm_service.generate(
            prompt=(
                f"Transform this user request into an elite, detailed image generation prompt: '{clean}'.\n"
                f"Incorporate: subject, environment, composition, lighting, camera perspective, textures, mood, atmosphere, and visual hierarchy."
            ),
            system_instruction=(
                "You are an expert AI Prompt Engineer for FLUX.2 models. Output ONLY the enhanced visual prompt string with no quotes or conversation."
            ),
            max_output_tokens=150,
        )
        expanded_clean = expanded.strip().strip('"\'`')
        if expanded_clean and len(expanded_clean) > 10:
            return expanded_clean
    except Exception as err:
        logger.warning(f"Prompt enhancement failed: {err}")

    return clean


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

    clean_prompt = await _enhance_image_prompt(raw_prompt)

    width, height = 1024, 1024
    if "x" in size:
        parts = size.split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            width, height = int(parts[0]), int(parts[1])

    # Call ImageGenerationService
    gen_result = await image_generation_service.generate_image(
        prompt=clean_prompt,
        model=model or MODEL_FLUX_2_KLEIN_9B,
        width=width,
        height=height,
    )

    image_bytes = base64.b64decode(gen_result["image"])
    file_name = f"generated-{uuid.uuid4().hex[:12]}.png"
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
                mime_type="image/png",
                refresh_token=drive_refresh_token or "",
            )
        except Exception as err:
            logger.warning(f"Failed to upload generated image to Drive: {err}")

    import base64
    base64_payload = base64.b64encode(image_bytes).decode("utf-8") if len(image_bytes) <= 12 * 1024 * 1024 else None

    document = Document(
        user_id=user_id,
        file_name=file_name,
        file_type="png",
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
        provider="cloudflare_workers_ai",
        model=gen_result.get("model", MODEL_FLUX_2_KLEIN_9B),
        revised_prompt=clean_prompt,
        drive_file_id=drive_file_id,
        drive_web_view_link=drive_web_view_link,
    )
