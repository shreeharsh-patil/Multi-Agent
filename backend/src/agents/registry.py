from typing import Optional, Any
from src.agents.base import BaseAgent, AgentManifest
from src.agents.metadata import AgentDepartment, AgentMetadata
from src.utils.logger import logger


class AgentRegistry:
    _agents: dict[str, BaseAgent] = {}
    _metadata: dict[str, AgentMetadata] = {}
    _initialized = False

    @classmethod
    def register(cls, agent: BaseAgent, metadata: Optional[AgentMetadata] = None) -> None:
        agent_id = agent.manifest.id
        cls._agents[agent_id] = agent
        if metadata:
            cls._metadata[agent_id] = metadata
        else:
            # Fallback metadata generation if registering legacy or custom agent
            cls._metadata[agent_id] = AgentMetadata(
                id=agent_id,
                name=agent.manifest.name,
                department=AgentDepartment.COMMAND_PLANNING,
                description=agent.manifest.description,
                capabilities=getattr(agent.manifest, "capabilities", []),
                icon=getattr(agent.manifest, "icon", "Bot"),
            )
        logger.info(f"Registered agent: {agent_id} ({agent.manifest.name})")

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        return cls._agents.get(agent_id)

    @classmethod
    def get_metadata(cls, agent_id: str) -> Optional[AgentMetadata]:
        return cls._metadata.get(agent_id)

    @classmethod
    def get_all_manifests(cls) -> list[AgentManifest]:
        return [a.manifest for a in cls._agents.values()]

    @classmethod
    def get_all_agents(cls) -> list[BaseAgent]:
        return list(cls._agents.values())

    @classmethod
    def get_all_metadata(cls) -> list[AgentMetadata]:
        return list(cls._metadata.values())

    @classmethod
    def get_by_department(cls, department: AgentDepartment | str) -> list[BaseAgent]:
        dept_val = department.value if isinstance(department, AgentDepartment) else str(department)
        return [
            a for aid, a in cls._agents.items()
            if aid in cls._metadata and cls._metadata[aid].department.value == dept_val
        ]

    @classmethod
    def get_by_capability(cls, capability: str) -> list[BaseAgent]:
        cap_clean = capability.casefold().strip()
        matching = []
        for aid, a in cls._agents.items():
            meta = cls._metadata.get(aid)
            if meta:
                meta_caps = getattr(meta, "capabilities", [])
                if any(cap_clean in str(c).casefold() or str(c).casefold() in cap_clean for c in meta_caps):
                    matching.append(a)
        return matching

    @classmethod
    def search(cls, query: str) -> list[dict[str, Any]]:
        q = query.casefold().strip()
        results = []
        for aid, meta in cls._metadata.items():
            if (
                q in meta.id.casefold()
                or q in meta.name.casefold()
                or q in meta.description.casefold()
                or q in meta.department.value.casefold()
                or any(q in c.casefold() for c in meta.capabilities)
            ):
                results.append({
                    "id": meta.id,
                    "name": meta.name,
                    "department": meta.department.value,
                    "description": meta.description,
                    "capabilities": meta.capabilities,
                    "responsibilities": meta.responsibilities,
                    "required_tools": meta.required_tools,
                    "optional_tools": meta.optional_tools,
                    "priority": meta.priority,
                    "icon": meta.icon,
                })
        return results

    @classmethod
    def initialize(cls, force: bool = False) -> None:
        if cls._initialized and not force:
            return
        if force:
            cls._agents.clear()
            cls._metadata.clear()
            import importlib
            import src.agents.catalog
            importlib.reload(src.agents.catalog)
        cls._initialized = True

        from src.agents.catalog import AGENT_CATALOG_DATA, GenericSpecialistAgent

        # Rich metadata definitions for domain agents
        domain_metadata_specs = {
            "knowledge": AgentMetadata(
                id="knowledge",
                name="Knowledge Agent",
                department=AgentDepartment.COMMAND_PLANNING,
                description="RAG-based document search, summaries, citations, knowledge graph, and retrieval.",
                capabilities=["rag", "document_search", "citations", "summaries", "knowledge_graph"],
                responsibilities=["Query internal document vectors", "Provide factual citations", "Summarize knowledge base"],
                specialized_instruction="You are the Knowledge Agent. Answer questions using retrieved documents from the knowledge base with exact citations.",
                domain_quality_criteria=["Source Citation Accuracy", "Fact Verification", "Context Grounding"],
                required_tools=["knowledge_search"],
                icon="BookOpen",
            ),
            "planner": AgentMetadata(
                id="planner",
                name="Planner Agent",
                department=AgentDepartment.COMMAND_PLANNING,
                description="Study planning, task management, scheduling, milestones, and deadline tracking.",
                capabilities=["study_schedules", "task_breakdown", "milestone_tracking", "prioritization"],
                responsibilities=["Create structured schedules", "Break large objectives into milestones", "Prioritize tasks"],
                specialized_instruction="You are the Planner Agent. Help users organize schedules, study plans, and deadline tracking.",
                domain_quality_criteria=["Feasibility", "Granularity", "Clear Milestones"],
                icon="Calendar",
            ),
            "memory": AgentMetadata(
                id="memory",
                name="Memory Agent",
                department=AgentDepartment.COMMAND_PLANNING,
                description="Manages long-term user memory, preferences, context recall, and personalization.",
                capabilities=["memory_store", "memory_search", "preference_tracking"],
                responsibilities=["Store durable user facts", "Recall preferences", "Maintain conversational context"],
                specialized_instruction="You are the Memory Agent. You manage long-term user preferences and conversational memory.",
                domain_quality_criteria=["Recall Relevance", "Privacy Guardrails", "Context Grounding"],
                required_tools=["memory_store", "memory_search"],
                icon="Brain",
            ),
            "tasks": AgentMetadata(
                id="tasks",
                name="Tasks Agent",
                department=AgentDepartment.COMMAND_PLANNING,
                description="Coordinates task queues, subtask assignment, dependencies, and execution progress.",
                capabilities=["task_queuing", "dependency_resolution", "status_tracking"],
                responsibilities=["Manage task lifecycle", "Resolve dependencies", "Report execution status"],
                specialized_instruction="You are the Tasks Agent. Manage task workflows, dependencies, and queue status.",
                domain_quality_criteria=["Dependency Correctness", "Status Clarity", "Execution Efficiency"],
                icon="ListTodo",
            ),
            "coding": AgentMetadata(
                id="coding",
                name="Coding Agent",
                department=AgentDepartment.CODING,
                description="Writes code, explains programming concepts, debugs issues, and generates documentation.",
                capabilities=["code_generation", "debugging", "refactoring", "code_review", "html_preview"],
                responsibilities=["Write production-ready code", "Debug complex runtime issues", "Document architectural patterns"],
                specialized_instruction="You are the Coding Agent. Write clean, well-tested code and explain technical concepts.",
                domain_quality_criteria=["Syntax Correctness", "Security Best Practices", "Clean Architecture"],
                icon="FileCode",
            ),
            "engineer": AgentMetadata(
                id="engineer",
                name="Engineer Agent",
                department=AgentDepartment.CODING,
                description="Systems design, software architecture, circuits, and engineering expertise.",
                capabilities=["systems_engineering", "hardware_design", "software_architecture", "circuits"],
                responsibilities=["Explain engineering first-principles", "Design system architectures", "Analyze circuits"],
                specialized_instruction="You are the Engineer Agent. Teach systems engineering, architecture, and hardware principles.",
                domain_quality_criteria=["First-Principles Rigor", "Formulas & Worked Examples", "Tradeoff Analysis"],
                required_tools=["web_search"],
                icon="Cpu",
            ),
            "architect": AgentMetadata(
                id="architect",
                name="Architect Agent",
                department=AgentDepartment.CODING,
                description="Architecture study tutor: design, construction, structures, and building systems.",
                capabilities=["architectural_design", "building_construction", "structural_analysis", "environmental_systems"],
                responsibilities=["Guide architectural concepts", "Detail structural construction", "Analyze building materials"],
                specialized_instruction="You are the Architect Agent. Cover architectural design, construction techniques, and structures.",
                domain_quality_criteria=["Structural Feasibility", "Material Precision", "Spatial Clarity"],
                required_tools=["web_search"],
                icon="Building2",
            ),
            "hacker": AgentMetadata(
                id="hacker",
                name="Cyber & Security Agent",
                department=AgentDepartment.CODING,
                description="Cybersecurity, networking, ethical hacking, and defense methodology.",
                capabilities=["cybersecurity", "vulnerability_assessment", "owasp", "network_security", "secure_coding"],
                responsibilities=["Assess security posture", "Explain cryptographic mechanisms", "Guide defensive remediation"],
                specialized_instruction="You are the Cyber & Security Agent. Teach cybersecurity, secure coding, and defense mechanisms.",
                domain_quality_criteria=["Defensive Focus", "Technical Depth", "Safe Educational Context"],
                required_tools=["web_search"],
                icon="ShieldAlert",
            ),
            "research": AgentMetadata(
                id="research",
                name="Research Agent",
                department=AgentDepartment.RESEARCH,
                description="Conducts internet research, compares sources, and generates reports.",
                capabilities=["web_search", "scrape_page", "source_synthesis", "comparative_analysis"],
                responsibilities=["Conduct deep web searches", "Extract and verify web sources", "Synthesize findings"],
                specialized_instruction="You are the Research Agent. Conduct thorough internet research and produce structured reports.",
                domain_quality_criteria=["Source Diversity", "Fact Verification", "Objective Synthesis"],
                required_tools=["web_search", "scrape_page"],
                icon="Search",
            ),
            "weather_news": AgentMetadata(
                id="weather_news",
                name="Weather & News Agent",
                department=AgentDepartment.RESEARCH,
                description="Real-time weather forecasts and live news headlines from global sources.",
                capabilities=["real_time_weather", "forecast", "live_news", "category_news"],
                responsibilities=["Fetch live meteorological data", "Summarize verified breaking news", "Track regional weather"],
                specialized_instruction="You are the Weather & News Agent. Fetch real-time weather and current news headlines.",
                domain_quality_criteria=["Timeliness", "Source Reliability", "Geographic Accuracy"],
                required_tools=["web_search"],
                icon="CloudSun",
            ),
            "youtube": AgentMetadata(
                id="youtube",
                name="YouTube Agent",
                department=AgentDepartment.RESEARCH,
                description="Analyzes YouTube videos, extracts transcripts, and summarizes video content.",
                capabilities=["video_summarization", "transcript_analysis", "chapter_extraction"],
                responsibilities=["Extract video transcripts", "Synthesize video chapters", "Highlight actionable takeaways"],
                specialized_instruction="You are the YouTube Agent. Summarize video content and extract key insights.",
                domain_quality_criteria=["Key Point Extraction", "Timestamp Integrity", "Conciseness"],
                required_tools=["web_search"],
                icon="Video",
            ),
            "doctor": AgentMetadata(
                id="doctor",
                name="Doctor Agent",
                department=AgentDepartment.RESEARCH,
                description="Medical study tutor: explains anatomy, physiology, pathology, and clinical reasoning.",
                capabilities=["anatomy", "physiology", "pathology", "clinical_reasoning", "medical_education"],
                responsibilities=["Explain physiological mechanisms", "Detail pathological processes", "Teach clinical reasoning"],
                specialized_instruction="You are the Doctor Agent. Teach pre-clinical and clinical medical concepts educationally.",
                domain_quality_criteria=["Medical Accuracy", "Educational Scope Notice", "Evidence-Based Guidance"],
                required_tools=["web_search"],
                icon="Stethoscope",
            ),
            "pharmacologist": AgentMetadata(
                id="pharmacologist",
                name="Pharmacologist Agent",
                department=AgentDepartment.RESEARCH,
                description="Pharmacy and pharmacology tutor: drug classes, mechanism of action, and interactions.",
                capabilities=["pharmacology", "drug_mechanisms", "pharmacokinetics", "drug_interactions"],
                responsibilities=["Detail drug mechanisms of action", "Explain pharmacokinetic parameters", "Highlight contraindications"],
                specialized_instruction="You are the Pharmacologist Agent. Teach pharmacology, drug classes, and interactions.",
                domain_quality_criteria=["Molecular Accuracy", "Safety & Contraindication Rigor", "Clinical Relevance"],
                required_tools=["web_search"],
                icon="Pill",
            ),
            "notes": AgentMetadata(
                id="notes",
                name="Notes Agent",
                department=AgentDepartment.CONTENT,
                description="Creates structured notes, summaries, flashcards, and revision materials.",
                capabilities=["structured_notes", "bullet_summaries", "flashcards", "revision_guides"],
                responsibilities=["Generate clean study notes", "Format revision summaries", "Produce flashcards"],
                specialized_instruction="You are the Notes Agent. Create structured, clear notes and revision materials.",
                domain_quality_criteria=["Hierarchy & Structure", "Conciseness", "High-Yield Summary"],
                icon="StickyNote",
            ),
            "quiz": AgentMetadata(
                id="quiz",
                name="Quiz Agent",
                department=AgentDepartment.CONTENT,
                description="Generates MCQs, exams, and practice questions with answer keys and explanations.",
                capabilities=["mcq_generation", "practice_exams", "rubric_creation", "answer_keys"],
                responsibilities=["Generate high-yield MCQs", "Formulate challenging distractors", "Provide detailed answer explanations"],
                specialized_instruction="You are the Quiz Agent. Generate practice questions and exams with answer keys.",
                domain_quality_criteria=["Question Clarity", "Plausible Distractors", "Explanatory Depth"],
                icon="GraduationCap",
            ),
            "cooking": AgentMetadata(
                id="cooking",
                name="Chef Agent",
                department=AgentDepartment.CONTENT,
                description="Cooking and culinary study tutor: techniques, recipes, gastronomy, and food science.",
                capabilities=["culinary_science", "recipe_formulation", "food_safety", "gastronomy"],
                responsibilities=["Explain culinary techniques", "Provide exact ingredient measurements", "Detail food safety (HACCP)"],
                specialized_instruction="You are the Chef Agent. Teach culinary arts, recipe formulation, and food science.",
                domain_quality_criteria=["Measurement Precision", "Technique Detail", "Food Safety (HACCP)"],
                required_tools=["web_search"],
                icon="Utensils",
            ),
            "music": AgentMetadata(
                id="music",
                name="Music Agent",
                department=AgentDepartment.CONTENT,
                description="Music theory, scales, intervals, melody, harmony, and composition analysis.",
                capabilities=["music_theory", "harmonic_analysis", "composition", "ear_training"],
                responsibilities=["Analyze chord progressions", "Explain scale and interval theory", "Guide composition techniques"],
                specialized_instruction="You are the Music Agent. Teach music theory, composition, and harmonic analysis.",
                domain_quality_criteria=["Theoretical Precision", "Clear Chord/Interval Naming", "Structural Analysis"],
                required_tools=["web_search"],
                icon="Music",
            ),
            "fitness": AgentMetadata(
                id="fitness",
                name="Fitness & Health Agent",
                department=AgentDepartment.CONTENT,
                description="Fitness, exercise science, kinesiology, programming, and sports nutrition.",
                capabilities=["exercise_physiology", "workout_programming", "kinesiology", "sports_nutrition"],
                responsibilities=["Design periodized workout programs", "Explain muscle biomechanics", "Guide sports nutrition"],
                specialized_instruction="You are the Fitness & Health Agent. Teach exercise science, programming, and nutrition.",
                domain_quality_criteria=["Biomechanical Safety", "Program Periodization", "Nutritional Accuracy"],
                required_tools=["web_search"],
                icon="Dumbbell",
            ),
            "art": AgentMetadata(
                id="art",
                name="Art & Design Agent",
                department=AgentDepartment.VISUAL,
                description="Art history, techniques, drawing, color theory, composition, and visual critique.",
                capabilities=["art_history", "color_theory", "composition_analysis", "drawing_techniques"],
                responsibilities=["Explain visual art principles", "Analyze composition and color palettes", "Critique artwork"],
                specialized_instruction="You are the Art & Design Agent. Teach visual art, design theory, and art history.",
                domain_quality_criteria=["Visual Analysis Depth", "Historical Context", "Technical Terminology"],
                required_tools=["web_search"],
                icon="Palette",
            ),
            "data_analysis": AgentMetadata(
                id="data_analysis",
                name="Data Analysis Agent",
                department=AgentDepartment.DATA,
                description="Analyzes structured data, CSV/Excel files, statistical distributions, and generates charts.",
                capabilities=["csv_analysis", "statistical_summary", "trend_detection", "chart_specification"],
                responsibilities=["Compute descriptive statistics", "Identify outliers and correlations", "Format chart data"],
                specialized_instruction="You are the Data Analysis Agent. Analyze datasets and provide statistical findings.",
                domain_quality_criteria=["Numerical Accuracy", "Statistical Validity", "Insight Depth"],
                icon="BarChart2",
            ),
            "drive": AgentMetadata(
                id="drive",
                name="Drive Agent",
                department=AgentDepartment.AUTOMATION,
                description="Manages Google Drive files: listing, reading file content, summarizing documents, uploading, and deleting.",
                capabilities=["drive_list", "drive_read", "drive_upload", "drive_delete"],
                responsibilities=["List user Drive files", "Read document content", "Upload generated study files"],
                specialized_instruction="You are the Drive Agent. Inspect and manage Google Drive files for the user.",
                domain_quality_criteria=["File Safety", "Accurate Extraction", "Data Integrity"],
                required_tools=["drive_list", "drive_read", "drive_upload", "drive_delete"],
                icon="HardDrive",
            ),
            "calendar": AgentMetadata(
                id="calendar",
                name="Calendar Agent",
                department=AgentDepartment.AUTOMATION,
                description="Lists, creates, reschedules, and manages Google Calendar events and meetings.",
                capabilities=["calendar_list", "calendar_create", "event_scheduling"],
                responsibilities=["Fetch upcoming calendar events", "Create new events with timestamps", "Check availability"],
                specialized_instruction="You are the Calendar Agent. Manage calendar schedules and meetings.",
                domain_quality_criteria=["Timezone Accuracy", "Conflict Avoidance", "Complete Event Details"],
                required_tools=["calendar_list", "calendar_create"],
                icon="CalendarDays",
            ),
            "contacts": AgentMetadata(
                id="contacts",
                name="Contacts Agent",
                department=AgentDepartment.AUTOMATION,
                description="Lists and searches Google Contacts for email addresses and phone numbers.",
                capabilities=["contacts_list", "contact_search"],
                responsibilities=["Search address book", "Fetch email and phone records", "Format contact details"],
                specialized_instruction="You are the Contacts Agent. Search Google Contacts for emails and phone numbers.",
                domain_quality_criteria=["Privacy Compliance", "Accurate Contact Matching", "Exact Email Extraction"],
                required_tools=["contacts_list"],
                icon="Users",
            ),
            "gmail": AgentMetadata(
                id="gmail",
                name="Gmail Agent",
                department=AgentDepartment.AUTOMATION,
                description="Searches, reads, drafts, and sends emails via Gmail integration.",
                capabilities=["email_search", "email_drafting", "email_sending"],
                responsibilities=["Search user email threads", "Draft professional emails", "Manage message flow"],
                specialized_instruction="You are the Gmail Agent. Draft and search user emails.",
                domain_quality_criteria=["Tone Calibration", "Clarity", "Recipient Safety"],
                icon="Mail",
            ),
            "tool": AgentMetadata(
                id="tool",
                name="Tool Agent",
                department=AgentDepartment.AUTOMATION,
                description="Executes tools: calculator, web search, scraping, and external API integrations.",
                capabilities=["calculator", "web_search", "scrape_page", "api_execution"],
                responsibilities=["Perform exact mathematical calculations", "Execute web tools", "Scrape URLs"],
                specialized_instruction="You are the Tool Agent. Execute calculations, search tools, and web scrapers.",
                domain_quality_criteria=["Mathematical Precision", "API Validation", "Safe Execution"],
                required_tools=["calculator", "web_search", "scrape_page"],
                icon="Puzzle",
            ),
            "finance": AgentMetadata(
                id="finance",
                name="Finance Agent",
                department=AgentDepartment.BUSINESS_QUALITY,
                description="Financial statements, corporate valuation, capital markets, and investment analysis.",
                capabilities=["financial_modeling", "valuation", "capital_markets", "statement_analysis"],
                responsibilities=["Analyze financial statements", "Model discounted cash flows", "Evaluate market ratios"],
                specialized_instruction="You are the Finance Agent. Teach valuation, financial modeling, and markets.",
                domain_quality_criteria=["Formula Rigor", "Accounting Consistency", "Practical Application"],
                required_tools=["web_search"],
                icon="TrendingUp",
            ),
            "accountant": AgentMetadata(
                id="accountant",
                name="Accountant (CA) Agent",
                department=AgentDepartment.BUSINESS_QUALITY,
                description="Financial accounting, journal entries, auditing, taxation, GST, and CA standards.",
                capabilities=["financial_accounting", "journal_ledger", "taxation_gst", "auditing"],
                responsibilities=["Formulate journal and ledger entries", "Explain statutory tax rules", "Audit financial statements"],
                specialized_instruction="You are the Accountant (CA) Agent. Teach CA accounting, GST, and audit procedures.",
                domain_quality_criteria=["Double-Entry Precision", "Tax Compliance Accuracy", "Step-by-Step Working"],
                required_tools=["web_search"],
                icon="Calculator",
            ),
            "economics": AgentMetadata(
                id="economics",
                name="Economics Agent",
                department=AgentDepartment.BUSINESS_QUALITY,
                description="Microeconomics, macroeconomics, fiscal/monetary policy, and international trade.",
                capabilities=["microeconomics", "macroeconomics", "market_structures", "monetary_policy"],
                responsibilities=["Analyze supply and demand shifts", "Explain macroeconomic indicators", "Model trade effects"],
                specialized_instruction="You are the Economics Agent. Teach micro/macro economics and monetary policy.",
                domain_quality_criteria=["Theoretical Rigor", "Model Consistency", "Clear Mechanism Explanation"],
                required_tools=["web_search"],
                icon="PieChart",
            ),
        }

        # Register existing domain-specific agents with their rich metadata
        try:
            from src.agents.knowledge.agent import KnowledgeAgent
            from src.agents.drive.agent import DriveAgent
            from src.agents.notes.agent import NotesAgent
            from src.agents.quiz.agent import QuizAgent
            from src.agents.planner.agent import PlannerAgent
            from src.agents.research.agent import ResearchAgent
            from src.agents.coding.agent import CodingAgent
            from src.agents.memory.agent import MemoryAgent
            from src.agents.tool.agent import ToolAgent
            from src.agents.calendar.agent import CalendarAgent
            from src.agents.data_analysis.agent import DataAnalysisAgent
            from src.agents.weather_news.agent import WeatherNewsAgent
            from src.agents.gmail.agent import GmailAgent
            from src.agents.tasks.agent import TasksAgent
            from src.agents.youtube.agent import YouTubeAgent
            from src.agents.contacts.agent import ContactsAgent
            from src.agents.engineer.agent import EngineerAgent
            from src.agents.pharmacologist.agent import PharmacologistAgent
            from src.agents.doctor.agent import DoctorAgent
            from src.agents.finance.agent import FinanceAgent
            from src.agents.accountant.agent import AccountantAgent
            from src.agents.economics.agent import EconomicsAgent
            from src.agents.architect.agent import ArchitectAgent
            from src.agents.hacker.agent import HackerAgent
            from src.agents.cooking.agent import ChefAgent
            from src.agents.music.agent import MusicAgent
            from src.agents.fitness.agent import FitnessAgent
            from src.agents.art.agent import ArtAgent

            domain_agents = [
                KnowledgeAgent(), DriveAgent(), NotesAgent(), QuizAgent(), PlannerAgent(),
                ResearchAgent(), CodingAgent(), MemoryAgent(), ToolAgent(), CalendarAgent(),
                DataAnalysisAgent(), WeatherNewsAgent(), GmailAgent(), TasksAgent(), YouTubeAgent(),
                ContactsAgent(), EngineerAgent(), PharmacologistAgent(), DoctorAgent(), FinanceAgent(),
                AccountantAgent(), EconomicsAgent(), ArchitectAgent(), HackerAgent(), ChefAgent(),
                MusicAgent(), FitnessAgent(), ArtAgent()
            ]
            for da in domain_agents:
                aid = da.manifest.id
                meta = domain_metadata_specs.get(aid)
                cls.register(da, metadata=meta)
        except Exception as err:
            logger.warning(f"Domain agents initialization notice: {err}")

        # Register all specialized catalog agents
        for meta in AGENT_CATALOG_DATA:
            agent_instance = GenericSpecialistAgent(meta)
            cls.register(agent_instance, meta)

        logger.info(f"Agent registry initialized with {len(cls._agents)} agents")


# Auto-initialize on import for safety
AgentRegistry.initialize()
