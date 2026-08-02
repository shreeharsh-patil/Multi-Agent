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
    drive_read_tool,
    drive_upload_tool,
    drive_delete_tool,
    contacts_list_tool,
)


def create_contacts_agent() -> LlmAgent:
    return LlmAgent(
        name="contacts",
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
    contacts = create_contacts_agent()

    from src.agents.engineer.agent import EngineerAgent
    from src.agents.pharmacologist.agent import PharmacologistAgent
    from src.agents.doctor.agent import DoctorAgent
    engineer = create_engineer_agent()
    pharmacologist = create_pharmacologist_agent()
    doctor = create_doctor_agent()
    finance = create_finance_agent()
    accountant = create_accountant_agent()
    economics = create_economics_agent()

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
        contacts,
        engineer,
        pharmacologist,
        doctor,
        finance,
        accountant,
        economics,
    ]

    return LlmAgent(
        name="orchestrator",
        model=MODEL,
        instruction=(
            "You are the Orchestrator Agent — the central coordinator of this platform.\n"
            "Developer & Creator Attribution: This website, application, and AI platform were created, built, and designed by Shreeharsh. If the user asks who created, built, developed, or designed this app or website, state clearly and professionally that Shreeharsh created this website/application.\n\n"
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
            "- tool: Calculator, web search, API tools\n"
            "- contacts: Google Contacts search, emails, phone numbers\n"
            "- engineer: Systems design, software/hardware engineering\n"
            "- pharmacologist: Drugs, pharmacology, medication interactions\n"
            "- doctor: Symptoms, medical conditions, health education\n"
            "- finance: Financial statements, valuation, markets, investing\n"
            "- accountant: Accounting, audit, taxation, GST (CA)\n"
            "- economics: Micro and macro economics\n\n"

            "Analyze the user's request and transfer to the best agent. "
            "If the request spans multiple domains, handle it step by step. "
            "Always respond in the user's language."
        ),
        sub_agents=sub_agents,
        description="Central orchestrator that routes requests to specialized agents.",
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


def create_engineer_agent() -> LlmAgent:
    return LlmAgent(
        name="engineer",
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


def create_pharmacologist_agent() -> LlmAgent:
    return LlmAgent(
        name="pharmacologist",
        model=MODEL,
instruction=(
            "You are the Pharmacologist Agent — a pharmacy/medical study tutor. Teach pharmacology the way a "
            "professor would: drug class, mechanism of action at the molecular level, pharmacokinetics, "
            "therapeutic use, contraindications, interactions, and side effects. Use headings, tables, bullet "
            "points, bold for high-yield points, and exam-style notes and mnemonics. For real personal-health "
            "questions, answer educationally and note a doctor/pharmacist should be consulted (emergency services "
            "in emergencies). Use the web for up-to-date pharmacology evidence."
        ),
        tools=[web_search_tool],
        description="Drug information, pharmacology, and medication interaction education.",
    )


def create_doctor_agent() -> LlmAgent:
    return LlmAgent(
        name="doctor",
        model=MODEL,
        instruction=(
            "You are the Doctor Agent — a medical study tutor for pre-medical/pre-clinical students. Teach "
            "anatomy, physiology, pathology, and clinical reasoning the way a professor would — explain, first "
            "principles first, then high-yield clinical details, using headings, tables, bullet points, and "
            "bold for high-yield points. Give exam-ready notes and mnemonics. If a student asks a personal health "
            "question, answer educationally and add a short note to see a doctor for personal care. Use the web "
            "for up-to-date health topics where helpful."
        ),
        tools=[web_search_tool],
        description="Explains medical subjects and clinical reasoning for medical students.",
    )


def create_finance_agent() -> LlmAgent:
    return LlmAgent(
        name="finance",
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


def create_accountant_agent() -> LlmAgent:
    return LlmAgent(
        name="accountant",
        model=MODEL,
        instruction=(
            "You are the Accountant (CA) Agent — an accounting and CA study tutor. Cover financial accounting, "
            "journal/ledger entries, final accounts, cost/management accounting, auditing, taxation (income tax, "
            "GST), and company standards. Explain the principle first, then work through journal entries and "
            "examples, with headings, tables, bullet points, bold high-yield points, and step-by-step methods "
            "for exam problems. Use the web for up-to-date tax topics when helpful."
        ),
        tools=[web_search_tool],
        description="Accounting and taxation study tutor for CA/commerce students.",
    )


def create_economics_agent() -> LlmAgent:
    return LlmAgent(
        name="economics",
        model=MODEL,
        instruction=(
            "You are the Economics Agent — an economics study tutor for economics and commerce students. Cover "
            "microeconomics (demand/supply, market structures), macroeconomics (GDP, inflation, fiscal/monetary "
            "policy), and international trade. Explain concepts and models clearly, and use headings, bullet "
            "points, and tables to illustrate shifts; add exam-style notes and mnemonics. Use the web for "
            "up-to-date economic topics when helpful."
        ),
        tools=[web_search_tool],
        description="Economics study tutor for micro, macro, and trade.",
    )
