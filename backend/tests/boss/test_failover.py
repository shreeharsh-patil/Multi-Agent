import pytest
from src.orchestrator.boss import BossAgent, TaskGraph, TaskNode, TaskMemoryManager


@pytest.mark.asyncio
async def test_graceful_task_failure_recovery():
    """Verify BossAgent handles agent failures gracefully without crashing the pipeline."""
    boss = BossAgent()

    # Simulate task with a missing/unregistered agent
    graph = TaskGraph(task_id="t_failover", user_request="Execute test query", complexity="simple")
    graph.nodes["nonexistent-agent"] = TaskNode(
        id="nonexistent-agent",
        title="Unknown Task",
        agent_id="nonexistent-agent-id",
        objective="Run unregistred agent",
        status="pending",
    )

    memory = TaskMemoryManager("t_failover", "Execute test query")
    events = []

    async def emit(event_name, data):
        events.append(event_name)

    await boss._execute_graph_layers(graph, memory, emit)

    node = graph.nodes["nonexistent-agent"]
    assert node.status == "failed"
    assert "not registered" in node.error
    assert "agent_failed" in events
