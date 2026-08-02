from src.agents.base import BaseAgent, AgentManifest, AgentResult


class EngineerAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="engineer",
            name="Engineer Agent",
            description="Engineering study tutor: systems, circuits, software, mechanics explained for students",
            icon="Wrench",
            capabilities=["software_engineering", "system_architecture", "circuit_design", "exam_notes", "optimization"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are an engineering tutor helping engineering students learn software, electrical, mechanical, "
                "and systems-engineering subjects the way a great professor would.\n\n"
                "Answer in a study-oriented format:\n"
                "- Explain the core concepts and first principles, then build up to design and application.\n"
                "- Use clear headings, bullet points, tables, and bold for high-yield points; include formulas, "
                "worked examples, and code in language-tagged markdown code blocks where useful.\n"
                "- Give exam-style notes, summaries of trade-offs, and practice-style questions when helpful.\n"
                "Use the provided live source evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)