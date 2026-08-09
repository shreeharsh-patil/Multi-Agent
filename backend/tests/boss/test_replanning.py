import pytest
from src.orchestrator.boss import BossAgent, TaskGraph, TaskNode, TaskMemoryManager


@pytest.mark.asyncio
async def test_uncertainty_triggers_replanning():
    """Verify low confidence output triggers dynamic replanning with verification-agent."""
    boss = BossAgent()
    graph = TaskGraph(task_id="t_replan", user_request="Complex architectural query", complexity="complex")
    graph.nodes["api-architect"] = TaskNode(id="api-architect", title="Architecture", agent_id="api-architect", objective="Design API", status="completed")

    memory = TaskMemoryManager("t_replan", "Complex architectural query")
    memory.record_result("api-architect", "Draft API design", confidence=0.5, conf_level="low")

    eval_result = await boss._evaluate_results("Complex architectural query", graph, memory)

    assert eval_result["passed"] is False
    assert "Uncertainty detected" in eval_result["reason"]
    assert any(task["agent_id"] == "verification-agent" for task in eval_result["new_subtasks"])


@pytest.mark.asyncio
async def test_failed_agent_triggers_red_team_audit():
    """Verify failed subtask triggers dynamic replanning with red-team-critic."""
    boss = BossAgent()
    graph = TaskGraph(task_id="t_fail_audit", user_request="Build high security auth app", complexity="complex")
    graph.nodes["backend-developer"] = TaskNode(id="backend-developer", title="Backend Auth", agent_id="backend-developer", objective="Implement Auth", status="failed", error="Auth failure")

    memory = TaskMemoryManager("t_fail_audit", "Build high security auth app")

    eval_result = await boss._evaluate_results("Build high security auth app", graph, memory)

    assert eval_result["passed"] is False
    assert any(task["agent_id"] == "red-team-critic" for task in eval_result["new_subtasks"])
