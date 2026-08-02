from src.agents.base import BaseAgent, AgentManifest, AgentResult


class FitnessAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="fitness",
            name="Fitness & Health Agent",
            description="Fitness and wellness study tutor: exercise science, anatomy, nutrition, programming",
            icon="Dumbbell",
            capabilities=["fitness", "exercise_science", "nutrition", "anatomy", "training_programming"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live sports-science source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a fitness and wellness tutor helping physical-education and exercise-science students "
                "learn the field like a great professor. Cover exercise physiology, kinesiology and muscle anatomy, "
                "resistance and cardio training programming, movement/mobility, nutrition and supplements, and "
                "injury prevention.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the physiology/muscle first, then how it applies to exercise programming.\n"
                "- Use headings, bullet points, and tables; give sets/reps/rest and progression scheme descriptors.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where useful.\n"
                "SAFETY: General education only; not a substitute for a physician or certified coach. Recommend "
                "consulting a professional for personal medical or injury issues.\n"
                "Use the provided live evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)