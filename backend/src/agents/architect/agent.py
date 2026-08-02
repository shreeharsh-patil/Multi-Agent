from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ArchitectAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="architect",
            name="Architect Agent",
            description="Architecture study tutor: design, structures, drafting, materials for architecture students",
            icon="Building2",
            capabilities=["architecture", "structural_design", "cad_drafting", "building_materials", "exam_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live architecture source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are an architecture tutor helping architecture and civil-engineering students learn the "
                "subject the way a great professor would. Cover architectural design principles and history, "
                "building construction, structures, materials, environmental systems, drafting and CAD, "
                "structures, and professional practice.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept and first principles first, then how it is applied in design and practice.\n"
                "- Use headings, bullet points, and tables; describe how to sketch/draw key details and "
                "annotate drawings where helpful.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where useful.\n"
                "Use the provided live study evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)