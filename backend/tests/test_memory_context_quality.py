from unittest.mock import AsyncMock

import pytest

from src.services.memory.service import MemoryService


@pytest.mark.asyncio
async def test_build_context_returns_relevant_high_confidence_memories():
    service = MemoryService()
    service.search = AsyncMock(return_value=[
        {
            "content": "Prefers concise explanations with practical examples",
            "metadata": {"confidence": 0.9, "category": "communication"},
        },
        {
            "content": "Unreliable low-confidence detail",
            "metadata": {"confidence": 0.2, "category": "general"},
        },
    ])

    context = await service.build_context("user-1", "How should you explain this?")

    assert "Prefers concise explanations with practical examples" in context
    assert "Unreliable low-confidence detail" not in context
    assert "Current user message" in context
    service.search.assert_awaited_once_with("user-1", "How should you explain this?", 5)


@pytest.mark.asyncio
async def test_build_context_fails_open_when_memory_search_errors():
    service = MemoryService()
    service.search = AsyncMock(side_effect=RuntimeError("vector store unavailable"))

    assert await service.build_context("user-1", "hello") == ""
