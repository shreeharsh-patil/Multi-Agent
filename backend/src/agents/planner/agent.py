from src.agents.base import BaseAgent, AgentManifest, AgentResult


class PlannerAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="planner",
            name="Planner Agent",
            description="Study planning, task management, schedules, and deadlines",
            icon="Calendar",
            capabilities=["study_planning", "task_management", "scheduling", "deadline_tracking"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Planner Agent. Help users plan their study schedules, manage tasks, "
                "set deadlines, and organize their time effectively. "
                "Create structured plans with timelines, priorities, and milestones."
            ),
        )
        return AgentResult(success=True, output=response)
