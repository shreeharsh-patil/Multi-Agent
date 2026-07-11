from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ToolAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="tool",
            name="Tool Agent",
            description="Calculator, Calendar, Gmail, Drive, APIs, databases",
            icon="Puzzle",
            capabilities=["calculator", "calendar", "gmail", "api_integration", "database_queries"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Tool Agent. Execute tools and integrations on behalf of the user. "
                "Support: calculator (math operations), Google Calendar (events), "
                "API calls, database queries. Explain what tools are available."
            ),
        )
        return AgentResult(success=True, output=response)
