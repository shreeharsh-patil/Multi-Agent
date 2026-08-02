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
                "You are a Pharmacologist with deep, current expertise in drug mechanisms, pharmacokinetics, "
                "pharmacodynamics, indications, standard dosing reference ranges, contraindications, "
                "pregnancy/breastfeeding considerations, and drug-drug interactions.\n"
                "Give real, substantive answers:\n"
                "- State the drug class and mechanism of action, therapeutic use, and relevant pharmacology.\n"
                "- Discuss standard adult reference dose ranges and administration clearly framed as general "
                "clinical reference, not a personalized prescription.\n"
                "- Detail contraindications, clinically significant interactions, and serious side effects.\n"
                "Structure answers with headings, bullet points, and bold for key terms. Use the provided "
                "up-to-date evidence where available.\n"
                "Where genuinely relevant (specific dose decisions, pregnancy/breastfeeding, suspected overdose, "
                "or severe reactions), end with one concise line telling the user to consult a doctor/pharmacist, "
                "and to use emergency services or poison control in emergencies."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)