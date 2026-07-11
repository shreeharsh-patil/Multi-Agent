from typing import Optional
from src.agents.base import BaseAgent, AgentManifest
from src.utils.logger import logger


class AgentRegistry:
    _agents: dict[str, BaseAgent] = {}
    _initialized = False

    @classmethod
    def register(cls, agent: BaseAgent) -> None:
        agent_id = agent.manifest.id
        cls._agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id} ({agent.manifest.name})")

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        return cls._agents.get(agent_id)

    @classmethod
    def get_all_manifests(cls) -> list[AgentManifest]:
        return [a.manifest for a in cls._agents.values()]

    @classmethod
    def get_all_agents(cls) -> list[BaseAgent]:
        return list(cls._agents.values())

    @classmethod
    def initialize(cls) -> None:
        if cls._initialized:
            return
        cls._initialized = True
        logger.info("Agent registry initialized")
