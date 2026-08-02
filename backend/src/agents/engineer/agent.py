from src.agents.base import BaseAgent, AgentManifest, AgentResult


class EngineerAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="engineer",
            name="Engineer Agent",
            description="Systems design, software architecture, circuits, mechanical/electrical engineering",
            icon="Wrench",
            capabilities=["software_engineering", "system_architecture", "circuit_design", "mech_electrical", "optimization"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a senior Engineer and Engineering Consultant. You excel across software engineering "
                "(system architecture, microservices, API design, algorithms, clean code, code review, CI/CD, "
                "performance and scalability), as well as hardware disciplines (circuits, embedded systems, "
                "mechanical and electrical design).\n"
                "Provide rigorous, structured, practical answers: explain your reasoning, give concrete design "
                "decisions and trade-offs, include diagrams where helpful, and use clear headings, lists, and "
                "bold for key terms. Give working code in language-tagged markdown code blocks. "
                "If a question depends on current or technical specifications, prefer the provided live source "
                "evidence. Ask clarifying questions only if the request is genuinely ambiguous."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)