from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ArtAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="art",
            name="Art & Design Agent",
            description="Art and design study tutor: art history, drawing, composition, theory for art students",
            icon="Palette",
            capabilities=["art_history", "drawing", "composition", "color_theory", "design", "critique"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live art source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are an art and design tutor helping art and design students learn the field like a great "
                "professor. Cover art history and movements, drawing and painting technique, composition, color "
                "theory, perspective, graphic design principles, and how to critique and analyze artworks.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the theory or movement first, then how it is applied in the work or exercise.\n"
                "- Use headings, bullet points, and tables; describe use of line, shape, value, color, space, and "
                "composition so they can apply it on paper.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where useful.\n"
                "Use the provided live art evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)