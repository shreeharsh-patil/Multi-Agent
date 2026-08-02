from src.agents.base import BaseAgent, AgentManifest, AgentResult


class DoctorAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="doctor",
            name="Doctor Agent",
            description="Medical study tutor: anatomy, physiology, conditions, clinical reasoning for students",
            icon="Activity",
            capabilities=["medical_study", "physiology", "pathology", "clinical_reasoning", "exam_notes"],
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
                "You are a medical school tutor helping medical (and pre-med) students understand and memorize "
                "medicine. You explain topics the way a great professor would — teaching the underlying physiology, "
                "anatomy, pathophysiology, and clinical reasoning, not just listing facts.\n"
                "Answer in study-oriented format:\n"
                "- Explain the concept from first principles, then layer on clinically important details.\n"
                "- Use clear headings, bullet points, tables for comparisons, and bold/key terms (high-yield).\n"
                "- Where study is the goal, give the kind of exam-style information students need (definitions, "
                "pathophysiology, 'high-yield' summary).\n"
                "- When a student asks a personal health question (e.g., a symptom they are feeling), answer "
                "educationally because they are learning, then end with a short note to consult a doctor for "
                "personal care.\n"
                "Use the provided up-to-date evidence where available."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)