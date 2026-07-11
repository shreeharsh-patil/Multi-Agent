import time
from typing import Optional
from src.utils.logger import logger
from src.utils.exceptions import AgentException
from src.agents.base import BaseAgent, AgentResult
from src.agents.registry import AgentRegistry
from src.orchestrator.router import AgentRouter


class AgentOrchestrator:
    def __init__(self):
        self.router = AgentRouter()
        self.registry = AgentRegistry()

    async def process(
        self,
        user_input: str,
        user_id: str,
        agent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> dict:
        start_time = time.time()
        logger.info("Processing request", extra={
            "user_id": user_id,
            "agent_id": agent_id,
            "input_length": len(user_input),
        })

        target_agent_id = agent_id or self.router.route(user_input)

        if not target_agent_id:
            target_agent_id = "knowledge"

        agent = self.registry.get_agent(target_agent_id)
        if not agent:
            raise AgentException(f"Agent '{target_agent_id}' not found")

        context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
        }

        result = await agent.execute(user_input, context)

        elapsed = time.time() - start_time
        logger.info("Request processed", extra={
            "agent_id": target_agent_id,
            "latency_ms": round(elapsed * 1000, 2),
            "success": result.success,
        })

        return {
            "agent_id": target_agent_id,
            "output": result.output,
            "citations": result.citations,
            "tool_calls": result.tool_calls,
            "latency_ms": round(elapsed * 1000, 2),
            "success": result.success,
            "error": result.error,
        }

    async def process_multi_agent(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
        conversation_id: Optional[str] = None,
    ) -> list[dict]:
        results = []
        for agent_id in agent_ids:
            result = await self.process(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
            )
            results.append(result)
        return results


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
