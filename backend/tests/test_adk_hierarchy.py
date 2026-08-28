import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.metadata import AgentDepartment, AgentMetadata
from src.agents.registry import AgentRegistry
from src.adk.agents import (
    create_boss_agent,
    get_boss_agent,
    get_adk_hierarchy_summary,
    build_all_adk_specialists,
    create_adk_specialist,
    safe_adk_name,
    adk_name_to_registry_id,
    registry_id_to_adk_name,
    reset_adk_agent_tree,
    SPECIALIST_FACTORIES,
    ADK_TOOL_MAP,
)
from src.adk.runner import (
    get_adk_status,
    execute_adk_specialists_batch,
    _format_agent_trace,
)
from src.config import settings


@pytest.fixture(autouse=True)
def setup_registry_and_adk():
    """Ensure clean registry and ADK tree for every test."""
    AgentRegistry.initialize(force=True)
    reset_adk_agent_tree()
    yield
    reset_adk_agent_tree()


def test_registry_enabled_count_greater_than_100():
    """Test 1: AgentRegistry enabled count must be > 100."""
    all_metadata = AgentRegistry.get_all_metadata()
    enabled_meta = [m for m in all_metadata if m.enabled]
    assert len(enabled_meta) >= 100, f"Expected >= 100 enabled agents, got {len(enabled_meta)}"
    assert len(enabled_meta) == 179, f"Expected 179 enabled agents, got {len(enabled_meta)}"


def test_adk_leaf_agent_count_greater_than_100():
    """Test 2: ADK leaf agent count must be > 100."""
    specialists = build_all_adk_specialists()
    assert len(specialists) >= 100, f"Expected >= 100 ADK leaf agents, got {len(specialists)}"
    assert len(specialists) == 179, f"Expected 179 ADK leaf agents, got {len(specialists)}"


def test_every_enabled_registry_specialist_maps_to_adk():
    """Test 3: Every enabled registry specialist maps to an ADK specialist."""
    specialists = build_all_adk_specialists()
    enabled_meta = [m for m in AgentRegistry.get_all_metadata() if m.enabled]
    for meta in enabled_meta:
        assert meta.id in specialists, f"Registry specialist '{meta.id}' not found in ADK specialists"
        adk_agent = specialists[meta.id]
        assert adk_agent is not None
        assert adk_agent.name == safe_adk_name(meta.id)


def test_every_adk_specialist_name_is_unique():
    """Test 4: Every ADK specialist name is strictly unique."""
    specialists = build_all_adk_specialists()
    names = [agent.name for agent in specialists.values()]
    assert len(names) == len(set(names)), "Duplicate ADK specialist names detected!"


def test_exactly_ten_department_managers_exist():
    """Test 5 & 6: There are exactly 10 department managers matching AgentDepartment enum."""
    boss = get_boss_agent()
    managers = boss.sub_agents
    assert len(managers) == 10, f"Expected 10 department managers, got {len(managers)}"

    expected_manager_names = {
        "command_planning_manager",
        "coding_manager",
        "research_manager",
        "content_manager",
        "visual_manager",
        "data_manager",
        "product_department_manager",
        "ai_ml_manager",
        "automation_manager",
        "business_quality_manager",
    }
    actual_manager_names = {m.name for m in managers}
    assert actual_manager_names == expected_manager_names


def test_every_specialist_belongs_to_exactly_one_manager():
    """Test 7: Every specialist belongs to exactly one department manager or division manager."""
    boss = get_boss_agent()
    seen_specialists: set[str] = set()

    for manager in boss.sub_agents:
        for sub in manager.sub_agents:
            if hasattr(sub, "sub_agents") and sub.sub_agents:
                for leaf in sub.sub_agents:
                    assert leaf.name not in seen_specialists, (
                        f"Specialist '{leaf.name}' found in multiple managers!"
                    )
                    seen_specialists.add(leaf.name)
            else:
                assert sub.name not in seen_specialists, (
                    f"Specialist '{sub.name}' found in multiple department managers!"
                )
                seen_specialists.add(sub.name)

    specialists = build_all_adk_specialists()
    assert len(seen_specialists) == len(specialists), (
        f"Expected {len(specialists)} total assigned specialists, got {len(seen_specialists)}"
    )


def test_registry_and_adk_counts_do_not_diverge():
    """Test 8: Registry count and ADK count do not silently diverge."""
    summary = get_adk_hierarchy_summary()
    assert summary["registry_agents"] == 179
    assert summary["adk_specialists"] == 179
    assert summary["department_managers"] == 10
    assert summary["division_managers"] == 1
    assert summary["total_adk_nodes"] == 191
    assert sum(summary["departments"].values()) == 179


def test_hierarchy_caching_and_reset():
    """Test 13: The hierarchy is cached and reset_adk_agent_tree resets the cache."""
    boss1 = get_boss_agent()
    boss2 = get_boss_agent()
    assert boss1 is boss2, "get_boss_agent() must return the cached singleton instance"

    reset_adk_agent_tree()
    boss3 = get_boss_agent()
    assert boss3 is not None
    assert boss3 is not boss1, "reset_adk_agent_tree() must rebuild a fresh hierarchy instance"


def test_disabled_agents_are_not_exposed():
    """Test 12: Disabled agents in registry are excluded from ADK hierarchy."""
    # Find one metadata and disable it
    meta = AgentRegistry.get_metadata("coding")
    if meta:
        meta.enabled = False
        reset_adk_agent_tree()
        specialists = build_all_adk_specialists()
        assert "coding" not in specialists
        meta.enabled = True
        reset_adk_agent_tree()


def test_tool_enabled_agents_retain_tools():
    """Test 14: Handcrafted tool-enabled agents retain their tools."""
    specialists = build_all_adk_specialists()

    knowledge_agent = specialists.get("knowledge")
    assert knowledge_agent is not None
    assert len(knowledge_agent.tools) >= 1
    assert any("knowledge_search" in getattr(t, "name", str(t)) or "knowledge" in str(t) for t in knowledge_agent.tools)

    drive_agent = specialists.get("drive")
    assert drive_agent is not None
    assert len(drive_agent.tools) >= 4

    calendar_agent = specialists.get("calendar")
    assert calendar_agent is not None
    assert len(calendar_agent.tools) >= 2


def test_safe_name_bidirectional_mapping():
    """Test safe ADK name bidirectional conversion."""
    reg_id = "supreme-commander"
    adk_name = safe_adk_name(reg_id)
    assert adk_name == "supreme_commander"
    assert adk_name_to_registry_id(adk_name) == reg_id
    assert registry_id_to_adk_name(reg_id) == adk_name


def test_format_agent_trace():
    """Test 17: Trace telemetry properly resolves registry info and departments."""
    trace = _format_agent_trace("coding_manager", "StartEvent", True)
    assert trace["department"] == "Department Management"

    trace_sp = _format_agent_trace("frontend_developer", "AgentEvent", True)
    assert trace_sp["registry_id"] == "frontend-developer"
    assert trace_sp["department"] == "Coding"
    assert trace_sp["name"] == "Frontend Developer"

    trace_sup = _format_agent_trace("supreme_commander", "AgentEvent", True)
    assert trace_sup["registry_id"] == "supreme-commander"
    assert trace_sup["department"] == "Command and Planning"
    assert trace_sup["name"] == "Supreme Commander"


@pytest.mark.asyncio
async def test_massive_mode_batch_execution_concurrency():
    """Test 15: Massive mode supports executing >100 specialists with bounded concurrency."""
    all_metadata = AgentRegistry.get_all_metadata()
    total_count = len(all_metadata)
    assert total_count >= 100
    assert total_count == 179

    # Create mock task items for all registered specialists
    tasks = [{"agent_id": m.id, "prompt": "Status check", "context": {}} for m in all_metadata]
    assert len(tasks) == total_count

    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value=MagicMock(success=True, output="Verified", citations=[]))

    with patch("src.agents.registry.AgentRegistry.get_agent", return_value=mock_agent):
        results = await execute_adk_specialists_batch(tasks, max_concurrency=8)
        assert len(results) == total_count
        assert all(r["success"] for r in results)
        assert mock_agent.execute.call_count == total_count


def test_adk_status_telemetry():
    """Test 16: get_adk_status() telemetry reporting."""
    status = get_adk_status()
    assert "registry_agents" in status
    assert status["registry_agents"] == 179
    assert status["adk_specialists"] == 179
    assert status["internet_intelligence_agents"] == 48
    assert status["department_managers"] == 10
    assert status["division_managers"] == 1
    assert status["total_adk_nodes"] == 191
    assert "departments" in status
    assert len(status["departments"]) == 10
