import pytest
from unittest.mock import AsyncMock, patch

from src.agents.knowledge.agent import KnowledgeAgent
from src.services.llm.base import BaseLLMProvider
from src.services.llm.rotator import RotatingProvider


class _PermanentFailureProvider(BaseLLMProvider):
    name = "permanent"

    def __init__(self):
        self.calls = 0

    async def generate(self, **kwargs):
        self.calls += 1
        raise RuntimeError("404 model_not_found")


class _SuccessfulProvider(BaseLLMProvider):
    name = "success"

    async def generate(self, **kwargs):
        return "ok"


class _PartialStreamProvider(BaseLLMProvider):
    name = "partial"

    async def generate(self, **kwargs):
        raise NotImplementedError

    async def generate_stream(self, **kwargs):
        yield "partial "
        raise RuntimeError("503 stream interrupted")


class _UnexpectedFallbackProvider(BaseLLMProvider):
    name = "must-not-run"

    def __init__(self):
        self.calls = 0

    async def generate(self, **kwargs):
        raise NotImplementedError

    async def generate_stream(self, **kwargs):
        self.calls += 1
        yield "duplicate"


@pytest.mark.asyncio
async def test_permanent_provider_error_falls_back_without_retries():
    failed = _PermanentFailureProvider()
    provider = RotatingProvider([failed, _SuccessfulProvider()])

    assert await provider.generate("hello") == "ok"
    assert failed.calls == 1


@pytest.mark.asyncio
async def test_partial_stream_is_not_replayed_by_another_provider():
    fallback = _UnexpectedFallbackProvider()
    provider = RotatingProvider([_PartialStreamProvider(), fallback])
    chunks = []

    with pytest.raises(RuntimeError, match="stream interrupted"):
        async for chunk in provider.generate_stream("hello"):
            chunks.append(chunk)

    assert chunks == ["partial "]
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_ordinary_knowledge_chat_does_not_initialize_retrieval():
    with patch("src.services.llm.llm_service.generate", new=AsyncMock(return_value="hello")) as generate:
        result = await KnowledgeAgent().execute("hello", {"user_id": "u1"})

    assert result.success is True
    assert result.output == "hello"
    generate.assert_awaited_once()
