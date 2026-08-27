from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.utils.logger import logger


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
        user_id = context.get("user_id", "")

        # Isolate the actual current user prompt from conversation history prefix
        actual_prompt = user_input
        if "=== PREVIOUS CONVERSATION HISTORY ===" in user_input:
            parts = user_input.split("====================================")
            if len(parts) > 1:
                actual_prompt = parts[-1].strip()

        lower_q = actual_prompt.lower()

        # Cross-domain delegation for specific integration queries based strictly on current prompt
        if any(w in lower_q for w in ["calendar", "calender", "meeting", "appointment", "schedule", "event"]):
            try:
                from src.agents.calendar.agent import CalendarAgent
                return await CalendarAgent().execute(actual_prompt, context)
            except Exception:
                pass
        elif any(w in lower_q for w in ["google drive", "gdrive", "drive file", "drive folder"]):
            try:
                from src.agents.drive.agent import DriveAgent
                return await DriveAgent().execute(actual_prompt, context)
            except Exception:
                pass
        elif any(w in lower_q for w in ["contact", "contacts", "email of", "phone number"]):
            try:
                from src.agents.contacts.agent import ContactsAgent
                return await ContactsAgent().execute(actual_prompt, context)
            except Exception:
                pass
        elif any(w in lower_q for w in ["web search", "search web", "search online", "internet search", "google search", "search the web"]):
            try:
                from src.agents.research.agent import ResearchAgent
                return await ResearchAgent().execute(actual_prompt, context)
            except Exception:
                pass


        # Do not initialize the embedding/vector stack for ordinary chat. It
        # adds substantial latency and makes a greeting depend on a separate
        # embedding credential. Retrieval is only relevant when the request
        # has an explicit document/workspace scope.
        has_document_scope = bool(
            context.get("workspace_id")
            or context.get("has_attachments")
            or context.get("document_ids")
        )
        docs = []
        if has_document_scope:
            try:
                from src.services.rag.retriever import get_retriever

                docs = await get_retriever().retrieve(
                    user_input,
                    user_id=user_id,
                    workspace_id=context.get("workspace_id"),
                    top_k=5,
                )
            except Exception as exc:
                # Attachment text is already injected by the chat endpoint.
                # A vector-store outage must not take down the whole chat.
                logger.warning(
                    "knowledge_retrieval_failed",
                    extra={"user_id_present": bool(user_id), "error": str(exc)[:500]},
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
