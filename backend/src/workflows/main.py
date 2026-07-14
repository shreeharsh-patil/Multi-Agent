from src.orchestrator.base import get_orchestrator


class WorkflowEngine:
    def __init__(self):
        self.orchestrator = get_orchestrator()

    async def run_sequential(
        self,
        user_input: str,
        user_id: str,
        agent_sequence: list[str],
    ) -> list[dict]:
        results = []
        for agent_id in agent_sequence:
            result = await self.orchestrator.process(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id,
            )
            results.append(result)
        return results

    async def run_parallel(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
    ) -> list[dict]:
        import asyncio

        tasks = [
            self.orchestrator.process(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id,
            )
            for agent_id in agent_ids
        ]
        results = await asyncio.gather(*tasks)
        return results

    async def run_conditional(
        self,
        user_input: str,
        user_id: str,
        condition_agent: str,
        true_agent: str,
        false_agent: str,
    ) -> list[dict]:
        result = await self.orchestrator.process(
            user_input=user_input,
            user_id=user_id,
            agent_id=condition_agent,
        )

        next_agent = true_agent if result["success"] else false_agent
        final = await self.orchestrator.process(
            user_input=user_input,
            user_id=user_id,
            agent_id=next_agent,
        )

        return [result, final]


workflow_engine = WorkflowEngine()
