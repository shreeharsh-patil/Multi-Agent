import base64

import pytest

from src.config import Settings
from src.orchestrator.router import AgentRouter
from src.services import image_generation as image_module
from src.services.image_generation import ImageGenerationService, MODEL_FLUX_2_KLEIN_9B


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image-payload"


def test_explicit_image_agent_selection_is_preserved():
    router = AgentRouter()

    assert router.route_smart("make something cinematic", "image") == "image"


def test_retired_groq_model_is_migrated_to_supported_qwen():
    configured = Settings(
        _env_file=None,
        debug=True,
        secret_key="diagnostic-secret-key",
        groq_model="qwen/qwen3.6-27b",
    )

    assert configured.groq_model == "qwen/qwen3.8-27b"


@pytest.mark.asyncio
async def test_flux2_uses_multipart_form_data(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        content = b"{}"

        def json(self):
            return {"result": {"image": base64.b64encode(PNG_BYTES).decode("ascii")}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(image_module.httpx, "AsyncClient", FakeClient)
    service = ImageGenerationService()

    image_bytes = await service._call_cloudflare_model(
        "account-id",
        "token",
        MODEL_FLUX_2_KLEIN_9B,
        "a cinematic mountain",
        1024,
        1024,
        None,
        None,
    )

    assert image_bytes == PNG_BYTES
    assert "files" in captured
    assert "json" not in captured
    fields = {name: value[1] for name, value in captured["files"] if value[0] is None}
    assert fields["prompt"] == "a cinematic mountain"
    assert fields["width"] == "1024"
    assert fields["height"] == "1024"


def test_invalid_provider_payload_is_rejected():
    with pytest.raises(RuntimeError, match="supported PNG, JPEG, or WebP"):
        image_module._detect_image_format(b"not-an-image")
