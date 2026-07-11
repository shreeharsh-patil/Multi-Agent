from src.agents.base import BaseAgent, AgentManifest, AgentResult


class QuizAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="quiz",
            name="Quiz Agent",
            description="MCQs, exams, and practice questions generation",
            icon="GraduationCap",
            capabilities=["mcq", "exam_generation", "practice_questions", "quiz_grading"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction=(
                "You are a Quiz Agent. Generate high-quality quiz questions including MCQs, "
                "true/false, fill-in-the-blanks, and short answer questions. "
                "Include answer keys and explanations. Adapt difficulty to the user's level."
            ),
        )
        return AgentResult(success=True, output=response)
