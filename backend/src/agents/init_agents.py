from src.agents.registry import AgentRegistry
from src.utils.logger import logger


def initialize_agents() -> None:
    AgentRegistry.initialize()
    logger.info(f"Initialized {len(AgentRegistry.get_all_agents())} specialized agents in registry.")
