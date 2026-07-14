from fastapi import APIRouter

router = APIRouter(prefix="/api/agents", tags=["Agents"])

AGENT_METADATA = [
    {"id": "knowledge", "name": "Knowledge Agent", "description": "RAG-based document search, summaries, and citations using the knowledge base.", "icon": "BookOpen", "capabilities": ["rag", "document_search", "citations", "summaries"]},
    {"id": "drive", "name": "Drive Agent", "description": "Google Drive file management, uploads, downloads, and folder organization.", "icon": "Brain", "capabilities": ["drive_list", "drive_upload", "drive_download", "folder_management"]},
    {"id": "notes", "name": "Notes Agent", "description": "Structured notes, summaries, flashcards, and revision materials.", "icon": "StickyNote", "capabilities": ["note_taking", "summaries", "flashcards", "revision_notes"]},
    {"id": "quiz", "name": "Quiz Agent", "description": "MCQs, exams, and practice questions with answer keys and explanations.", "icon": "GraduationCap", "capabilities": ["mcq", "exam_generation", "practice_questions"]},
    {"id": "planner", "name": "Planner Agent", "description": "Study planning, task management, scheduling, and deadline tracking.", "icon": "Calendar", "capabilities": ["study_planning", "task_management", "scheduling"]},
    {"id": "research", "name": "Research Agent", "description": "Internet research, source comparison, and comprehensive report generation.", "icon": "Search", "capabilities": ["web_search", "source_comparison", "report_generation"]},
    {"id": "coding", "name": "Coding Agent", "description": "Code writing, explanation, debugging, and documentation generation.", "icon": "FileCode", "capabilities": ["code_generation", "code_explanation", "debugging"]},
    {"id": "memory", "name": "Memory Agent", "description": "Long-term memory, conversation history, user preferences, and recall.", "icon": "Brain", "capabilities": ["long_term_memory", "conversation_history", "user_preferences"]},
    {"id": "tool", "name": "Tool Agent", "description": "Calculator, web search, and external API tool execution.", "icon": "Puzzle", "capabilities": ["calculator", "web_search", "api_integration"]},
]


@router.get("")
async def list_agents() -> list[dict]:
    return [
        {**agent, "version": "0.1.0", "enabled": True}
        for agent in AGENT_METADATA
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    for agent in AGENT_METADATA:
        if agent["id"] == agent_id:
            return {**agent, "version": "0.1.0", "enabled": True}
    return {"error": f"Agent '{agent_id}' not found"}
