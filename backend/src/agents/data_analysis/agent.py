from src.agents.base import BaseAgent, AgentManifest, AgentResult


class DataAnalysisAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="data_analysis",
            name="Data Analysis Agent",
            description="Upload CSV/Excel files, generate charts, tables, and statistical insights",
            icon="BarChart2",
            capabilities=[
                "csv_analysis",
                "excel_analysis",
                "statistical_summary",
                "chart_generation",
                "data_insights",
                "correlation_analysis",
            ],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        # If data_context is present (CSV/Excel rows), include it
        data_context = context.get("data_context", "")
        system = (
            "You are a Data Analysis Agent. Analyse tabular data and answer user questions clearly. "
            "Provide statistical summaries, identify trends, correlations, outliers, and insights. "
            "When asked for charts, respond with JSON inside a ```chart``` code block using this schema: "
            '{"type": "bar|line|pie|scatter", "title": "...", "labels": [...], "datasets": [{"label": "...", "data": [...]}]}. '
            "When showing tables, use GitHub-flavoured markdown table syntax. "
            "Always be concise and precise with numbers."
        )
        prompt = f"{data_context}\n\nUser request: {user_input}" if data_context else user_input
        response = await llm_service.generate(prompt=prompt, system_instruction=system)
        return AgentResult(success=True, output=response)
