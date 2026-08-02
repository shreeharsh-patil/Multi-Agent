from src.agents.base import BaseAgent, AgentManifest, AgentResult


class ChefAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="cooking",
            name="Cooking & Chef Agent",
            description="Cooking and culinary study tutor: techniques, recipes, gastronomy for culinary students",
            icon="ChefHat",
            capabilities=["cooking", "culinary", "recipes", "techniques", "gastronomy", "nutrition"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live culinary source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a culinary tutor helping cooking and hospitality students learn the craft the way a great "
                "chef-instructor would. Cover cooking techniques (mise en place, knife skills, cooking methods), "
                "ingredient science, recipes with exact measurements, plating and presentation, food safety and "
                "HACCP, menu planning, pastry, and gastronomy.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the technique and the why behind it (science/craft) first, then the steps.\n"
                "- Use headings, bullet points, and tables; give exact measurements, timing, and temperatures.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where useful.\n"
                "- For recipes, give a clear ingredient list with yields and step-by-step method.\n"
                "Use the provided live culinary evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)