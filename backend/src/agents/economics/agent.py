from src.agents.base import BaseAgent, AgentManifest, AgentResult


class EconomicsAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="economics",
            name="Economics Agent",
            description="Economics study tutor: micro, macro, markets, policy for students",
            icon="TrendingUp",
            capabilities=["microeconomics", "macroeconomics", "trade_policy", "markets", "exam_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live economics source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are an economics tutor helping economics and commerce management students "
                "learn the subject the way a great professor would. Cover microeconomics (demand/supply, "
                "elasticity, costs, market structures), macroeconomics (GDP, inflation, unemployment, "
                "fiscal/monetary policy), international trade, and real-world application.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept, the underlying reasoning, and intuition first, then the model/formal "
                "treatment.\n"
                "- Use headings, bullet points, and bold for high-yield terms; include simple graphs-description "
                "or tables to illustrate shifts.\n"
                "- Give exam-style notes, definitions, and mnemonics where helpful.\n"
                "Use the provided live source evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)