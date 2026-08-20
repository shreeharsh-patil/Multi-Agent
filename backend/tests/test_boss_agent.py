import pytest
import asyncio
from src.agents.registry import AgentRegistry
from src.agents.metadata import AgentDepartment, AgentMetadata, TaskMode, ConfidenceLevel
from src.orchestrator.boss import get_boss_agent, BossAgent, TaskMemoryManager, TaskGraph, TaskNode
from src.tools.registry import ToolRegistry


def test_registry_100_agents_loaded():
    """Verify that all 100 specialized agents across 10 departments are registered with deep domain prompts."""
    all_agents = AgentRegistry.get_all_agents()
    all_metadata = AgentRegistry.get_all_metadata()

    assert len(all_agents) >= 100, f"Expected 100+ agents, got {len(all_agents)}"
    assert len(all_metadata) >= 100, f"Expected 100+ metadata records, got {len(all_metadata)}"

    # Check that all 10 departments have agents registered
    departments = {m.department for m in all_metadata}
    assert len(departments) == 10, f"Expected 10 departments, got {len(departments)}"

    from src.agents.catalog import AGENT_CATALOG_DATA
    for meta in AGENT_CATALOG_DATA:
        assert len(meta.specialized_instruction) > 20, f"Agent {meta.id} missing specialized prompt"
        assert len(meta.domain_quality_criteria) > 0, f"Agent {meta.id} missing domain quality criteria"


def test_extensibility_101st_agent():
    """Verify that adding a 101st agent requires only registration and doesn't break BossAgent."""
    from src.agents.base import BaseAgent, AgentManifest, AgentResult

    class Custom101Agent(BaseAgent):
        def _create_manifest(self):
            return AgentManifest(
                id="agent-101-specialist",
                name="101st Specialist Agent",
                description="Custom extension agent 101",
                icon="Bot",
            )

        async def execute(self, user_input, context):
            return AgentResult(success=True, output="Custom 101 output")

    custom_agent = Custom101Agent()
    meta = AgentMetadata(
        id="agent-101-specialist",
        name="101st Specialist Agent",
        department=AgentDepartment.AUTOMATION,
        description="Custom extension agent 101",
        capabilities=["custom-101-cap"],
        specialized_instruction="You are custom 101 agent",
        domain_quality_criteria=["Test Criteria"],
    )
    AgentRegistry.register(custom_agent, meta)

    retrieved = AgentRegistry.get_agent("agent-101-specialist")
    assert retrieved is not None
    assert retrieved.manifest.id == "agent-101-specialist"

    by_cap = AgentRegistry.get_by_capability("custom-101-cap")
    assert len(by_cap) == 1


@pytest.mark.asyncio
async def test_boss_intent_analysis_and_modes():
    """Verify BossAgent classifies intent into TaskModes (QUICK, STANDARD, DEEP, CRITICAL)."""
    boss = BossAgent()

    quick_intent = await boss._analyze_intent("What is HTML?")
    assert quick_intent["mode"] == TaskMode.QUICK

    deep_intent = await boss._analyze_intent("Build an AI note taking application with vector embeddings and database backend")
    assert deep_intent["mode"] in [TaskMode.DEEP, TaskMode.CRITICAL]

    critical_intent = await boss._analyze_intent("Perform security review and OWASP vulnerability audit on auth system")
    assert critical_intent["mode"] == TaskMode.CRITICAL


@pytest.mark.asyncio
async def test_shopping_task_routing():
    """Verify BossAgent recognizes shopping requests, extracts budget/category, and routes to product-researcher team."""
    boss = BossAgent()

    # Query 1: Find a mouse under ₹500
    intent1 = await boss._analyze_intent("Find a mouse under ₹500")
    assert intent1["is_shopping"] is True
    assert intent1["shopping_params"]["category"] == "mouse"
    assert intent1["shopping_params"]["budget"] == 500.0

    graph1 = await boss._build_execution_graph("t_shop1", "Find a mouse under ₹500", intent1)
    assert "product-researcher" in graph1.nodes
    assert "price-verification-agent" in graph1.nodes
    assert "product-comparison-agent" in graph1.nodes

    # Query 2: Best keyboard under ₹2000
    intent2 = await boss._analyze_intent("Best keyboard under ₹2000")
    assert intent2["is_shopping"] is True
    assert intent2["shopping_params"]["category"] == "keyboard"
    assert intent2["shopping_params"]["budget"] == 2000.0

    # Query 3: Best laptop under ₹60000
    intent3 = await boss._analyze_intent("Best laptop under ₹60000")
    assert intent3["is_shopping"] is True
    assert intent3["shopping_params"]["category"] == "laptop"
    assert intent3["shopping_params"]["budget"] == 60000.0


@pytest.mark.asyncio
async def test_live_data_task_routing():
    """Verify BossAgent recognizes time-sensitive queries, triggers is_live_data, and routes to live-search-specialist team."""
    boss = BossAgent()

    # Query 1: Latest AI models
    intent1 = await boss._analyze_intent("What are the latest AI models released today?")
    assert intent1["is_live_data"] is True
    graph1 = await boss._build_execution_graph("t_live1", "What are the latest AI models released today?", intent1)
    assert "live-search-specialist" in graph1.nodes
    assert "real-time-data-verifier" in graph1.nodes
    assert "fact-checker" in graph1.nodes

    # Query 2: Current browser versions
    intent2 = await boss._analyze_intent("Current Chrome and Firefox browser versions")
    assert intent2["is_live_data"] is True


@pytest.mark.asyncio
async def test_image_generation_task_routing():
    """Verify BossAgent recognizes image generation requests and routes to FLUX image pipeline."""
    boss = BossAgent()

    intent = await boss._analyze_intent("Generate a cyberpunk city wallpaper")
    assert intent["is_image_generation"] is True

    graph = await boss._build_execution_graph("t_img1", "Generate a cyberpunk city wallpaper", intent)
    assert "prompt-engineer" in graph.nodes
    assert "image-generation-agent" in graph.nodes
    assert "visual-critic" in graph.nodes


@pytest.mark.asyncio
async def test_boss_execution_loop():
    """Verify BossAgent executes graph, tracks task memory, and returns synthesized output."""
    boss = BossAgent()
    events = []

    def handle_event(event_type, payload):
        events.append(event_type)

    result = await boss.execute_task(
        user_request="What is Retrieval-Augmented Generation (RAG)?",
        user_id="test_user",
        on_event=handle_event,
    )

    assert result["status"] in ["completed", "partial_success"]
    assert len(result["output"]) > 0
    assert result["total_agents_activated"] > 0
    assert result["total_agents_activated"] < 20  # Never activates all 100 agents!
    assert "boss_received" in events
    assert "plan_created" in events
    assert "pre_execution_check_passed" in events
    assert "post_execution_check_passed" in events
    assert "synthesizing_final_answer" in events
    assert "boss_completed" in events


def test_tool_registry():
    """Verify ToolRegistry contains default tools and executes authorization checks."""
    tools = ToolRegistry.list_tools()
    assert len(tools) >= 10

    web_search = ToolRegistry.get_tool("web_search")
    assert web_search is not None
    assert web_search.name == "Web Search Engine"

    exec_res = ToolRegistry.execute_tool("web_search", query="TCP protocol")
    assert exec_res["success"] is True


def test_task_memory_propagates_user_and_request_context():
    memory = TaskMemoryManager(
        "task-1",
        "Summarize my private workspace",
        "user-123",
        {"workspace_id": "workspace-9", "conversation_history": "recent context"},
    )
    node = TaskNode(id="research", title="Research", agent_id="research", objective="Research the request")
    context = memory.get_context_for_node(node)

    assert context["user_id"] == "user-123"
    assert context["workspace_id"] == "workspace-9"
    assert context["conversation_history"] == "recent context"
