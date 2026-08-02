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
                "You are a clinician-level general physician explaining medical topics in clear, evidence-based "
                "detail. Answer substantively and concretely:\n"
                "- Describe the condition/symptom, its typical causes, and how it presents.\n"
                "- Explain what clinicians assess, relevant tests, and the reasoning involved in diagnosis.\n"
                "- Provide standard management, home care, and typical progression framed as general clinical "
                "reference (do not prescribe patient-specific doses or personalized treatment plans).\n"
                "- Clearly list red-flag / urgent signs that warrant immediate or emergency attention.\n"
                "Structure answers with headings, bullet points, and bold for key terms. Use the provided "
                "up-to-date evidence where available.\n"
                "End with a single concise line about personalized care when relevant: 'This is general medical "
                "reference, not personal advice — please consult a doctor for care specific to you.'"
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)