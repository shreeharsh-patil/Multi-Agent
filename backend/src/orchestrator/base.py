import time
from typing import Optional
from src.utils.logger import logger
from src.utils.exceptions import AgentException
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

        # Route via ADK multi-agent system
        from src.adk.runner import process_message

        conv_id = conversation_id or f"orch_{user_id}_{int(time.time())}"

        try:
            result = await process_message(
                message=user_input,
                user_id=user_id,
                conversation_id=conv_id,
            )

            elapsed = time.time() - start_time
            logger.info("Request processed via ADK", extra={
                "agent_id": target_agent_id,
                "latency_ms": round(elapsed * 1000, 2),
                "success": result.get("success", True),
            })

            return {
                "agent_id": target_agent_id,
                "output": result.get("output", ""),
                "citations": result.get("citations", []),
                "tool_calls": [],
                "agent_traces": result.get("agent_traces", []),
                "latency_ms": round(elapsed * 1000, 2),
                "success": result.get("success", True),
                "error": result.get("error"),
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"ADK processing failed", extra={"error": str(e)})

            # Fallback: use custom agent if ADK fails
            agent = self.registry.get_agent(target_agent_id)
            if agent:
                context = {"user_id": user_id, "conversation_id": conversation_id}
                result = await agent.execute(user_input, context)
                return {
                    "agent_id": target_agent_id,
                    "output": result.output,
                    "citations": result.citations,
                    "tool_calls": result.tool_calls,
                    "latency_ms": round(elapsed * 1000, 2),
                    "success": result.success,
                    "error": result.error,
                }

            raise AgentException(f"Agent execution failed: {e}") from e

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
