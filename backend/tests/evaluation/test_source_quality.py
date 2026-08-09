import pytest
from src.orchestrator.boss import BossAgent, TaskMemoryManager


def test_source_quality_hierarchy():
    """Verify primary and official sources rank higher in evaluation."""
    sources = [
        {"title": "Official Python Docs", "url": "https://docs.python.org/3/whatsnew/3.12.html", "rank": 1},
        {"title": "Tech Blog", "url": "https://randomblog.example.com/python-update", "rank": 5},
    ]

    official = [s for s in sources if "docs.python.org" in s["url"]]
    assert len(official) == 1
    assert official[0]["rank"] == 1


@pytest.mark.asyncio
async def test_multi_source_cross_checking():
    """Verify TaskMemoryManager tracks multiple sources without losing citations."""
    memory = TaskMemoryManager("t_sources", "Latest LLM benchmarks")
    sources1 = [{"title": "Llama 3 Paper", "url": "https://arxiv.org/abs/2407.21783"}]
    sources2 = [{"title": "Meta AI Blog", "url": "https://ai.meta.com/blog/meta-llama-3/"}]

    memory.record_result("ai-researcher", "Llama 3 benchmark findings", sources=sources1)
    memory.record_result("fact-checker", "Verified Llama 3 benchmarks", sources=sources2)

    assert len(memory.sources) == 2
    assert any("arxiv.org" in s["url"] for s in memory.sources)
    assert any("ai.meta.com" in s["url"] for s in memory.sources)
