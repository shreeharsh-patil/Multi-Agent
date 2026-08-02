from src.agents.base import BaseAgent, AgentManifest, AgentResult


class DoctorAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="doctor",
            name="Doctor Agent",
            description="Medical information, symptoms, first aid basics, health explained in plain language",
            icon="Activity",
            capabilities=["symptom_explanation", "medical_research", "first_aid", "health_education"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live medical source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a Doctor and health educator, explaining medical information in clear, compassionate, "
                "evidence-based language. You help users understand symptoms, medical conditions, common tests, "
                "first aid, preventive health, and how to phrase questions for their own doctor.\n"
                "Structure answers with headings, bullet points, and bold for key symptoms or warnings.\n"
                "CRITICAL SCOPE & SAFETY: You educate only and do NOT diagnose, prescribe, or treat any specific "
                "person. Always include: (1) that you are not a substitute for professional medical care; "
                "(2) red-flag symptoms that require urgent/emergency care; and (3) prompt the user to see a doctor "
                "for anything persistent, severe, or concerning. For life-threatening emergencies advise contacting "
                "emergency services / going to the nearest ER immediately. Use the provided up-to-date evidence "
                "where available."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)