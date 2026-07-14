from src.agents.base import BaseAgent, AgentManifest, AgentResult


class MemoryAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="memory",
            name="Memory Agent",
            description="Long-term memory, conversation history, user preferences, semantic memory",
            icon="Brain",
            capabilities=["long_term_memory", "conversation_history", "user_preferences", "semantic_memory"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.memory.service import memory_service

        user_id = context.get("user_id", "")

        memories = await memory_service.search(user_id, user_input, top_k=5)
        memory_context = ""
        if memories:
            memory_context = "Relevant memories:\n" + "\n".join(
                f"- {m.get('metadata', {}).get('key', 'unknown')}: {m.get('content', '')}" for m in memories
            )

        response = await llm_service.generate(
            prompt=f"{memory_context}\n\nUser: {user_input}" if memory_context else user_input,
            system_instruction=(
                "You are a Memory Agent. Help users remember past conversations, preferences, "
                "and important information. Store and retrieve memories. "
                "Be helpful and proactive in recalling relevant information."
            ),
        )

        if "remember" in user_input.lower():
            await memory_service.store(
                user_id=user_id,
                key="user_memory",
                content=user_input,
                type="fact",
            )

        return AgentResult(success=True, output=response)
