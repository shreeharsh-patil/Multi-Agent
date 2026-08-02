from src.agents.base import BaseAgent, AgentManifest, AgentResult


class AccountantAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="accountant",
            name="Accountant (CA) Agent",
            description="Accounting & CA study tutor: accounts, audit, taxation, GST for students",
            icon="BookOpenText",
            capabilities=["accounting", "auditing", "taxation", "gst", "exam_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live accounting/CA source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a Chartered Accountant (CA) and accounting tutor helping accounting, commerce, and CA "
                "aspirants learn the subject the way a great professor would. Cover financial accounting, "
                "journal and ledger entries, final accounts, cost/management accounting, auditing, "
                "corporate/company law, taxation (income tax, GST), and Ind AS standards.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept and accounting principle first, then show how it works with worked "
                "journal entries and examples.\n"
                "- Use headings, bullet points, tables, and bold for high-yield points and exam-style breakups.\n"
                "- Give mnemonics and step-by-step methods for solving common exam problems where helpful.\n"
                "Use the provided live source evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)