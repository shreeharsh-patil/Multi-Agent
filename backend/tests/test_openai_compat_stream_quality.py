from types import SimpleNamespace

import pytest

from src.services.llm.openai_compat import OpenAICompatibleProvider


class _Completions:
    def __init__(self, stream_factory):
        self.stream_factory = stream_factory
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return self.stream_factory()


class _Client:
    def __init__(self, stream_factory):
        self.chat = SimpleNamespace(completions=_Completions(stream_factory))


def _chunk(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))],
    )


async def _partial_then_fail():
    yield _chunk("partial ")
    raise RuntimeError("503 stream interrupted")


async def _unexpected_second_stream():
    yield _chunk("duplicate")


async def _fail_before_output():
    raise RuntimeError("429 rate limit")
    yield  # pragma: no cover - keeps this an async generator


async def _successful_stream():
    yield _chunk("ok")


def _provider(first_factory, second_factory):
    provider = OpenAICompatibleProvider(
        name="test-provider",
        api_key="first,second",
        model="test-model",
        base_url="https://example.invalid/v1",
    )
    first = _Client(first_factory)
    second = _Client(second_factory)
    provider.clients = [("first", first), ("second", second)]
    provider._initialized = True
    return provider, first, second


@pytest.mark.asyncio
async def test_partial_stream_failure_is_not_replayed_with_another_key():
    provider, first, second = _provider(_partial_then_fail, _unexpected_second_stream)
    chunks = []

    with pytest.raises(RuntimeError, match="stream interrupted"):
        async for chunk in provider.generate_stream("hello"):
            chunks.append(chunk)

    assert chunks == ["partial "]
    assert first.chat.completions.calls == 1
    assert second.chat.completions.calls == 0


@pytest.mark.asyncio
async def test_failure_before_output_can_fall_back_to_another_key():
    provider, first, second = _provider(_fail_before_output, _successful_stream)
    chunks = []

    async for chunk in provider.generate_stream("hello"):
        chunks.append(chunk)

    assert chunks == ["ok"]
    assert first.chat.completions.calls == 1
    assert second.chat.completions.calls == 1
    assert provider._current_idx == 1
