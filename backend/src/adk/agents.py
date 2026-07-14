"""Google ADK agent definitions.

Each agent is an adk.agents.LlmAgent with:
- A specific instruction (system prompt)
- Relevant tools
- Sub-agents for delegation

The root OrchestratorAgent routes requests to specialized sub-agents
via TransferToAgentTool.
"""

from google.adk.agents import LlmAgent
from src.config import settings
from src.adk.tools import (
    knowledge_search_tool,
    memory_store_tool,
    memory_search_tool,
    calculator_tool,
    web_search_tool,
    scrape_page_tool,
    drive_list_tool,
    drive_upload_tool,
    drive_delete_tool,
)

MODEL = settings.gemini_model


def create_knowledge_agent() -> LlmAgent:
    return LlmAgent(
        name="knowledge",
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


def create_drive_agent() -> LlmAgent:
    return LlmAgent(
        name="drive",
        model=MODEL,
        instruction=(
            "You are the Drive Agent. You help users manage their Google Drive files. "
            "You have the following capabilities:\n"
            "1. drive_list - List files in the user's Google Drive\n"
            "2. drive_upload - Upload text content as a file to Drive\n"
            "3. drive_delete - Delete a file from Drive\n\n"
            "To list files: call drive_list with the user's email/ID.\n"
            "To upload: call drive_upload with the user's ID, file name, and content.\n"
            "To delete: call drive_delete with the user's ID and file ID.\n\n"
            "If the user hasn't connected their Google Drive, guide them to "
            "Settings > Google Drive to sign in and grant access."
        ),
        tools=[drive_list_tool, drive_upload_tool, drive_delete_tool],
        description="Manages Google Drive files, uploads, downloads, and folder organization.",
    )


def create_notes_agent() -> LlmAgent:
    return LlmAgent(
        name="notes",
        model=MODEL,
        instruction=(
            "You are the Notes Agent. Create structured, well-organized notes. "
            "Support formats: summaries, bullet points, flashcards (Q&A), and revision guides. "
            "Use clear headings and organize information logically. "
            "When the user asks for flashcards, generate question-answer pairs."
        ),
        description="Creates structured notes, summaries, flashcards, and revision materials.",
    )


def create_quiz_agent() -> LlmAgent:
    return LlmAgent(
        name="quiz",
        model=MODEL,
        instruction=(
            "You are the Quiz Agent. Generate high-quality quiz questions. "
            "Support formats: multiple choice, true/false, fill-in-the-blanks, short answer. "
            "Always include answer keys and explanations for each question. "
            "Adapt difficulty based on what the user requests (beginner, intermediate, advanced)."
        ),
        description="Generates MCQs, exams, and practice questions with answer keys.",
    )


def create_planner_agent() -> LlmAgent:
    return LlmAgent(
        name="planner",
        model=MODEL,
        instruction=(
            "You are the Planner Agent. Help users plan their schedules and manage tasks. "
            "Create structured plans with timelines, priorities, and milestones. "
            "Help with: study schedules, task lists, deadline tracking, and goal setting. "
            "Break large tasks into smaller manageable steps."
        ),
        description="Helps with study planning, task management, scheduling, and deadlines.",
    )


def create_research_agent() -> LlmAgent:
    return LlmAgent(
        name="research",
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


def create_coding_agent() -> LlmAgent:
    return LlmAgent(
        name="coding",
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


def create_memory_agent() -> LlmAgent:
    return LlmAgent(
        name="memory",
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


def create_tool_agent() -> LlmAgent:
    return LlmAgent(
        name="tool",
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


def create_orchestrator_agent() -> LlmAgent:
    """Create the root orchestrator agent with all sub-agents.

    The orchestrator uses TransferToAgentTool to route requests
    to the appropriate specialized agent based on the user's intent.
    """
    knowledge = create_knowledge_agent()
    drive = create_drive_agent()
    notes = create_notes_agent()
    quiz = create_quiz_agent()
    planner = create_planner_agent()
    research = create_research_agent()
    coding = create_coding_agent()
    memory = create_memory_agent()
    tool_agent = create_tool_agent()

    sub_agents = [
        knowledge,
        drive,
        notes,
        quiz,
        planner,
        research,
        coding,
        memory,
        tool_agent,
    ]

    return LlmAgent(
        name="orchestrator",
        model=MODEL,
        instruction=(
            "You are the Orchestrator Agent — the central coordinator. "
            "Your job is to understand what the user needs and transfer them "
            "to the most appropriate specialized agent.\n\n"

            "Available agents:\n"
            "- knowledge: RAG-based document search, summaries, citations\n"
            "- drive: Google Drive file management\n"
            "- notes: Note-taking, flashcards, revision notes\n"
            "- quiz: MCQ generation, practice exams\n"
            "- planner: Study planning, task management, schedules\n"
            "- research: Internet research, report generation\n"
            "- coding: Code writing, debugging, documentation\n"
            "- memory: Long-term memory, preferences, recall\n"
            "- tool: Calculator, web search, API tools\n\n"

            "Analyze the user's request and transfer to the best agent. "
            "If the request spans multiple domains, handle it step by step. "
            "Always respond in the user's language."
        ),
        sub_agents=sub_agents,
        description="Central orchestrator that routes requests to specialized agents.",
    )
