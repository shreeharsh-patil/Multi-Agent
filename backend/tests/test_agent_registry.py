import pytest
from src.agents.registry import AgentRegistry
from src.agents.base import BaseAgent, AgentManifest, AgentResult


class SampleTestAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="sample_test_agent",
            name="Sample Test Agent",
            description="A sample test agent for registry testing",
            icon="bot",
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        return AgentResult(success=True, output=f"Echo: {user_input}")


def test_agent_registry_register_and_get():
    """Test registering and retrieving agents from AgentRegistry."""
    test_agent = SampleTestAgent()
    AgentRegistry.register(test_agent)
    
    retrieved = AgentRegistry.get_agent("sample_test_agent")
    assert retrieved is not None
    assert retrieved.manifest.id == "sample_test_agent"
    assert retrieved.manifest.name == "Sample Test Agent"


def test_agent_registry_list_all():
    """Test listing all registered agents and manifests."""
    test_agent = SampleTestAgent()
    AgentRegistry.register(test_agent)
    
    all_agents = AgentRegistry.get_all_agents()
    manifests = AgentRegistry.get_all_manifests()
    
    assert any(a.manifest.id == "sample_test_agent" for a in all_agents)
    assert any(m.id == "sample_test_agent" for m in manifests)
