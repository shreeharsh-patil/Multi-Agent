from src.agents.base import BaseAgent, AgentManifest, AgentResult


class FinanceAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="finance",
            name="Finance Agent",
            description="Finance study tutor: financial statements, valuation, markets, investing for students",
            icon="Wallet",
            capabilities=["finance", "financial_analysis", "valuation", "investment", "exam_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live finance source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a finance tutor helping finance and management students learn the subject "
                "the way a great professor would. Cover financial statement analysis (balance sheet, P&L, cash "
                "flow), valuation (DCF, ratios, comps), corporate finance, capital markets, investing, and risk "
                "in clear, practical terms.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept and first principles first, then how it is applied in practice.\n"
                "- Use formulas, worked numerical examples, and headings, bullet points, and tables.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where helpful.\n"
                "Use the provided live source evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)