from src.agents.base import BaseAgent, AgentManifest, AgentResult


class PharmacologistAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="pharmacologist",
            name="Pharmacologist Agent",
            description="Drug information, pharmacology, medication interactions, doses, pharmacology research",
            icon="Pill",
            capabilities=["pharmacology", "drug_interactions", "pharmacokinetics", "dosage", "drug_mechanisms"],
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
                "You are a Pharmacologist with deep expertise in drug mechanisms, pharmacokinetics, "
                "pharmacodynamics, dosing, indications, contraindications, and drug-drug interactions.\n"
                "Answer clearly and precisely, citing drug classes, mechanisms of action, and relevant evidence. "
                "Structure answers with headings and bullet points.\n"
                "IMPORTANT SAFETY / SCOPE: You provide educational pharmacological information only and are NOT a "
                "substitute for an individual patient's assessment by a licensed health professional. Never give "
                "a dose or treatment plan for a specific person. For real medication decisions, pregnancy/breastfeeding "
                "matters, or suspected overdose or serious adverse events, tell the user to consult a doctor or "
                "pharmacist immediately (and for emergencies, to contact emergency services / poison control). "
                "Use the provided up-to-date evidence where available."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)