from unittest.mock import AsyncMock

import pytest
from src.orchestrator.router import AgentRouter
from src.services import image_generation
from src.services.rag.ocr import analyze_image


def test_image_prompts_route_to_image_agent():
    assert AgentRouter().route("Create an image of a solar-powered city") == "image"


def test_dalle_options_use_supported_quality(monkeypatch):
    monkeypatch.setattr(image_generation.settings, "openai_image_model", "dall-e-3")
    monkeypatch.setattr(image_generation.settings, "openai_image_quality", "medium")
    assert image_generation._openai_options("1792x1024") == ("1792x1024", "standard")


@pytest.mark.asyncio
async def test_generated_image_is_persisted_as_document(monkeypatch, tmp_path):
    monkeypatch.setattr(image_generation.settings, "image_provider", "openai")
    monkeypatch.setattr(image_generation.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(image_generation, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        image_generation,
        "_generate_openai",
        AsyncMock(return_value=(b"png-data", "A revised prompt")),
    )

    class FakeDocument:
        def __init__(self, **values):
            self.__dict__.update(values)
            self.id = "507f1f77bcf86cd799439011"

        async def insert(self):
            return self

    monkeypatch.setattr(image_generation, "Document", FakeDocument)
    result = await image_generation.generate_and_store_image("A clean product sketch", "user-1")

    assert result.provider == "openai"
    assert result.revised_prompt == "A revised prompt"
    assert result.download_url.endswith("/download")
    assert (tmp_path / result.file_name).read_bytes() == b"png-data"


@pytest.mark.asyncio
async def test_image_analysis_uses_multimodal_provider(monkeypatch):
    generate = AsyncMock(return_value="Extracted text: Total 42")
    monkeypatch.setattr("src.services.rag.ocr.llm_service.generate_multimodal", generate)

    result = await analyze_image(b"image", "image/png", "receipt.png")

    assert result == "Extracted text: Total 42"
    assert generate.await_args.args[1:] == (b"image", "image/png")
