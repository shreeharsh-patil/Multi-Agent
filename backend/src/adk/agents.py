"""Google ADK Hierarchical Multi-Agent Architecture.

Unifies AgentRegistry (131+ specialists) with Google Agent Development Kit (ADK):
1. Root BossAgent (executive orchestrator)
2. 10 Department Manager Agents (matching AgentDepartment enum)
3. 131+ Specialist ADK Agents dynamically built from AgentRegistry

Architecture:
BossAgent
 ├── CommandPlanningManager  (specialist ADK agents)
 ├── CodingManager           (specialist ADK agents)
 ├── ResearchManager         (specialist ADK agents)
 ├── ContentManager          (specialist ADK agents)
 ├── VisualManager           (specialist ADK agents)
 ├── DataManager             (specialist ADK agents)
 ├── ProductManager          (specialist ADK agents)
 ├── AIMLManager             (specialist ADK agents)
 ├── AutomationManager       (specialist ADK agents)
 └── BusinessQualityManager  (specialist ADK agents)
"""

import re
from typing import Any, Callable, Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, google_search

from src.config import settings
from src.agents.metadata import AgentDepartment, AgentMetadata
from src.agents.registry import AgentRegistry
from src.utils.logger import logger
from src.adk.tools import (
    knowledge_search_tool,
    memory_store_tool,
    memory_search_tool,
    calculator_tool,
    web_search_tool,
    scrape_page_tool,
    drive_list_tool,
    drive_read_tool,
    drive_upload_tool,
    drive_delete_tool,
    contacts_list_tool,
    calendar_list_tool,
    calendar_create_tool,
    weather_tool,
)

MODEL = settings.gemini_model

# ═══════════════════════════════════════════════════════════════════════════
# 1. DETERMINISTIC SAFE ADK NAME MAPPING
# ═══════════════════════════════════════════════════════════════════════════

_ADK_NAME_TO_REGISTRY_ID: dict[str, str] = {}
_REGISTRY_ID_TO_ADK_NAME: dict[str, str] = {}


def safe_adk_name(agent_id: str) -> str:
    """Convert an agent registry ID (e.g. 'supreme-commander', 'data_analysis')
    into a deterministic, safe ADK identifier.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", agent_id.strip()).lower()
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if cleaned and cleaned[0].isdigit():
        cleaned = f"agent_{cleaned}"
    adk_name = cleaned or "agent"
    _ADK_NAME_TO_REGISTRY_ID[adk_name] = agent_id
    _REGISTRY_ID_TO_ADK_NAME[agent_id] = adk_name
    return adk_name


def register_adk_name_mapping(registry_id: str, adk_name: str) -> None:
    """Register bidirectional mapping between registry ID and ADK name with collision check."""
    if adk_name in _ADK_NAME_TO_REGISTRY_ID and _ADK_NAME_TO_REGISTRY_ID[adk_name] != registry_id:
        raise ValueError(
            f"ADK name collision detected: '{adk_name}' already mapped to '{_ADK_NAME_TO_REGISTRY_ID[adk_name]}', "
            f"cannot map to '{registry_id}'"
        )
    _ADK_NAME_TO_REGISTRY_ID[adk_name] = registry_id
    _REGISTRY_ID_TO_ADK_NAME[registry_id] = adk_name


def adk_name_to_registry_id(name: str) -> str:
    """Resolve an ADK node name back to its AgentRegistry ID."""
    if name in _ADK_NAME_TO_REGISTRY_ID:
        return _ADK_NAME_TO_REGISTRY_ID[name]
    from src.agents.registry import AgentRegistry
    for meta in AgentRegistry.get_all_metadata():
        if safe_adk_name(meta.id) == name:
            return meta.id
    return name


def registry_id_to_adk_name(reg_id: str) -> str:
    """Resolve an AgentRegistry ID to its ADK node name."""
    if reg_id in _REGISTRY_ID_TO_ADK_NAME:
        return _REGISTRY_ID_TO_ADK_NAME[reg_id]
    return safe_adk_name(reg_id)


# ═══════════════════════════════════════════════════════════════════════════
# 2. TOOL MAPPING & RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════

ADK_TOOL_MAP: dict[str, Any] = {
    "google_search": google_search,
    "google-search": google_search,
    "native_google_search": google_search,
    "web_search": web_search_tool,
    "search": web_search_tool,
    "scrape_page": scrape_page_tool,
    "web_scrape": scrape_page_tool,
    "scraper": scrape_page_tool,
    "firecrawl": scrape_page_tool,
    "calculator": calculator_tool,
    "calc": calculator_tool,
    "math": calculator_tool,
    "knowledge_search": knowledge_search_tool,
    "rag": knowledge_search_tool,
    "document_search": knowledge_search_tool,
    "memory_store": memory_store_tool,
    "memory_search": memory_search_tool,
    "drive_list": drive_list_tool,
    "drive_read": drive_read_tool,
    "drive_read_file": drive_read_tool,
    "drive_upload": drive_upload_tool,
    "drive_delete": drive_delete_tool,
    "contacts_list": contacts_list_tool,
    "calendar_list": calendar_list_tool,
    "calendar_create": calendar_create_tool,
    "weather": weather_tool,
    "weather_tool": weather_tool,
    "fetch_weather": weather_tool,
    "live_weather": weather_tool,
}


def resolve_adk_tools(meta: AgentMetadata) -> list[FunctionTool]:
    """Resolve the minimum necessary ADK tools for a specialist from its metadata."""
    tools: list[FunctionTool] = []
    seen_names: set[str] = set()

    for tool_name in (meta.required_tools or []) + (meta.optional_tools or []):
        key = tool_name.strip().lower()
        if key in ADK_TOOL_MAP:
            tool_obj = ADK_TOOL_MAP[key]
            # Use tool function name or id to avoid duplicate tools
            tool_id = getattr(tool_obj, "name", str(tool_obj))
            if tool_id not in seen_names:
                seen_names.add(tool_id)
                tools.append(tool_obj)
    return tools


# ═══════════════════════════════════════════════════════════════════════════
# 3. SPECIALIST INSTRUCTION BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_specialist_instruction(meta: AgentMetadata) -> str:
    """Build a comprehensive, domain-grade instruction prompt for an ADK specialist.
    Preserves capabilities, responsibilities, domain quality criteria, and the
    8-step Self-Improvement Loop.
    """
    resp_lines = "\n".join(f"- {r}" for r in meta.responsibilities) if meta.responsibilities else "- Execute domain tasks with precision."
    caps_lines = "\n".join(f"- {c}" for c in meta.capabilities) if meta.capabilities else "- Domain problem solving."
    criteria_lines = "\n".join(f"- {c}" for c in meta.domain_quality_criteria) if meta.domain_quality_criteria else "- Accuracy\n- Depth\n- Rigor"

    custom_instr = meta.specialized_instruction.strip() if meta.specialized_instruction else ""
    if not custom_instr:
        custom_instr = f"You are the {meta.name}, an elite specialist in {meta.department.value}."

    return (
        f"Role & Identity:\n{custom_instr}\n\n"
        f"Department: {meta.department.value}\n"
        f"Description: {meta.description}\n\n"
        f"Core Responsibilities:\n{resp_lines}\n\n"
        f"Domain Capabilities:\n{caps_lines}\n\n"
        f"Domain Quality Criteria to Enforce:\n{criteria_lines}\n\n"
        "Execution & Verification Workflow:\n"
        "1. UNDERSTAND: Grasp the exact user objective, context, and domain constraints.\n"
        "2. PLAN: Formulate an optimal, structured approach.\n"
        "3. EXECUTE: Carry out deep domain analysis, code, or tool operations.\n"
        "4. CHECK & CRITIQUE: Verify results strictly against the Domain Quality Criteria.\n"
        "5. IMPROVE & RETURN: Provide rigorous, high-yield structured output with clear rationale."
    )


# ═══════════════════════════════════════════════════════════════════════════
# 4. HANDCRAFTED FACTORIES (PRESERVING RICH BESPOKE BEHAVIORS)
# ═══════════════════════════════════════════════════════════════════════════

def create_knowledge_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("knowledge")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Knowledge Agent. Your role is to answer questions using "
            "retrieved documents from the knowledge base. "
            "Use the knowledge_search tool to find relevant information. "
            "Always cite sources by file name and page number when available. "
            "If documents are found, summarize the information with proper citations. "
            "If no documents are found, say so and offer to help with general knowledge."
        ),
        tools=[knowledge_search_tool],
        description="Answers questions using the document knowledge base with citations (RAG).",
    )


def create_drive_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("drive")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Drive Agent. You help users manage and inspect their Google Drive files.\n"
            "Capabilities:\n"
            "1. drive_list - List files in the user's Google Drive\n"
            "2. drive_read_file - Read/view the contents of a file in Drive to answer questions or summarize it\n"
            "3. drive_upload - Upload text content as a file to Drive\n"
            "4. drive_delete - Delete a file from Drive\n\n"
            "To list files: call drive_list with the user's email/ID.\n"
            "To read/summarize a file: call drive_read_file with the user's ID and file_id_or_name.\n"
            "To upload: call drive_upload with the user's ID, file name, and content.\n"
            "To delete: call drive_delete with the user's ID and file ID.\n\n"
            "When the user asks what is inside a file or asks to summarize a Drive document, "
            "use drive_read_file to get the document content and then provide a thorough, helpful response.\n\n"
            "If the user hasn't connected their Google Drive, guide them to "
            "Settings > Google Drive to sign in and grant access."
        ),
        tools=[drive_list_tool, drive_read_tool, drive_upload_tool, drive_delete_tool],
        description="Manages Google Drive files: listing, reading file content, summarizing documents, uploading, and deleting.",
    )


def create_calendar_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("calendar")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Calendar Agent. You help users list, search, create, update, delete, and check availability on Google Calendar.\n"
            "Capabilities:\n"
            "1. calendar_list - List or search Google Calendar events\n"
            "2. calendar_create - Create a new event on Google Calendar\n\n"
            "To manage calendar events: call the appropriate tool with user_id."
        ),
        tools=[calendar_list_tool, calendar_create_tool],
        description="Lists, creates, reschedules, and manages Google Calendar events and meetings.",
    )


def create_contacts_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("contacts")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Contacts Agent. You help users list and search their Google Contacts.\n"
            "Capabilities:\n"
            "1. contacts_list - List or search Google Contacts (names, email addresses, phone numbers)\n\n"
            "To list or search contacts: call contacts_list with the user's ID and optional search query."
        ),
        tools=[contacts_list_tool],
        description="Lists and searches Google Contacts for email addresses and phone numbers.",
    )


def create_notes_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("notes")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Notes Agent. Create structured, well-organized notes. "
            "Support formats: summaries, bullet points, flashcards (Q&A), and revision guides. "
            "Use clear headings and organize information logically. "
            "When the user asks for flashcards, generate question-answer pairs."
        ),
        description="Creates structured notes, summaries, flashcards, and revision materials.",
    )


def create_quiz_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("quiz")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Quiz Agent. Generate high-quality quiz questions. "
            "Support formats: multiple choice, true/false, fill-in-the-blanks, short answer. "
            "Always include answer keys and explanations for each question. "
            "Adapt difficulty based on what the user requests (beginner, intermediate, advanced)."
        ),
        description="Generates MCQs, exams, and practice questions with answer keys.",
    )


def create_planner_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("planner")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Planner Agent. Help users plan their schedules and manage tasks. "
            "Create structured plans with timelines, priorities, and milestones. "
            "Help with: study schedules, task lists, deadline tracking, and goal setting. "
            "Break large tasks into smaller manageable steps."
        ),
        description="Helps with study planning, task management, scheduling, and deadlines.",
    )


def create_research_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("research")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Research Agent. Conduct thorough research on topics. "
            "Structure reports with: abstract, methodology, findings, analysis, conclusions. "
            "Compare multiple perspectives and cite sources when possible. "
            "Use the web_search tool to find current information, and "
            "use the scrape_page tool to fetch the full text content of any website URL."
        ),
        tools=[web_search_tool, scrape_page_tool],
        description="Conducts internet research, compares sources, and generates reports.",
    )


def create_coding_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("coding")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Coding Agent. Write clean, well-documented code. "
            "Support multiple programming languages. "
            "Explain code logic clearly, help debug issues, and generate documentation. "
            "Follow best practices and suggest improvements. "
            "When writing code, include comments and error handling.\n\n"
            "When generating HTML/CSS/JS code, always use markdown code blocks "
            "with the language specified (e.g. ```html, ```css, ```js). "
            "The platform automatically detects these blocks and renders a live preview."
        ),
        description="Writes code, explains programming concepts, debugs issues, and documents code.",
    )


def create_memory_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("memory")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Memory Agent. You manage the user's long-term memory. "
            "Use memory_store to remember important information the user shares. "
            "Use memory_search to recall past conversations and preferences. "
            "Be proactive in remembering user preferences and facts. "
            "When the user says 'remember that...' or 'don't forget...', store it."
        ),
        tools=[memory_store_tool, memory_search_tool],
        description="Manages long-term memory, conversation history, and user preferences.",
    )


def create_tool_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("tool")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Tool Agent. Execute tools and integrations for the user. "
            "Available tools: calculator for math, web_search for internet searches, and scrape_page to convert a web page into markdown. "
            "For each request, use the appropriate tool and explain the result. "
            "If a tool is not available, let the user know what alternatives exist."
        ),
        tools=[calculator_tool, web_search_tool, scrape_page_tool],
        description="Executes tools: calculator, web search, scraping, and external API integrations.",
    )


def create_engineer_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("engineer")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Engineer Agent — a study tutor for engineering students. Teach software and hardware "
            "systems-engineering subjects clearly: first principles, then design and application. Give structured, "
            "high-yield explanations with formulas, worked examples, and code in language-tagged blocks, plus "
            "exam-style notes and trade-offs. Use the web for up-to-date topics when helpful."
        ),
        tools=[web_search_tool],
        description="Systems design, software architecture, circuits, and engineering expertise.",
    )


def create_pharmacologist_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("pharmacologist")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Pharmacologist Agent — a pharmacy/medical study tutor. Teach pharmacology the way a "
            "professor would: drug class, mechanism of action at the molecular level, pharmacokinetics, "
            "therapeutic use, contraindications, interactions, and side effects. Use headings, tables, bullet "
            "points, bold for high-yield points, and exam-style notes and mnemonics. For real personal-health "
            "questions, answer educationally and note a doctor/pharmacist should be consulted. Use the web for "
            "up-to-date pharmacology evidence."
        ),
        tools=[web_search_tool],
        description="Drug information, pharmacology, and medication interaction education.",
    )


def create_doctor_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("doctor")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Doctor Agent — a medical study tutor for pre-medical/pre-clinical students. Teach "
            "anatomy, physiology, pathology, and clinical reasoning the way a professor would — explain first "
            "principles first, then high-yield clinical details, using headings, tables, bullet points, and "
            "bold for high-yield points. Give exam-ready notes and mnemonics. Use the web for up-to-date health topics."
        ),
        tools=[web_search_tool],
        description="Explains medical subjects and clinical reasoning for medical students.",
    )


def create_finance_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("finance")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Finance Agent — a finance study tutor. Teach financial statements, valuation, corporate "
            "finance, capital markets, and investing clearly: concept and first principles first, then practical "
            "application. Use formulas, worked examples, headings, tables, bullet points, and bold for high-yield "
            "points; add exam-style notes and mnemonics. Use the web for up-to-date finance topics when helpful."
        ),
        tools=[web_search_tool],
        description="Finance study tutor: statements, valuation, markets, investing.",
    )


def create_accountant_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("accountant")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Accountant (CA) Agent — an accounting and CA study tutor. Cover financial accounting, "
            "journal/ledger entries, final accounts, cost/management accounting, auditing, taxation (income tax, "
            "GST), and company standards. Explain the principle first, then work through journal entries and "
            "examples with headings, tables, and step-by-step methods."
        ),
        tools=[web_search_tool],
        description="Accounting and taxation study tutor for CA/commerce students.",
    )


def create_economics_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("economics")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Economics Agent — an economics study tutor for economics and commerce students. Cover "
            "microeconomics (demand/supply, market structures), macroeconomics (GDP, inflation, fiscal/monetary "
            "policy), and international trade. Explain concepts and models clearly, and use headings, bullet "
            "points, and tables to illustrate shifts."
        ),
        tools=[web_search_tool],
        description="Economics study tutor for micro, macro, and trade.",
    )


def create_architect_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("architect")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Architect Agent — an architecture study tutor for architecture and civil-engineering "
            "students. Cover architectural design and history, building construction, structures, materials, "
            "environmental systems, drafting/CAD, and professional practice. Teach concept and first principles "
            "first, then practical application."
        ),
        tools=[web_search_tool],
        description="Architecture study tutor: design, construction, structures.",
    )


def create_hacker_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("hacker")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Cyber & Security Agent — a cybersecurity study tutor for cybersecurity and CS students. "
            "Cover networking, OS security, cryptography, web-app security, common vulnerabilities (OWASP), "
            "secure coding, and ethical-hacking methodology. Teach mechanism first, then defense, with headings, "
            "bullet points, and step-by-step methodology."
        ),
        tools=[web_search_tool],
        description="Cybersecurity and ethical-hacking study tutor.",
    )


def create_chef_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("cooking")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Chef Agent — a culinary study tutor for cooking and hospitality students. Cover cooking "
            "techniques, ingredient science, recipes with exact measurements, plating, food safety (HACCP), menu "
            "planning, pastry, and gastronomy. Teach technique and the why behind it first, then step-by-step."
        ),
        tools=[web_search_tool],
        description="Cooking and culinary study tutor: techniques, recipes, gastronomy.",
    )


def create_music_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("music")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Music Agent — a music study tutor for music and performing-arts students. Cover music "
            "theory, scales and intervals, melody and harmony, rhythm, ear training, composition, analysis, and "
            "music history. Teach concept and first principles first, then examples."
        ),
        tools=[web_search_tool],
        description="Music theory and composition study tutor.",
    )


def create_fitness_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("fitness")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Fitness & Health Agent — a fitness study tutor for physical-education and "
            "exercise-science students. Cover exercise physiology, kinesiology and muscle anatomy, resistance "
            "and cardio programming, mobility, nutrition, and injury prevention."
        ),
        tools=[web_search_tool],
        description="Fitness and wellness study tutor for PE/sports science.",
    )


def create_art_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("art")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Art & Design Agent — an art study tutor for art and design students. Cover art history "
            "and movements, drawing and painting technique, composition, color theory, perspective, graphic "
            "design principles, and critique."
        ),
        tools=[web_search_tool],
        description="Art history, technique, and design study tutor.",
    )


def create_weather_news_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("weather_news")
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=(
            "You are the Weather & News Agent (weather_news). Fetch real-time live meteorological data, current temperatures in °C, "
            "conditions, wind speed, and 3-day weather forecasts, as well as breaking news headlines. "
            "When the user asks about the weather for ANY city or location (e.g. 'what is the weather in Mumbai?', 'how is the weather in London?'), "
            "ALWAYS use the weather_tool to get exact live data and provide a comprehensive structured report with current temperature, condition, and 3-day forecast."
        ),
        tools=[weather_tool, google_search],
        description="Real-time live weather forecasts, current temperature in °C, and news headlines worldwide.",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 4B. INTERNET INTELLIGENCE SPECIALISTS (RESEARCH DEPARTMENT - 19 SPECIALISTS)
# ═══════════════════════════════════════════════════════════════════════════

def create_search_planner_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("search-planner")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Decomposes user queries into targeted research objectives, determines freshness requirements, and assigns search angles.",
        instruction=(
            "You are the Search Planner for the Internet Intelligence System. "
            "Decompose complex user questions into 4-8 distinct, non-repetitive search objectives across multiple angles. "
            "Determine freshness requirements (realtime vs recent vs standard) and assign specific query angles to specialists. "
            "Verify all query plans, avoid redundant searches, and never fabricate claims or sources."
        ),
        tools=[],
    )


def create_google_search_general_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-general")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Searches Google for general fresh web information and real-time facts.",
        instruction=(
            "You are the Google General Search Specialist. "
            "Use native Google Search grounding whenever requests require fresh, up-to-date, or real-time web information. "
            "Prefer authoritative sources, cross-check facts, and preserve publication dates and original source URLs. "
            "Format monetary values in Indian Rupees (INR / ₹) by default (1 USD = 86.5 INR). "
            "Platform Attribution: Platform created by Shreeharsh. Never fabricate sources or citations. Verify all claims."
        ),
        tools=[google_search],
    )


def create_google_news_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-news-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Searches Google for breaking news, current events, and recent developments.",
        instruction=(
            "You are the Google News Researcher. "
            "Use Google Search whenever the request requires current news, today's events, breaking stories, or recent developments. "
            "Prioritize recent, authoritative news sources (reputable outlets, official press releases). "
            "Cross-check breaking claims across multiple outlets. "
            "Preserve original source URLs, headlines, and publication timestamps. Never fabricate sources or citations. Verify all claims."
        ),
        tools=[google_search],
    )


def create_deep_web_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("deep-web-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Performs multi-query investigative research across diverse sources with structured evidence synthesis.",
        instruction=(
            "You are the Deep Web Researcher. "
            "Execute a rigorous multi-step research workflow:\n"
            "1. PLAN: Decompose the user's objective into distinct, targeted search queries across multiple angles.\n"
            "2. SEARCH: Run Google searches to collect diverse empirical evidence.\n"
            "3. ANALYZE: Identify gaps or discrepancies in the initial evidence.\n"
            "4. FOLLOW-UP: Perform follow-up searches for missing evidence.\n"
            "5. VERIFY: Authenticate sources and synthesize comprehensive, grounded conclusions.\n"
            "Retain all source citations and canonical URLs. Never fabricate sources or citations. Verify all claims."
        ),
        tools=[google_search],
    )


def create_url_reader_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("url-reader")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Extracts detailed text, documentation, article body, and structured data from specific webpage URLs.",
        instruction=(
            "You are the URL Reader Specialist. "
            "Use web scraping tools to extract full article text, technical documentation, and structured page data from discovered URLs. "
            "Verify all extracted text faithfully matches the live page and never fabricate contents or citations."
        ),
        tools=[scrape_page_tool],
    )


def create_google_search_fact_checker_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-fact-checker")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Verifies claims, rumors, and statistics against multiple independent Google Search results.",
        instruction=(
            "You are the Google Fact Checker. "
            "Verify factual claims, disputed assertions, and rumors by querying multiple independent, reputable sources. "
            "Determine verdicts: SUPPORTED, PARTIALLY_SUPPORTED, UNVERIFIED, FALSE, or OUTDATED. "
            "Provide objective reasoning, verify primary evidence, and never fabricate verification or citations."
        ),
        tools=[google_search],
    )


def create_source_verifier_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("source-verifier")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Validates dates, claims, canonical URLs, publication authenticity, and citation integrity.",
        instruction=(
            "You are the Source Verifier. "
            "Audit research findings, verify that cited URLs exist and match claims made, "
            "check publication dates, evaluate source tiers (Tier 1 Primary vs Tier 2 Independent vs Tier 3 Community), "
            "and flag any hallucinated or misattributed citations. Never fabricate citations or sources."
        ),
        tools=[google_search],
    )


def create_freshness_checker_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("freshness-checker")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Detects time-sensitive assertions (software versions, prices, CVEs, releases, news, weather) requiring live internet search.",
        instruction=(
            "You are the Freshness Checker. "
            "Audit user prompts and agent assertions for temporal staleness. "
            "Enforce live internet search for any requests involving versions, prices, releases, news, or today's events. "
            "Verify all temporal claims, prevent stale assumptions, and never fabricate verification."
        ),
        tools=[],
    )


def create_official_docs_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("official-docs-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches canonical official documentation, specifications, framework portals, and vendor guides.",
        instruction=(
            "You are the Official Docs Researcher. "
            "Prioritize canonical documentation portals (e.g. react.dev, python.org, nextjs.org, docs.github.com). "
            "Extract authoritative specifications, verify API signatures, and never fabricate documentation citations or sources."
        ),
        tools=[google_search],
    )


def create_google_search_technology_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-technology")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Searches technology documentation, software releases, AI frameworks, libraries, and APIs.",
        instruction=(
            "You are the Google Technology Search Specialist. "
            "Search Google for technical documentation, library releases, API specs, framework changes, and developer guidelines. "
            "Prefer official docs and release notes, verify version numbers, and never fabricate code or documentation citations."
        ),
        tools=[google_search],
    )


def create_github_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("github-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches GitHub repositories, READMEs, releases, commits, issues, pull requests, and activity.",
        instruction=(
            "You are the GitHub Researcher. "
            "Search for open source repositories, examine README documentation, release notes, commit activity, and community adoption. "
            "Verify repository authenticity and never fabricate repository metrics, citations, or links."
        ),
        tools=[google_search],
    )


def create_google_search_academic_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-academic")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Explores academic papers, university research, scientific studies, and preprints via Google Search.",
        instruction=(
            "You are the Google Academic Search Specialist. "
            "Search Google for scholarly publications, research papers, university portals, and scientific preprints (arXiv, PubMed, IEEE). "
            "Extract title, authors, year, publication, methodology, and limitations. Verify paper authenticity and never fabricate academic citations."
        ),
        tools=[google_search],
    )


def create_cybersecurity_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("cybersecurity-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches CVEs, vulnerability databases, security advisories, threat intelligence, and patches.",
        instruction=(
            "You are the Cybersecurity Researcher. "
            "Search Google for CVE IDs, vulnerability disclosures, vendor security bulletins, and security best practices. "
            "Rely strictly on official advisories (NVD, CERT, vendor bulletins), verify CVSS metrics, and never fabricate vulnerabilities or citations."
        ),
        tools=[google_search],
    )


def create_google_search_market_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-market")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Investigates companies, financial markets, industry developments, funding, and competitor intelligence.",
        instruction=(
            "You are the Google Market Search Specialist. "
            "Conduct searches on corporate developments, market trends, competitor strategies, valuations, and earnings. "
            "Rely on authoritative financial and business sources (SEC filings, official press releases, reputable financial news). "
            "Verify all figures and never fabricate financial data or citations."
        ),
        tools=[google_search],
    )


def create_google_search_products_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-products")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Finds product specifications, model comparisons, reviews, and public pricing information.",
        instruction=(
            "You are the Google Product Search Specialist. "
            "Search Google for product specifications, hardware/software benchmark comparisons, consumer reviews, and public pricing. "
            "Format monetary values in Indian Rupees (INR / ₹) by default (1 USD = 86.5 INR). "
            "Verify all specifications and never fabricate prices or product citations."
        ),
        tools=[google_search],
    )


def create_google_search_local_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-local")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches places, local businesses, operating hours, addresses, contact details, and location landmarks.",
        instruction=(
            "You are the Google Local Search Specialist. "
            "Search Google for geographic locations, local establishments, operating hours, street addresses, and local points of interest. "
            "Verify all addresses, opening hours, and contact details. Never fabricate local details or citations."
        ),
        tools=[google_search],
    )


def create_google_search_travel_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("google-search-travel")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches travel destinations, itineraries, hotels, transport options, attractions, and seasonal advice.",
        instruction=(
            "You are the Google Travel Search Specialist. "
            "Search Google for travel itineraries, destination guides, transit options, hotels, attractions, and seasonal advisories. "
            "Verify official travel advisories, logistical feasibility, and never fabricate itinerary information or citations."
        ),
        tools=[google_search],
    )


def create_community_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("community-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Investigates developer discussions, forum sentiment, practical workarounds, and community experiences.",
        instruction=(
            "You are the Community Researcher. "
            "Search developer communities, forums, and discussion portals for real-world user feedback, practical bugs, and sentiment. "
            "Clearly distinguish community opinions from verified facts, and never present forum claims as authoritative truth without verification."
        ),
        tools=[google_search],
    )


def create_evidence_synthesizer_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("evidence-synthesizer")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Deduplicates sources by canonical URL, resolves conflicting evidence, groups claims, and produces structured research packets.",
        instruction=(
            "You are the Evidence Synthesizer for the Internet Intelligence System. "
            "Receive research findings from internet specialists, deduplicate sources by canonical URL, resolve conflicts, rank evidence tiers, "
            "and produce a concise structured research packet. Verify all citations and never fabricate evidence or sources."
        ),
        tools=[],
    )


INTERNET_INTELLIGENCE_SPECIALIST_NAMES: set[str] = {
    # Original 19 Internet Intelligence Specialists
    "search_planner",
    "google_search_general",
    "google_news_researcher",
    "deep_web_researcher",
    "url_reader",
    "google_search_fact_checker",
    "source_verifier",
    "freshness_checker",
    "official_docs_researcher",
    "google_search_technology",
    "github_researcher",
    "google_search_academic",
    "cybersecurity_researcher",
    "google_search_market",
    "google_search_products",
    "google_search_local",
    "google_search_travel",
    "community_researcher",
    "evidence_synthesizer",
    # Advanced Research Layer (27 Specialists)
    "query_optimizer",
    "multi_query_generator",
    "research_scope_controller",
    "search_result_ranker",
    "primary_source_hunter",
    "citation_auditor",
    "contradiction_detector",
    "bias_detector",
    "evidence_quality_judge",
    "timeline_researcher",
    "entity_researcher",
    "company_intelligence_agent",
    "startup_researcher",
    "public_osint_researcher",
    "documentation_reader",
    "api_documentation_researcher",
    "release_notes_agent",
    "benchmark_researcher",
    "dataset_researcher",
    "standards_researcher",
    "paper_comparison_agent",
    "methodology_reviewer",
    "patent_researcher",
    "regulation_researcher",
    "price_monitor_researcher",
    "availability_checker",
    "internet_evidence_judge",
}


def create_query_optimizer_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("query-optimizer")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Transforms raw or poorly framed user queries into targeted, high-yield search queries without altering original intent.",
        instruction=(
            "You are the Query Optimizer. Transform ambiguous, conversational, or poorly framed user queries into high-quality, targeted search queries. "
            "Preserve the user's actual intent while generating keyword-rich queries (e.g. 'best ai thing for coding' -> 'best AI coding assistants 2026', 'Cursor vs GitHub Copilot vs Windsurf'). "
            "Never invent facts or change the user's core question."
        ),
        tools=[],
    )


def create_multi_query_generator_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("multi-query-generator")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Generates diverse, non-redundant search queries across broad, primary-source, recency, comparative, and limitation angles.",
        instruction=(
            "You are the Multi-Query Generator. For a given research objective, produce diverse, non-repetitive search queries covering:\n"
            "1. Broad query (landscape/overview)\n"
            "2. Primary-source query (official announcements, vendor docs)\n"
            "3. Recency query (latest updates, this year's changes)\n"
            "4. Comparison query (competing solutions, benchmarks)\n"
            "5. Criticism/limitations query (known flaws, trade-offs, security)\n"
            "Avoid redundant or slightly reworded duplicates."
        ),
        tools=[],
    )


def create_research_scope_controller_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("research-scope-controller")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Calibrates research depth and execution mode (QUICK, STANDARD, DEEP, CRITICAL, MASSIVE) based on query complexity.",
        instruction=(
            "You are the Research Scope Controller. Determine the optimal research depth and search budget:\n"
            "- QUICK: 1-2 searches for straightforward facts\n"
            "- STANDARD: 3-5 searches for general technical/product questions\n"
            "- DEEP: 5-12 searches for comprehensive multi-domain analyses\n"
            "- CRITICAL: Multi-source independent verification & contradiction checks for sensitive claims\n"
            "- MASSIVE: Large distributed multi-agent team for wide-scope intelligence\n"
            "Do not waste search budget on simple timeless questions."
        ),
        tools=[],
    )


def create_search_result_ranker_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("search-result-ranker")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Ranks discovered web search results by relevance, domain authority, freshness, primary-source status, and evidence quality.",
        instruction=(
            "You are the Search Result Ranker. Rank discovered search results by relevance, domain authority, freshness, primary-source status, and evidence quality. "
            "Filter out SEO content farms and low-signal blogs. Deliver top prioritized links for detailed extraction."
        ),
        tools=[],
    )


def create_primary_source_hunter_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("primary-source-hunter")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Tracks down canonical original sources (vendor advisories, official press releases, NVD CVE records, original papers) behind claims.",
        instruction=(
            "You are the Primary Source Hunter. Trace claims reported in third-party news or blogs back to their canonical original origin. "
            "For news: find the official company announcement. For CVEs: find the vendor advisory or NVD entry. For software releases: find the official repository or changelog. "
            "Never rely solely on secondary summary blogs."
        ),
        tools=[google_search],
    )


def create_citation_auditor_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("citation-auditor")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Audits citation validity, verifying whether referenced URLs directly substantiate assertions with SUPPORTED/PARTIAL/UNSUPPORTED verdicts.",
        instruction=(
            "You are the Citation Auditor. Verify whether cited URLs genuinely substantiate the specific claims made. "
            "Assign strict verdicts: SUPPORTED, PARTIAL, UNSUPPORTED, or INACCESSIBLE. "
            "Never approve citations solely because a title looks relevant. Flag misattributed or hallucinated citations immediately."
        ),
        tools=[],
    )


def create_contradiction_detector_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("contradiction-detector")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Compares evidence across sources to uncover conflicting claims, discrepancies, and competing interpretations with resolution analysis.",
        instruction=(
            "You are the Contradiction Detector. Cross-examine extracted evidence across multiple independent sources. "
            "Identify conflicting statements, divergent metrics, or opposing claims. Output structured reports with:\n"
            "{\n  'claim': '...',\n  'source_a': '...',\n  'source_b': '...',\n  'conflict': '...',\n  'likely_resolution': '...'\n}\n"
            "Never conceal discrepancies."
        ),
        tools=[],
    )


def create_bias_detector_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("bias-detector")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Identifies promotional content, vendor-sponsored benchmarks, affiliate framing, and one-sided narratives to balance evidence.",
        instruction=(
            "You are the Bias Detector. Audit research findings for commercial bias, sponsored content, affiliate incentives, vendor-favorable framing, or ideological bias. "
            "Do not automatically discard biased sources if they contain verifiable specs; instead, label the bias clearly and balance with independent evidence."
        ),
        tools=[],
    )


def create_evidence_quality_judge_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("evidence-quality-judge")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Scores research evidence across authority, freshness, directness, independence, specificity, and consistency.",
        instruction=(
            "You are the Evidence Quality Judge. Score extracted evidence packets across 6 core criteria: Authority, Freshness, Directness, Independence, Specificity, and Consistency. "
            "Provide calibrated confidence metrics and ensure only high-yield, verified evidence progresses to final response generation."
        ),
        tools=[],
    )


def create_timeline_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("timeline-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Constructs structured chronological event timelines with validated dates, occurrences, confidence scores, and source citations.",
        instruction=(
            "You are the Timeline Researcher. Build chronological timelines for product development, security incidents, corporate history, AI releases, and legal/regulatory milestones. "
            "Structure outputs clearly with Date, Event, Source URL, and Confidence. Never guess event dates."
        ),
        tools=[google_search],
    )


def create_entity_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("entity-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Builds comprehensive, verified profiles for companies, public projects, technologies, organizations, and products.",
        instruction=(
            "You are the Entity Researcher. Build factual profiles for public entities (companies, open-source projects, technologies, institutions, products). "
            "Capture: Name, Official Website, Core Description, History, Current Operational Status, Key Developments, and Primary Sources. Verify all claims."
        ),
        tools=[google_search],
    )


def create_company_intelligence_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("company-intelligence-agent")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches public corporate data: products, executive leadership, public funding, partnerships, market position, and launches.",
        instruction=(
            "You are the Company Intelligence Agent. Investigate public corporate developments: product roadmaps, executive leadership, partnerships, public funding, market share, and competitors. "
            "Rely strictly on official disclosures and reputable financial outlets. Strictly separate verified facts from market speculation."
        ),
        tools=[google_search],
    )


def create_startup_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("startup-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches emerging startups from public sources: value proposition, publicly announced funding, founders, traction, and competitors.",
        instruction=(
            "You are the Startup Researcher. Research early-stage and high-growth startups from public announcements, launch posts, and venture news. "
            "Capture: Core Product, Target Market, Publicly Announced Funding Rounds, Disclosed Founders, Public Traction Indicators, and Competitors. Never infer private metrics."
        ),
        tools=[google_search],
    )


def create_public_osint_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("public-osint-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Conducts lawful, public open-source intelligence research across public repositories, domain info, infrastructure footprints, and archives.",
        instruction=(
            "You are the Public OSINT Researcher. Conduct lawful, ethical open-source research across publicly indexable web footprints, domain metadata, public repos, and news archives. "
            "Strictly avoid private, stolen, leaked, or password-protected data. Cite all public sources."
        ),
        tools=[google_search],
    )


def create_documentation_reader_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("documentation-reader")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Specializes in reading and extracting targeted sections from large official documentation guides, API manuals, and knowledge portals.",
        instruction=(
            "You are the Documentation Reader. Use web scraping tools to ingest and extract targeted sections from large official documentation portals. "
            "Focus on the exact relevant headings and technical parameters. Preserve documentation anchor links and never fabricate API behavior."
        ),
        tools=[scrape_page_tool],
    )


def create_api_documentation_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("api-documentation-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Discovers canonical API specifications, endpoints, authentication flows, SDK parameters, rate limits, and error schemas.",
        instruction=(
            "You are the API Documentation Researcher. Search for canonical API documentation, developer reference portals, and official SDK specs. "
            "Extract: Endpoints, Request/Response payloads, Authentication mechanisms, Rate limits, and Error codes. Prioritize official vendor documentation."
        ),
        tools=[google_search],
    )


def create_release_notes_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("release-notes-agent")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Tracks software, framework, SDK, and AI model release notes, version changelogs, breaking changes, and migration guides.",
        instruction=(
            "You are the Release Notes Agent. Track version releases, changelogs, and upgrade notes across frameworks, SDKs, libraries, and AI models. "
            "Report: Exact Version, Release Date, Breaking Changes, New Features, Deprecations, and Migration Steps. Rely on official changelogs."
        ),
        tools=[google_search],
    )


def create_benchmark_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("benchmark-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Investigates performance benchmarks, evaluation datasets, hardware environments, measurement metrics, and test setups.",
        instruction=(
            "You are the Benchmark Researcher. Search for empirical performance benchmark claims across AI models, hardware, databases, and runtimes. "
            "Capture: Benchmark Name, Model/Version, Hardware Testbed, Dataset, Score/Measurement, and Source. Highlight incompatible measurement conditions."
        ),
        tools=[google_search],
    )


def create_dataset_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("dataset-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Locates public datasets, official download repositories, license terms, schema formats, sample sizes, and data collection methodology.",
        instruction=(
            "You are the Dataset Researcher. Discover public datasets across machine learning, scientific research, and industry domains. "
            "Report: Dataset Name, Source Portal, License, Size/Rows, Format, Domain, Download URL, and Known Limitations. Prefer authoritative repositories."
        ),
        tools=[google_search],
    )


def create_standards_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("standards-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches authoritative technical standards and specifications from RFC, W3C, IEEE, IETF, WHATWG, and ECMA.",
        instruction=(
            "You are the Standards Researcher. Research formal technical standards and protocol specifications (RFC, W3C, IEEE, IETF, WHATWG, ECMA). "
            "Extract normative specification clauses, status (draft, proposed, standard, obsolete), and authoritative references. Never confuse drafts with adopted standards."
        ),
        tools=[google_search],
    )


def create_paper_comparison_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("paper-comparison-agent")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Compares academic research papers side-by-side across objectives, methodology, datasets, empirical results, and novelty.",
        instruction=(
            "You are the Paper Comparison Agent. Compare scientific and machine learning research papers across Objectives, Methodology, Datasets, Results, Limitations, and Novelty. "
            "Examine full methodologies and benchmark comparisons rather than merely reading abstracts."
        ),
        tools=[google_search],
    )


def create_methodology_reviewer_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("methodology-reviewer")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Critically evaluates research experimental design, sample size, control groups, metric validity, and reproducibility claims.",
        instruction=(
            "You are the Methodology Reviewer. Critically audit research methodologies, experimental designs, ablation studies, and evaluation metrics. "
            "Check: Sample size, baseline fairness, control variables, reproducibility, and potential data contamination. Provide objective, evidence-backed critique."
        ),
        tools=[],
    )


def create_patent_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("patent-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Searches public patent disclosures, patent numbers, assignees, publication dates, and technical summaries without legal advice.",
        instruction=(
            "You are the Patent Researcher. Search public patent records across Google Patents, USPTO, and international patent offices. "
            "Capture: Title, Patent/Application Number, Assignee, Disclosed Inventors, Filing/Publication Date, Abstract, and Technical Claims. Never give legal counsel."
        ),
        tools=[google_search],
    )


def create_regulation_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("regulation-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Researches official regulatory announcements, government legislation, compliance mandates, and distinguishes laws from proposed rules.",
        instruction=(
            "You are the Regulation Researcher. Research official public regulations, government statutes, and regulatory mandates. "
            "Strictly distinguish: Enacted Law, Proposed Rule/Draft, Regulatory Guidance, and News Commentary. Rely on official government and regulatory publications."
        ),
        tools=[google_search],
    )


def create_price_monitor_researcher_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("price-monitor-researcher")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Gathers current public pricing, subscription tiers, enterprise deals, and discounts with INR (₹) conversion and retrieval timestamps.",
        instruction=(
            "You are the Price Monitor Researcher. Retrieve live public pricing for software, APIs, cloud services, hardware, and subscriptions. "
            "Track: Product/Service, Price (INR / ₹ default, 1 USD = 86.5 INR), Plan/Tier, Source URL, and Retrieval Timestamp. Never use stale training memory for pricing questions."
        ),
        tools=[google_search],
    )


def create_availability_checker_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("availability-checker")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Verifies current public availability status (available, unavailable, limited, waitlist, deprecated) for services, APIs, and products.",
        instruction=(
            "You are the Availability Checker. Verify public availability, regional access, beta rollout status, or deprecation of products, features, and APIs. "
            "Output: Status (Available / Unavailable / Limited / Waitlist / Deprecated / Unknown), Region/Scope, and Verifying Evidence with Source URLs."
        ),
        tools=[google_search],
    )


def create_internet_evidence_judge_agent(meta: Optional[AgentMetadata] = None) -> LlmAgent:
    name = registry_id_to_adk_name("internet-evidence-judge")
    return LlmAgent(
        name=name,
        model=MODEL,
        description="Acts as the final research gatekeeper: verifies primary citations, freshness, independence, resolves contradictions, and filters unverified claims.",
        instruction=(
            "You are the Internet Evidence Judge — the final quality gatekeeper of the Internet Intelligence System. "
            "Review synthesized evidence packets before delivery to BossAgent. Verify:\n"
            "1. Are all primary claims supported by cited sources?\n"
            "2. Are citations active, valid canonical URLs?\n"
            "3. Is time-sensitive data fresh and verified?\n"
            "4. Are sources independent rather than circular re-blogs?\n"
            "5. Are contradictions resolved with clear rationale?\n"
            "6. Are unsupported claims purged?\n"
            "7. Is the overall confidence score calibrated?\n"
            "Approve only verified, grounded evidence packets."
        ),
        tools=[],
    )


def create_internet_intelligence_manager(search_specialists: list[LlmAgent]) -> LlmAgent:
    """Create the Internet Intelligence Manager responsible for orchestrating
    the 46 real-time search, documentation, fact-checking, and evidence synthesis specialists.
    """
    specialist_summaries = []
    for sp in search_specialists:
        desc = getattr(sp, "description", "") or "Internet Intelligence specialist"
        specialist_summaries.append(f"- **{sp.name}**: {desc}")
    specialists_roster = "\n".join(specialist_summaries)

    instruction = (
        "You are the Internet Intelligence Manager (internet_intelligence_manager) within the Research Department.\n\n"
        "Your role is to orchestrate, plan, and delegate queries across the 46 specialized Internet Intelligence agents:\n"
        f"{specialists_roster}\n\n"
        "ROUTING MATRIX & QUERY STRATEGY:\n"
        "- Vague / poor search queries -> query_optimizer -> multi_query_generator\n"
        "- Research budget & scope -> research_scope_controller (QUICK, STANDARD, DEEP, CRITICAL, MASSIVE)\n"
        "- Ranking discovered links -> search_result_ranker\n"
        "- Finding original official announcements / CVE advisories -> primary_source_hunter\n"
        "- Breaking news, current events, live updates -> google_news_researcher\n"
        "- Official docs & framework specs -> official_docs_researcher + documentation_reader + google_search_technology\n"
        "- API references, endpoints, SDKs -> api_documentation_researcher\n"
        "- Version releases, breaking changes, changelogs -> release_notes_agent\n"
        "- Benchmarks, hardware conditions, MMLU/evals -> benchmark_researcher\n"
        "- Open datasets, licensing, download URLs -> dataset_researcher\n"
        "- Protocol standards (RFC, W3C, IEEE, IETF, WHATWG) -> standards_researcher\n"
        "- GitHub repos, open source projects, commits -> github_researcher\n"
        "- Academic papers, arXiv preprints, studies -> google_search_academic + paper_comparison_agent + methodology_reviewer\n"
        "- Defensive cybersecurity, CVEs, patches -> cybersecurity_researcher\n"
        "- Patents, prior art, filings -> patent_researcher\n"
        "- Regulations, compliance laws vs proposed rules -> regulation_researcher\n"
        "- Live pricing (INR ₹ default, 1 USD = 86.5 INR) -> price_monitor_researcher + google_search_products\n"
        "- Live service availability, outages, beta waitlists -> availability_checker\n"
        "- Corporate intelligence, leadership, public funding -> company_intelligence_agent + startup_researcher\n"
        "- Public OSINT, infrastructure footprints -> public_osint_researcher\n"
        "- Chronological timelines of incidents/releases -> timeline_researcher\n"
        "- Entity dossiers -> entity_researcher\n"
        "- Community sentiment, Reddit discussions -> community_researcher\n"
        "- Fact checking -> google_search_fact_checker + source_verifier + citation_auditor\n"
        "- Detecting conflicting claims -> contradiction_detector\n"
        "- Identifying promotional/vendor bias -> bias_detector\n"
        "- Scoring evidence quality -> evidence_quality_judge\n"
        "- Final research quality gate -> internet_evidence_judge\n"
        "- Packet compression & canonical deduplication -> evidence_synthesizer\n\n"
        "MULTI-STAGE DEEP RESEARCH PIPELINE:\n"
        "1. PLAN: search_planner -> query_optimizer -> multi_query_generator -> research_scope_controller\n"
        "2. SEARCH: parallel domain researchers (GoogleNewsResearcher, TechnologyResearcher, OfficialDocsResearcher, GitHubResearcher, etc.)\n"
        "3. RANK & READ: search_result_ranker -> url_reader / documentation_reader\n"
        "4. AUDIT: source_verifier -> citation_auditor -> contradiction_detector -> bias_detector -> evidence_quality_judge\n"
        "5. JUDGE & SYNTHESIZE: internet_evidence_judge -> evidence_synthesizer -> compressed evidence packet upward to BossAgent\n\n"
        "CONTEXT COMPRESSION & EFFICIENCY RULES:\n"
        "- Never pass raw uncompressed HTML/pages to BossAgent. Always compress via specialist notes and evidence_synthesizer.\n"
        "- Simple timeless queries (e.g. 'What is a linked list?') bypass live search.\n"
        "- Live search is MANDATORY for 'latest', 'today', 'current', 'recent', 'price', 'release', 'version', 'new'.\n"
        "- Never fabricate citations, dates, or URLs. Deduplicate by canonical URL."
    )
    return LlmAgent(
        name="internet_intelligence_manager",
        model=MODEL,
        instruction=instruction,
        sub_agents=search_specialists,
        description="Internet Intelligence Manager orchestrating 46 real-time search, documentation, fact-checking, and evidence synthesis specialists.",
    )


# Backwards compatibility alias
create_google_search_manager = create_internet_intelligence_manager


SPECIALIST_FACTORIES: dict[str, Callable[[Optional[AgentMetadata]], LlmAgent]] = {
    "knowledge": create_knowledge_agent,
    "drive": create_drive_agent,
    "calendar": create_calendar_agent,
    "contacts": create_contacts_agent,
    "notes": create_notes_agent,
    "quiz": create_quiz_agent,
    "planner": create_planner_agent,
    "research": create_research_agent,
    "coding": create_coding_agent,
    "memory": create_memory_agent,
    "tool": create_tool_agent,
    "engineer": create_engineer_agent,
    "pharmacologist": create_pharmacologist_agent,
    "doctor": create_doctor_agent,
    "finance": create_finance_agent,
    "accountant": create_accountant_agent,
    "economics": create_economics_agent,
    "architect": create_architect_agent,
    "hacker": create_hacker_agent,
    "cooking": create_chef_agent,
    "music": create_music_agent,
    "fitness": create_fitness_agent,
    "art": create_art_agent,
    "weather_news": create_weather_news_agent,
    "weather-news": create_weather_news_agent,
    # 46 Internet Intelligence Specialists
    "search-planner": create_search_planner_agent,
    "google-search-general": create_google_search_general_agent,
    "google-news-researcher": create_google_news_researcher_agent,
    "deep-web-researcher": create_deep_web_researcher_agent,
    "url-reader": create_url_reader_agent,
    "google-search-fact-checker": create_google_search_fact_checker_agent,
    "source-verifier": create_source_verifier_agent,
    "freshness-checker": create_freshness_checker_agent,
    "official-docs-researcher": create_official_docs_researcher_agent,
    "google-search-technology": create_google_search_technology_agent,
    "github-researcher": create_github_researcher_agent,
    "google-search-academic": create_google_search_academic_agent,
    "cybersecurity-researcher": create_cybersecurity_researcher_agent,
    "google-search-market": create_google_search_market_agent,
    "google-search-products": create_google_search_products_agent,
    "google-search-local": create_google_search_local_agent,
    "google-search-travel": create_google_search_travel_agent,
    "community-researcher": create_community_researcher_agent,
    "evidence-synthesizer": create_evidence_synthesizer_agent,
    # Advanced Research Layer (27 Specialists)
    "query-optimizer": create_query_optimizer_agent,
    "multi-query-generator": create_multi_query_generator_agent,
    "research-scope-controller": create_research_scope_controller_agent,
    "search-result-ranker": create_search_result_ranker_agent,
    "primary-source-hunter": create_primary_source_hunter_agent,
    "citation-auditor": create_citation_auditor_agent,
    "contradiction-detector": create_contradiction_detector_agent,
    "bias-detector": create_bias_detector_agent,
    "evidence-quality-judge": create_evidence_quality_judge_agent,
    "timeline-researcher": create_timeline_researcher_agent,
    "entity-researcher": create_entity_researcher_agent,
    "company-intelligence-agent": create_company_intelligence_agent,
    "startup-researcher": create_startup_researcher_agent,
    "public-osint-researcher": create_public_osint_researcher_agent,
    "documentation-reader": create_documentation_reader_agent,
    "api-documentation-researcher": create_api_documentation_researcher_agent,
    "release-notes-agent": create_release_notes_agent,
    "benchmark-researcher": create_benchmark_researcher_agent,
    "dataset-researcher": create_dataset_researcher_agent,
    "standards-researcher": create_standards_researcher_agent,
    "paper-comparison-agent": create_paper_comparison_agent,
    "methodology-reviewer": create_methodology_reviewer_agent,
    "patent-researcher": create_patent_researcher_agent,
    "regulation-researcher": create_regulation_researcher_agent,
    "price-monitor-researcher": create_price_monitor_researcher_agent,
    "availability-checker": create_availability_checker_agent,
    "internet-evidence-judge": create_internet_evidence_judge_agent,
}


# ═══════════════════════════════════════════════════════════════════════════
# 5. DYNAMIC SPECIALIST FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def create_adk_specialist(meta: AgentMetadata) -> LlmAgent:
    """Convert an AgentMetadata object into a Google ADK LlmAgent.
    Uses handcrafted specialist factories for rich domain behaviors when available;
    otherwise generates a high-quality dynamic specialist.
    """
    adk_name = safe_adk_name(meta.id)
    register_adk_name_mapping(meta.id, adk_name)

    if meta.id in SPECIALIST_FACTORIES:
        return SPECIALIST_FACTORIES[meta.id](meta)

    tools = resolve_adk_tools(meta)
    instruction = build_specialist_instruction(meta)

    return LlmAgent(
        name=adk_name,
        model=MODEL,
        description=meta.description,
        instruction=instruction,
        tools=tools or [],
    )


def build_all_adk_specialists() -> dict[str, LlmAgent]:
    """Dynamically build all enabled ADK specialist agents from AgentRegistry.
    AgentRegistry is the single source of truth.
    """
    AgentRegistry.initialize()

    all_metadata = AgentRegistry.get_all_metadata()
    specialists: dict[str, LlmAgent] = {}

    for meta in all_metadata:
        if not meta.enabled:
            continue
        agent = create_adk_specialist(meta)
        specialists[meta.id] = agent

    registry_enabled_count = len([m for m in all_metadata if m.enabled])
    adk_specialist_count = len(specialists)

    if adk_specialist_count < 100:
        raise ValueError(
            f"Expected >= 100 ADK specialist agents, but only {adk_specialist_count} were created."
        )

    if adk_specialist_count != registry_enabled_count:
        logger.warning(
            f"ADK specialist count ({adk_specialist_count}) differs from enabled registry count ({registry_enabled_count})"
        )

    logger.info(
        f"Built {adk_specialist_count} Google ADK specialist agents from AgentRegistry."
    )
    return specialists


# ═══════════════════════════════════════════════════════════════════════════
# 6. DEPARTMENT MANAGERS (10 MANAGERS FOR 10 DEPARTMENTS)
# ═══════════════════════════════════════════════════════════════════════════

DEPARTMENT_MANAGER_CONFIG: dict[AgentDepartment, dict[str, str]] = {
    AgentDepartment.COMMAND_PLANNING: {
        "name": "command_planning_manager",
        "description": "Coordinates high-level strategy, task decomposition, dependency planning, knowledge retrieval, and workflow orchestration.",
        "focus": "Strategic planning, milestone sequencing, prompt optimization, knowledge recall, and orchestration.",
    },
    AgentDepartment.CODING: {
        "name": "coding_manager",
        "description": "Oversees frontend, backend, fullstack, database, devops, mobile, security, and hardware engineering specialists.",
        "focus": "Code generation, system architecture, database design, debugging, security auditing, and refactoring.",
    },
    AgentDepartment.RESEARCH: {
        "name": "research_manager",
        "description": "Directs academic, market, technical, medical, scientific, competitive, and deep web research specialists.",
        "focus": "Internet search, source verification, medical/pharmacy sciences, literature review, and comprehensive report synthesis.",
    },
    AgentDepartment.CONTENT: {
        "name": "content_manager",
        "description": "Leads technical writing, copywriting, educational notes, quiz formulation, study guides, music, culinary, and fitness content specialists.",
        "focus": "Educational notes, exam generation, blog/article writing, formatting, flashcards, and creative guides.",
    },
    AgentDepartment.VISUAL: {
        "name": "visual_manager",
        "description": "Manages UI/UX design, brand design, art theory, visual critique, chart styling, and visual asset generation.",
        "focus": "UI layouts, design systems, art critique, color palettes, visual hierarchy, and diagram design.",
    },
    AgentDepartment.DATA: {
        "name": "data_manager",
        "description": "Orchestrates data analysis, spreadsheet modeling, SQL queries, statistical forecasting, and report generation.",
        "focus": "Data cleaning, statistical calculations, trend forecasting, tabular modeling, and data verification.",
    },
    AgentDepartment.PRODUCT: {
        "name": "product_department_manager",
        "description": "Guides product management, user research, competitor teardowns, feature prioritization, pricing, and growth strategy.",
        "focus": "User journey mapping, market fit, product critique, pricing models, and feature specifications.",
    },
    AgentDepartment.AI_ML: {
        "name": "ai_ml_manager",
        "description": "Leads AI research, ML engineering, deep learning, prompt engineering, RAG architecture, model evaluation, and AI safety.",
        "focus": "Machine learning architectures, RAG pipelines, fine-tuning strategies, prompt optimization, and AI governance.",
    },
    AgentDepartment.AUTOMATION: {
        "name": "automation_manager",
        "description": "Coordinates browser automation, scraping, external API integration, Google Drive, Calendar, Contacts, and scheduling.",
        "focus": "Workflow automation, API execution, cloud drive file operations, calendar scheduling, and web scraping.",
    },
    AgentDepartment.BUSINESS_QUALITY: {
        "name": "business_quality_manager",
        "description": "Governs business analysis, finance, accounting (CA), economics, quality control, risk audit, and red-team review.",
        "focus": "Financial modeling, CA accounting, macroeconomic analysis, quality assurance, risk evaluation, and executive review.",
    },
}


def create_department_manager(
    department: AgentDepartment,
    specialists: list[LlmAgent],
) -> LlmAgent:
    """Create a Department Manager LlmAgent that coordinates all specialist workers
    in its department.
    """
    config = DEPARTMENT_MANAGER_CONFIG.get(
        department,
        {
            "name": f"{safe_adk_name(department.value)}_manager",
            "description": f"Manages {department.value} specialists.",
            "focus": f"Coordinates tasks within {department.value}.",
        },
    )

    # For the Research Department, isolate the Internet Intelligence division under InternetIntelligenceManager
    if department == AgentDepartment.RESEARCH:
        internet_specialists = [
            s for s in specialists if s.name in INTERNET_INTELLIGENCE_SPECIALIST_NAMES
        ]
        other_specialists = [
            s for s in specialists if s.name not in INTERNET_INTELLIGENCE_SPECIALIST_NAMES
        ]
        if internet_specialists:
            intel_manager = create_internet_intelligence_manager(internet_specialists)
            managed_sub_agents = [intel_manager] + other_specialists
        else:
            managed_sub_agents = specialists
    else:
        managed_sub_agents = specialists

    specialist_summaries = []
    for sp in managed_sub_agents:
        desc = getattr(sp, "description", "") or "Domain specialist"
        specialist_summaries.append(f"- **{sp.name}**: {desc}")

    specialists_roster = "\n".join(specialist_summaries)

    instruction = (
        f"You are the {config['name']} — executive manager of the '{department.value}' department.\n\n"
        f"Department Focus: {config['focus']}\n\n"
        f"Available Sub-Agents & Specialists in your department ({len(managed_sub_agents)} members):\n"
        f"{specialists_roster}\n\n"
        "Manager Responsibilities:\n"
        "1. Analyze incoming departmental tasks delegated by BossAgent.\n"
        "2. For live internet research, Google Search grounding, docs, and fact-checking, delegate to internet_intelligence_manager.\n"
        "3. For specialized medical, pharmacology, video, and domain research, delegate to the dedicated research specialist.\n"
        "4. Summarize and synthesize the specialist findings hierarchically.\n"
        "5. Return a structured department report upward to BossAgent containing:\n"
        "   - **Department**: The department name\n"
        "   - **Specialists Consulted**: List of specialist names used\n"
        "   - **Key Findings & Outputs**: High-yield factual results and technical solutions\n"
        "   - **Confidence & Recommendations**: Verification score and next steps\n\n"
        "Never leak internal raw chatter; always provide clean, authoritative synthesis."
    )

    return LlmAgent(
        name=config["name"],
        model=MODEL,
        instruction=instruction,
        sub_agents=managed_sub_agents,
        description=config["description"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# 7. ROOT BOSS AGENT
# ═══════════════════════════════════════════════════════════════════════════

BOSS_INSTRUCTION = (
    "You are BossAgent — the Chief Multi-Agent Executive Coordinator of this platform.\n\n"
    "CREATOR ATTRIBUTION:\n"
    "This website, application, and AI platform were created, built, and designed by Shreeharsh. "
    "If the user asks who created, built, developed, or designed this app or website, state clearly and professionally: "
    "'This website and application were created and developed by **Shreeharsh**.'\n\n"
    "CURRENCY & PRICING RULE:\n"
    "All product prices, deals, and costs MUST be stated in Indian Rupees (INR / ₹) by default. Convert USD prices to INR (1 USD = 86.5 INR).\n\n"
    "CLICKABLE LINKS RULE:\n"
    "ALWAYS render every product, documentation, API, service, and website as an active clickable Markdown link [Name](url). "
    "Never output raw plain text URLs without hyperlinking them.\n\n"
    "HIERARCHICAL MULTI-AGENT ORCHESTRATION:\n"
    "You lead 10 specialized Department Managers who oversee 170+ specialist agents and a dedicated Internet Intelligence Division:\n"
    "1. **command_planning_manager**: Strategy, task decomposition, knowledge RAG, memory, planning.\n"
    "2. **coding_manager**: Frontend, backend, databases, systems engineering, cybersecurity, architecture.\n"
    "3. **research_manager**: Directs internet_intelligence_manager (46 Internet Intelligence specialists) + scraping, medical, scientific, and news research.\n"
    "4. **content_manager**: Study notes, quiz generation, technical writing, culinary, music, fitness.\n"
    "5. **visual_manager**: UI/UX design, visual critique, brand identity, art theory.\n"
    "6. **data_manager**: Tabular analytics, statistics, SQL querying, trend forecasting.\n"
    "7. **product_department_manager**: Product requirements, user research, competitor teardown, pricing.\n"
    "8. **ai_ml_manager**: ML models, RAG pipelines, fine-tuning, prompt engineering, AI safety.\n"
    "9. **automation_manager**: Web scraping, browser automation, Google Drive, Calendar, Contacts, APIs.\n"
    "10. **business_quality_manager**: Corporate finance, CA accounting, economics, risk audit, QA.\n\n"
    "Execution Workflow:\n"
    "- Understand the user's intent and identify all required departments.\n"
    "- For multi-disciplinary requests (e.g. research + code + market analysis), delegate across the relevant department managers.\n"
    "- Synthesize all department reports into a cohesive, beautifully structured final response for the user.\n"
    "- Always answer helpfully, accurately, and in the user's requested language."
)


def create_boss_agent() -> LlmAgent:
    """Create the full hierarchical Google ADK multi-agent tree:
    Root (BossAgent) -> 10 Department Managers -> Internet Intelligence Manager -> 170+ Specialist Leaf Agents.
    """
    global _cached_boss_agent, _cached_hierarchy_info

    # 1. Build all specialists
    all_specialists = build_all_adk_specialists()

    # 2. Group specialists by department
    department_specialists_map: dict[AgentDepartment, list[LlmAgent]] = {
        dept: [] for dept in AgentDepartment
    }

    all_metadata = AgentRegistry.get_all_metadata()
    for meta in all_metadata:
        if not meta.enabled or meta.id not in all_specialists:
            continue
        agent_node = all_specialists[meta.id]
        dept = meta.department
        if dept in department_specialists_map:
            department_specialists_map[dept].append(agent_node)
        else:
            department_specialists_map[AgentDepartment.COMMAND_PLANNING].append(agent_node)

    # 3. Create the 10 Department Managers
    department_managers: list[LlmAgent] = []
    department_counts: dict[str, int] = {}

    for dept in AgentDepartment:
        specialists = department_specialists_map.get(dept, [])
        manager = create_department_manager(dept, specialists)
        department_managers.append(manager)
        department_counts[dept.value] = len(specialists)

    # 4. Create the Root BossAgent
    boss = LlmAgent(
        name="boss_agent",
        model=MODEL,
        instruction=BOSS_INSTRUCTION,
        sub_agents=department_managers,
        description="Central Chief Multi-Agent Orchestrator leading 10 department managers and 170+ specialist agents.",
    )

    # Cache hierarchy summary
    total_specialists = len(all_specialists)
    internet_intel_count = len([s for s in all_specialists.values() if s.name in INTERNET_INTELLIGENCE_SPECIALIST_NAMES])
    total_division_managers = 1 if internet_intel_count > 0 else 0
    total_department_managers = len(department_managers)
    total_roots = 1
    total_nodes = total_specialists + total_division_managers + total_department_managers + total_roots

    _cached_hierarchy_info = {
        "enabled": True,
        "provider": "gemini",
        "model": MODEL,
        "registry_agents": len(all_metadata),
        "adk_specialists": total_specialists,
        "internet_intelligence_agents": internet_intel_count,
        "google_search_agents": internet_intel_count,
        "department_managers": total_department_managers,
        "division_managers": total_division_managers,
        "root_agents": total_roots,
        "total_adk_nodes": total_nodes,
        "root_agent": "boss_agent",
        "architecture": "hierarchical",
        "departments": department_counts,
    }

    logger.info(
        f"ADK hierarchy initialized:\n"
        f"  Registry specialists: {len(all_metadata)}\n"
        f"  ADK leaf specialists: {total_specialists}\n"
        f"  Internet Intelligence division specialists: {internet_intel_count}\n"
        f"  Division managers: {total_division_managers}\n"
        f"  Department managers: {total_department_managers}\n"
        f"  Root agents: {total_roots}\n"
        f"  Total ADK nodes: {total_nodes}\n"
        f"  Departments breakdown: {department_counts}"
    )

    _cached_boss_agent = boss
    return boss


_cached_boss_agent: Optional[LlmAgent] = None
_cached_hierarchy_info: Optional[dict] = None


def get_boss_agent() -> LlmAgent:
    """Return cached BossAgent singleton, building the hierarchy lazily once."""
    global _cached_boss_agent
    if _cached_boss_agent is None:
        _cached_boss_agent = create_boss_agent()
    return _cached_boss_agent


def get_orchestrator() -> LlmAgent:
    """Alias for get_boss_agent."""
    return get_boss_agent()


def reset_adk_agent_tree() -> None:
    """Clear cached ADK agent tree for tests or hot-reload."""
    global _cached_boss_agent, _cached_hierarchy_info
    _cached_boss_agent = None
    _cached_hierarchy_info = None
    logger.info("ADK agent tree cache reset.")


def get_adk_hierarchy_summary() -> dict:
    """Return telemetry and node counts for the active ADK hierarchy."""
    global _cached_hierarchy_info
    if _cached_hierarchy_info is None:
        get_boss_agent()
    return dict(_cached_hierarchy_info or {})
