import re
from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.models.agent import AgentConfig


class CustomAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        self.config = config
        super().__init__()

    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id=self.config.agent_id,
            name=self.config.name,
            description=self.config.description,
            icon=self.config.icon,
            capabilities=self.config.tools,
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service

        tool_context = []
        if "calculator" in self.config.tools:
            expression = re.search(r"(?:calculate|compute|what is)\s+([0-9+*/().%\-\s]+)", user_input, re.I)
            if expression:
                from src.adk.tools import calculator
                tool_context.append(await calculator(expression.group(1).strip()))
        if "web_search" in self.config.tools and re.search(r"\b(search|research|latest|look up)\b", user_input, re.I):
            from src.adk.tools import web_search
            tool_context.append(await web_search(user_input))

        tools_hint = ", ".join(self.config.tools) if self.config.tools else "none"
        prompt = user_input
        if tool_context:
            prompt += "\n\nTool results (use these when relevant):\n" + "\n\n".join(tool_context)
        response = await llm_service.generate(
            prompt=prompt,
            system_instruction=(
                f"{self.config.system_instruction}\n\n"
                f"You are {self.config.name}. Available tools: {tools_hint}. "
                "Never claim to have used a tool that is not available."
            ),
        )
        return AgentResult(success=True, output=response, metadata={"tools": self.config.tools})
