from src.agents.base import BaseAgent, AgentManifest, AgentResult


class NotesAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="notes",
            name="Notes Agent",
            description="Structured notes, summaries, flashcards, and revision notes",
            icon="StickyNote",
            capabilities=["note_taking", "summaries", "flashcards", "revision_notes"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Notes Agent. Create structured, well-organized notes. "
                "Support formats: summaries, bullet points, flashcards (Q&A), revision guides. "
                "Use clear headings and organize information logically."
            ),
        )
        return AgentResult(success=True, output=response)
