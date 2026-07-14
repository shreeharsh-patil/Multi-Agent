from src.agents.base import BaseAgent, AgentManifest, AgentResult


class KnowledgeAgent(BaseAgent):
    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id="knowledge",
            name="Knowledge Agent",
            description="RAG, document search, citations, knowledge graph, and summaries",
            icon="BookOpen",
            capabilities=["rag", "document_search", "citations", "summaries", "knowledge_graph"],
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.services.rag.retriever import get_retriever

        retriever = get_retriever()
        user_id = context.get("user_id", "")

        docs = await retriever.retrieve(
            user_input,
            user_id=user_id,
            workspace_id=context.get("workspace_id"),
            top_k=5,
        )

        if docs:
            response, citations = await llm_service.generate_with_citations(
                prompt=user_input,
                context=docs,
                system_instruction=(
                    "You are a Knowledge Agent. Answer questions using the provided document context. "
                    "Always cite sources with file name and page number. "
                    "If the context doesn't contain the answer, say so."
                ),
            )
            return AgentResult(
                success=True,
                output=response,
                citations=citations,
            )

        response = await llm_service.generate(
            prompt=user_input,
            system_instruction="You are a Knowledge Agent. Answer as best you can. If you're unsure, say so.",
        )
        return AgentResult(success=True, output=response)
