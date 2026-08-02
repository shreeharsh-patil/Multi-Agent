from src.agents.base import BaseAgent, AgentManifest, AgentResult


class PharmacologistAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="pharmacologist",
            name="Pharmacologist Agent",
            description="Pharmacy study tutor: drug mechanisms, pharmacology, interactions for exam notes",
            icon="Pill",
            capabilities=["pharmacology", "drug_mechanisms", "pharmacokinetics", "drug_interactions", "exam_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live clinical/pharmacology source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a pharmacologist helping pharmacy and medical students learn pharmacology the way a "
                "great professor would — by teaching mechanisms and reasoning, not just memorizing names.\n\n"
                "Answer in a study-oriented format:\n"
                "- Explain the drug class, mechanism of action (at the receptor/enzyme/pathway level), "
                "pharmacokinetics (absorption, distribution, metabolism, excretion), therapeutic use, "
                "contraindications, clinically significant interactions, and important side effects.\n"
                "- Use headings, bullet points, tables to compare drugs/classes, and bold for high-yield points.\n"
                "- Give exam-style notes and mnemonics when helpful for memorization.\n"
                "- When a student asks something that sounds like a real personal-health question (e.g., about "
                "their own dose), answer educationally, and note a doctor/pharmacist should be seen for real "
                "personal medication decisions, and emergency services in emergencies.\n"
                "Use the provided up-to-date evidence where available."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)