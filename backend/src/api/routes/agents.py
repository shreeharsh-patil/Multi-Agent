from datetime import datetime, timezone
import json
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from src.models.agent import AgentConfig
from src.agents.registry import AgentRegistry

router = APIRouter(prefix="/api/agents", tags=["Agents"])


class CustomAgentInput(BaseModel):
    name: str
    description: str = ""
    icon: str = "Bot"
    system_instruction: str
    tools: list[str] = []
    enabled: bool = True


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)


def resolved_user(request: Request) -> str:
    auth_user = getattr(request.state, "user", None)
    return (auth_user.get("sub") if auth_user else None) or "default"


def serialize_custom(agent: AgentConfig) -> dict:
    return {
        "id": agent.agent_id, "name": agent.name, "description": agent.description,
        "icon": agent.icon, "capabilities": agent.tools, "tools": agent.tools,
        "systemInstruction": agent.system_instruction, "enabled": agent.enabled,
        "version": agent.version, "custom": True,
    }

AGENT_METADATA = [
    {"id": "image", "name": "Image Generation Agent", "description": "Creates downloadable images and visual assets from natural-language prompts.", "icon": "Image", "capabilities": ["image_generation", "text_to_image", "visual_assets"]},
    {"id": "knowledge", "name": "Knowledge Agent", "description": "RAG-based document search, summaries, and citations using the knowledge base.", "icon": "BookOpen", "capabilities": ["rag", "document_search", "citations", "summaries"]},
    {"id": "drive", "name": "Drive Agent", "description": "Google Drive file management, document reading, summarization, uploads, and downloads.", "icon": "HardDrive", "capabilities": ["drive_list", "drive_read", "drive_summarize", "drive_upload", "drive_download", "folder_management"]},
    {"id": "notes", "name": "Notes Agent", "description": "Structured notes, summaries, flashcards, and revision materials.", "icon": "StickyNote", "capabilities": ["note_taking", "summaries", "flashcards", "revision_notes"]},
    {"id": "quiz", "name": "Quiz Agent", "description": "MCQs, exams, and practice questions with answer keys and explanations.", "icon": "GraduationCap", "capabilities": ["mcq", "exam_generation", "practice_questions"]},
    {"id": "planner", "name": "Planner Agent", "description": "Study planning, task management, scheduling, and deadline tracking.", "icon": "Calendar", "capabilities": ["study_planning", "task_management", "scheduling"]},
    {"id": "calendar", "name": "Calendar Agent", "description": "Lists event details, creates, reschedules, and checks Google Calendar availability.", "icon": "CalendarDays", "capabilities": ["list_events", "event_details", "create_events", "availability", "reschedule"]},
    {"id": "research", "name": "Research Agent", "description": "Internet research, source comparison, and comprehensive report generation.", "icon": "Search", "capabilities": ["web_search", "source_comparison", "report_generation"]},
    {"id": "deep_research", "name": "Deep Research Specialist", "description": "Performs multi-step web exploration, page scraping, cross-source synthesis, and generates exhaustive multi-page research reports.", "icon": "BookOpenCheck", "capabilities": ["multi_page_deep_research", "live_web_crawling", "academic_synthesis", "exhaustive_reporting"]},
    {"id": "coding", "name": "Coding Agent", "description": "Code writing, explanation, debugging, and documentation generation.", "icon": "FileCode", "capabilities": ["code_generation", "code_explanation", "debugging"]},
    {"id": "memory", "name": "Memory Agent", "description": "Long-term memory, conversation history, user preferences, and recall.", "icon": "Brain", "capabilities": ["long_term_memory", "conversation_history", "user_preferences"]},
    {"id": "tool", "name": "Tool Agent", "description": "Calculator, web search, and external API tool execution.", "icon": "Puzzle", "capabilities": ["calculator", "web_search", "api_integration"]},
    {"id": "data_analysis", "name": "Data Analysis Agent", "description": "Upload CSV/Excel files, generate charts, tables, and statistical insights from your data.", "icon": "BarChart2", "capabilities": ["csv_analysis", "excel_analysis", "statistical_summary", "chart_generation", "data_insights"]},
    {"id": "weather_news", "name": "Weather & News Agent", "description": "Real-time weather forecasts and live news headlines from global sources — no API key required.", "icon": "CloudSun", "capabilities": ["real_time_weather", "3_day_forecast", "live_news_headlines", "category_news", "ai_weather_insights"]},
    {"id": "contacts", "name": "Contacts Agent", "description": "Lists, searches, and fetches Google Contacts details including emails and phone numbers.", "icon": "Users", "capabilities": ["list_contacts", "search_contacts", "contact_details"]},
]


@router.get("")
async def list_agents(request: Request) -> list[dict]:
    all_metadata = AgentRegistry.get_all_metadata()
    built_ins = [
        {
            "id": m.id,
            "name": m.name,
            "department": m.department.value,
            "description": m.description,
            "icon": m.icon,
            "capabilities": m.capabilities,
            "responsibilities": m.responsibilities,
            "tools": m.required_tools + m.optional_tools,
            "version": "0.1.0",
            "enabled": m.enabled,
        }
        for m in all_metadata
    ]
    custom_agents = await AgentConfig.find(AgentConfig.user_id == resolved_user(request), AgentConfig.custom == True).sort(-AgentConfig.updated_at).to_list()
    return built_ins + [serialize_custom(agent) for agent in custom_agents]


@router.get("/adk-status")
async def get_adk_hierarchy_status() -> dict:
    """Return live dynamic status and hierarchy telemetry for Google ADK."""
    from src.adk.runner import get_adk_status
    return get_adk_status()


@router.post("")
async def create_custom_agent(request: Request, body: CustomAgentInput) -> dict:
    if not body.name.strip() or not body.system_instruction.strip():
        raise HTTPException(status_code=400, detail="Name and system instructions are required")
    agent = AgentConfig(
        user_id=resolved_user(request),
        agent_id=f"custom_{uuid.uuid4().hex[:12]}",
        name=body.name.strip(), description=body.description.strip(), icon=body.icon,
        system_instruction=body.system_instruction.strip(), tools=body.tools, enabled=body.enabled,
    )
    await agent.insert()
    return serialize_custom(agent)


@router.patch("/{agent_id}")
async def update_custom_agent(agent_id: str, request: Request, body: CustomAgentInput) -> dict:
    agent = await AgentConfig.find_one(AgentConfig.agent_id == agent_id, AgentConfig.user_id == resolved_user(request), AgentConfig.custom == True)
    if not agent:
        raise HTTPException(status_code=404, detail="Custom agent not found")
    agent.name = body.name.strip() or agent.name
    agent.description = body.description.strip()
    agent.icon = body.icon
    agent.system_instruction = body.system_instruction.strip() or agent.system_instruction
    agent.tools = body.tools
    agent.enabled = body.enabled
    agent.updated_at = datetime.now(timezone.utc)
    await agent.save()
    return serialize_custom(agent)


@router.delete("/{agent_id}")
async def delete_custom_agent(agent_id: str, request: Request) -> dict:
    agent = await AgentConfig.find_one(AgentConfig.agent_id == agent_id, AgentConfig.user_id == resolved_user(request), AgentConfig.custom == True)
    if not agent:
        raise HTTPException(status_code=404, detail="Custom agent not found")
    await agent.delete()
    return {"success": True}


@router.get("/{agent_id}")
async def get_agent(agent_id: str, request: Request) -> dict:
    # Check built-in agents first
    for agent in AGENT_METADATA:
        if agent["id"] == agent_id:
            return {**agent, "version": "0.1.0", "enabled": True}
    # Check custom agents in database
    custom_agent = await AgentConfig.find_one(
        AgentConfig.agent_id == agent_id,
        AgentConfig.user_id == resolved_user(request),
        AgentConfig.custom == True,
    )
    if custom_agent:
        return serialize_custom(custom_agent)
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


@router.post("/{agent_id}/run")
async def run_custom_agent(agent_id: str, request: Request, body: AgentRunRequest) -> StreamingResponse:
    user_id = resolved_user(request)
    agent = await AgentConfig.find_one(
        AgentConfig.agent_id == agent_id,
        AgentConfig.user_id == user_id,
        AgentConfig.custom == True,
        AgentConfig.enabled == True,
    )
    if not agent:
        raise HTTPException(status_code=404, detail=f"Custom agent '{agent_id}' not found")

    from src.services.llm import llm_service
    from src.utils.logger import logger

    async def gen():
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield sse("agent_run_start", {"agent_id": agent_id, "name": agent.name})

        tools = agent.tools or []
        extra = ""
        used_tools: list[str] = []
        try:
            if "web_search" in tools:
                from src.adk.tools import web_search

                res = await web_search(body.message, for_research=True)
                if res and "No search results" not in res:
                    extra += f"\n\nWEB SEARCH RESULTS:\n{res}"
                    used_tools.append("web search")
            if "knowledge_search" in tools or "knowledge" in tools:
                from src.adk.tools import knowledge_search

                res = await knowledge_search(body.message, user_id=user_id)
                if res and "No relevant documents" not in res:
                    extra += f"\n\nKNOWLEDGE BASE RESULTS:\n{res}"
                    used_tools.append("knowledge base")
            if "google_drive" in tools:
                from src.adk.tools import drive_list

                res = await drive_list(user_id=user_id)
                if res and "connect Google Drive" not in res and "empty" not in res:
                    extra += f"\n\nGOOGLE DRIVE FILES:\n{res}"
                    used_tools.append("Google Drive")
        except Exception as e:
            logger.warning(f"Custom agent tool run failed for {agent_id}: {e}")

        system = agent.system_instruction
        if extra:
            system += (
                "\n\nYou have access to tool results below. Use them as evidence when relevant, "
                "and mention the source (e.g. 'per web search') when you cite them."
            )
        full_prompt = body.message + extra

        tokens: list[str] = []
        try:
            async for chunk in llm_service.generate_stream(
                prompt=full_prompt,
                system_instruction=system,
                temperature=0.5,
            ):
                tokens.append(chunk)
                yield sse("agent_run_token", {"token": chunk})
        except Exception as e:
            logger.error(f"Custom agent execution error for {agent_id}: {e}")
            tokens.append(f"\n[Agent error: {e}]")
            yield sse("agent_run_token", {"token": f"\n[Agent error: {e}]"})

        yield sse("agent_run_complete", {"output": "".join(tokens), "tools": used_tools})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
