from src.agents.base import BaseAgent, AgentManifest, AgentResult


class MusicAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="music",
            name="Music Agent",
            description="Music study tutor: theory, composition, instruments, analysis for music students",
            icon="Music",
            capabilities=["music_theory", "composition", "instruments", "analysis", "history"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.adk.tools import web_search

        evidence = ""
        try:
            search_results = await web_search(user_input, for_research=False)
            if search_results and len(search_results.strip()) > 30:
                evidence = f"\n\nRelevant live music source evidence (use where applicable):\n{search_results}"
        except Exception:
            pass

        response = await llm_service.generate(
            prompt=user_input + evidence,
            system_instruction=(
                "You are a music tutor helping music and performing-arts students learn the craft the way a great "
                "professor would. Cover music theory (notation, scales, keys, intervals, chords, harmony), ear "
                "training, composition, instrument technique, music history and genres, and listening analysis.\n"
                "Answer in a study-oriented format:\n"
                "- Explain the concept and first principles first, then apply it to examples and scores.\n"
                "- Use headings, bullet points, and tables; describe note/chord patterns clearly (e.g., "
                "note-names and intervals) so they can be followed without audio.\n"
                "- Bold high-yield points and add exam-style notes and mnemonics where useful.\n"
                "Use the provided live music evidence where relevant."
            ),
            temperature=0.3,
            max_output_tokens=2048,
        )
        return AgentResult(success=True, output=response)