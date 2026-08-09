import pytest
from src.services.image_generation import (
    MODEL_FLUX_2_KLEIN_9B,
    MODEL_FLUX_2_KLEIN_4B,
    MODEL_FLUX_1_SCHNELL,
    MODEL_SDXL_LIGHTNING,
    ImageGenerationService,
)


def test_flux_model_constants():
    """Verify Cloudflare Workers AI model constants match official specifications."""
    assert MODEL_FLUX_2_KLEIN_9B == "@cf/black-forest-labs/flux-2-klein-9b"
    assert MODEL_FLUX_2_KLEIN_4B == "@cf/black-forest-labs/flux-2-klein-4b"
    assert MODEL_FLUX_1_SCHNELL == "@cf/black-forest-labs/flux-1-schnell"


@pytest.mark.asyncio
async def test_image_service_model_fallback():
    """Verify ImageGenerationService handles model routing and fallback sequence."""
    service = ImageGenerationService()
    # Test fallback call with prompt
    res = await service.generate_image("A majestic lion in the savannah", model=MODEL_FLUX_2_KLEIN_9B)
    assert res["success"] is True
    assert "model" in res
    assert "image" in res
    assert "createdAt" in res
