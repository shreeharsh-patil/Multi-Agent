from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ResearchAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="research",
            name="Research Agent",
            description="Internet search, source comparison, report generation, citations",
            icon="Search",
            capabilities=["web_search", "source_comparison", "report_generation", "citations"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Research Agent. Conduct thorough research, compare multiple sources, "
                "and generate comprehensive reports with proper citations. "
                "Structure reports with: abstract, methodology, findings, analysis, conclusions, references."
            ),
        )
        return AgentResult(success=True, output=response)
