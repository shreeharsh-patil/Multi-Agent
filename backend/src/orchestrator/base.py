import time
from typing import Optional, Any, Callable
from src.utils.logger import logger
from src.utils.exceptions import AgentException
from src.agents.registry import AgentRegistry
from src.orchestrator.router import AgentRouter
from src.orchestrator.boss import BossAgent, get_boss_agent, TaskNode, TaskGraph, TaskMemoryManager


class BossAgentFacade(BossAgent):
    """Facade ensuring legacy method compatibility while BossAgent acts as the sole executive controller."""

    def __init__(self):
        super().__init__()
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
        logger.info("BossAgent processing request", extra={
            "user_id": user_id,
            "agent_id": agent_id,
            "input_length": len(user_input),
        })

        target_agent_id = agent_id or self.router.route(user_input)

        if not target_agent_id:
            target_agent_id = "knowledge"

        # Execute target agent via BossAgent context
        agent = self.registry.get_agent(target_agent_id)
        if agent:
            context = {"user_id": user_id, "conversation_id": conversation_id}
            result = await agent.execute(user_input, context)
            elapsed = time.time() - start_time
            return {
                "agent_id": target_agent_id,
                "output": result.output,
                "citations": result.citations,
                "tool_calls": result.tool_calls,
                "latency_ms": round(elapsed * 1000, 2),
                "success": result.success,
                "error": result.error,
            }

        raise AgentException(f"Agent execution failed: target agent {target_agent_id} not found")

    async def process_multi_agent(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
        conversation_id: Optional[str] = None,
    ) -> list[dict]:
        import asyncio
        tasks = [
            self.process(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
            )
            for agent_id in agent_ids
        ]
        return list(await asyncio.gather(*tasks))

    async def process_team(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> dict:
        """Runs a specialist handoff pipeline controlled by BossAgent."""
        valid_agents = [agent_id for agent_id in agent_ids if self.registry.get_agent(agent_id)]
        if not valid_agents:
            raise AgentException("Teamwork mode requires at least one valid agent")

        handoff = user_input
        stages = []
        for index, agent_id in enumerate(valid_agents):
            agent = self.registry.get_agent(agent_id)
            if not agent:
                continue
            agent_context = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "team_index": index,
                **(context or {}),
            }
            result = await agent.execute(handoff, agent_context)
            stage = {
                "agent_id": agent_id,
                "output": result.output,
                "success": result.success,
                "error": result.error,
            }
            stages.append(stage)
            if not result.success:
                break
            handoff = (
                f"Original user request:\n{user_input}\n\n"
                f"Previous specialist handoff from {agent_id}:\n{result.output}\n\n"
                "Continue the request as the next specialist."
            )

        output = "\n\n".join(
            f"### {stage['agent_id'].title()} Agent\n{stage['output']}" for stage in stages
        )
        return {
            "output": output,
            "stages": stages,
            "agent_traces": [
                {"agent_id": stage["agent_id"], "event_type": "TeamStage", "has_content": bool(stage["output"])}
                for stage in stages
            ],
            "events_count": len(stages),
            "success": all(stage["success"] for stage in stages),
        }

    async def process_dynamic(
        self,
        user_input: str,
        user_id: str,
        plan: dict,
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None,
        on_event=None,
    ) -> dict:
        """Executes a dynamic task graph via the BossAgent lifecycle."""
        res = await self.execute_task(
            user_request=user_input,
            user_id=user_id,
            task_id=conversation_id,
            on_event=on_event,
        )
        return {
            "output": res["output"],
            "citations": [],
            "agent_traces": [
                {"agent_id": aid, "event_type": "BossAgentSpecialist", "has_content": True}
                for aid in res.get("active_agents", [])
            ],
            "events_count": len(res.get("active_agents", [])),
            "success": res["status"] in ["completed", "partial_success"],
            "state": "SUCCESS" if res["status"] == "completed" else "PARTIAL_SUCCESS",
            "latency_ms": res["latency_ms"],
            "plan": plan,
        }


# BossAgent is the single executive controller and orchestrator
def get_orchestrator() -> BossAgentFacade:
    """Alias for backwards compatibility pointing directly to BossAgent instance."""
    return get_boss_agent_instance()


_boss_facade_instance: Optional[BossAgentFacade] = None


def get_boss_agent_instance() -> BossAgentFacade:
    global _boss_facade_instance
    if _boss_facade_instance is None:
        _boss_facade_instance = BossAgentFacade()
    return _boss_facade_instance
