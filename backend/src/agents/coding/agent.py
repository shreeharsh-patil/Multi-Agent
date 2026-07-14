from src.agents.base import BaseAgent, AgentManifest, AgentResult


class CodingAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="coding",
            name="Coding Agent",
            description="Code writing, explanation, debugging, and documentation",
            icon="FileCode",
            capabilities=["code_generation", "code_explanation", "debugging", "documentation"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Coding Agent. Write clean, well-documented code. "
                "Support multiple programming languages. Explain code logic, help debug issues, "
                "and generate documentation. Always follow best practices.\n\n"
                "When generating HTML/CSS/JS code, always use markdown code blocks "
                "with the language specified (e.g. ```html, ```css, ```js). "
                "The platform automatically detects these blocks and renders a live preview."
            ),
        )
        return AgentResult(success=True, output=response)
