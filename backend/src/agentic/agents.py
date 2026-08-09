"""The 100 specialized worker agents + the Executive Agent Registry.

Every agent is a real ``BaseAgent`` whose ``execute()`` performs an actual LLM
call (optionally grounded with authorized tool evidence). No agent result is
fabricated: the Boss selects a minimal team, and only the selected workers run.

Design goals
------------
* Meaningful names + stable slugs (``web-researcher``, ``backend-developer``).
* Capability metadata drives capability-based routing (see selector.py).
* Adding the 101st agent = append one ``AgentDef`` and re-initialize. The Boss
  requires zero changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.base import BaseAgent, AgentManifest, AgentResult, AgentTaskSpec
from src.utils.logger import logger


@dataclass
class AgentDef:
    slug: str
    name: str
    department: str
    description: str
    responsibilities: list
    capabilities: list
    role_prompt: str
    required_tools: list = field(default_factory=list)
    optional_tools: list = field(default_factory=list)
    priority: int = 50
    can_run_in_parallel: bool = True
    max_retries: int = 2
    model_tier: str = "balanced"
    icon: str = "Bot"
    cost_weight: float = 1.0
    avg_latency_ms: int = 1000


# ---------------------------------------------------------------------------
# RoleAgent — generic real executor materialized from an AgentDef
# ---------------------------------------------------------------------------

class RoleAgent(BaseAgent):
    """A worker whose execution is a genuine, task-scoped LLM call.

    It only uses tools that are both declared by its manifest AND granted by
    the Boss on the subtask whitelist (enforced in tools.run_authorized_tool).
    """

    def __init__(self, definition: AgentDef):
        self._def = definition
        self.manifest = self._create_manifest()
        self.definition = definition

    def _create_manifest(self) -> AgentManifest:
        d = self._def
        return AgentManifest(
            id=d.slug,
            name=d.name,
            description=d.description,
            icon=d.icon,
            capabilities=d.capabilities,
            department=d.department,
            responsibilities=d.responsibilities,
            required_tools=d.required_tools,
            optional_tools=d.optional_tools,
            priority=d.priority,
            can_run_in_parallel=d.can_run_in_parallel,
            max_retries=d.max_retries,
            model_tier=d.model_tier,
            cost_weight=d.cost_weight,
            avg_latency_ms=d.avg_latency_ms,
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        from src.services.llm import llm_service
        from src.agentic.tools import run_authorized_tool

        spec: AgentTaskSpec | None = context.get("spec")
        objective = spec.objective if spec else (user_input or "").strip()
        tool_ctx = {
            "user_id": context.get("user_id", "default"),
            "task_id": context.get("task_id", ""),
            "subtask": context.get("subtask", self.manifest.id),
            "objective": objective,
            "instruction": spec.instructions if spec else "",
        }

        # ----- Tool routing (authorized intersection) -----
        if spec is None:
            granted = context.get("available_tools", [])
        else:
            granted = spec.available_tools
        declared = self.manifest.required_tools + self.manifest.optional_tools
        authorized = [t for t in granted if t in declared]

        tool_evidence: list[str] = []
        tool_calls: list[dict] = []
        run_tools = context.get("use_tools", True)
        if run_tools:
            for slug in authorized:
                argument = objective
                if slug == "calculator":
                    argument = spec.instructions if spec else objective
                result = await run_authorized_tool(slug, tool_ctx, argument=argument, allowed=authorized)
                if result and "not authorized" not in result and "Tool unavailable" not in result:
                    tool_evidence.append(f"[{slug}]\n{result[:6000]}")
                    tool_calls.append({"name": slug, "result": result[:1200]})

        # ----- Craft the scoped prompt -----
        if spec is not None:
            base = spec.render()
        else:
            base = f"Objective: {objective}\nInstructions: {context.get('instructions', '') or ''}"
        if spec and spec.previous_results:
            base += "\n\nYou may build on prior specialist results that are relevant to your responsibility."
        if tool_evidence:
            base += "\n\nEVIDENCE FROM AUTHORIZED TOOLS:\n" + "\n\n".join(tool_evidence)

        output = await llm_service.generate(
            prompt=base,
            system_instruction=self._build_system_instruction(),
            temperature=0.4,
            max_output_tokens=self._token_budget(),
        )
        if not output or not output.strip():
            return AgentResult(success=False, output="", error="Agent returned an empty response", tool_calls=tool_calls)
        return AgentResult(success=True, output=output.strip(), tool_calls=tool_calls)

    def _build_system_instruction(self) -> str:
        d = self._def
        lines = [
            f"You are the {d.name} — a specialized {d.department} worker in a multi-agent orchestra coordinated by a Boss Agent.",
            d.role_prompt,
            "Deliver a concrete, well-structured result (Markdown). State assumptions, flag uncertainty, "
            "do not claim to have used tools you did not use, and never expose internal routing or chain-of-thought.",
        ]
        return "\n".join(lines)

    def _token_budget(self) -> int:
        tier = self.manifest.model_tier
        if tier == "cheap":
            return 1024
        if tier == "strong":
            return 4096
        return 2400


# ---------------------------------------------------------------------------
# The 100 specialized agents
# ---------------------------------------------------------------------------

_C = ("code_python", "code_javascript", "code_typescript", "frontend", "react",
      "backend", "api_design", "database_design", "debugging", "testing",
      "security", "deployment", "devops", "web_search", "research",
      "deep_research", "technical_research", "academic_research",
      "documentation_research", "competitive_research", "fact_checking",
      "source_evaluation", "information_extraction", "research_synthesis",
      "content_writing", "scriptwriting", "copywriting", "storywriting",
      "technical_writing", "seo_writing", "hooks", "editing", "grammar",
      "critique_writing", "visual_design", "image_prompting",
      "thumbnail_design", "composition", "lighting", "color_grading",
      "ui_design", "ux_design", "branding", "critique_visual", "data_analysis",
      "spreadsheets", "sql", "statistics", "chart_design", "data_cleaning",
      "forecasting", "reporting", "data_verification", "insight_synthesis",
      "product_strategy", "product_research", "feature_analysis",
      "user_research", "ux_research", "market_analysis", "competitor_analysis",
      "pricing", "growth", "critique_product", "ai_research", "ml",
      "deep_learning", "llm", "rag", "prompt_engineering", "model_evaluation",
      "model_selection", "ai_safety", "ai_optimization", "workflow_design",
      "automation", "browser_automation", "api_automation", "scraping",
      "file_management", "email_automation", "scheduling", "integrations",
      "automation_testing", "business_analysis", "market_research",
      "financial_analysis", "strategy", "risk_analysis", "policy_research",
      "quality_control", "verification", "red_team", "executive_review")


def _def(slug, name, dept, desc, caps, role, resp=None, tools=None, opt=None,
         priority=50, parallel=True, retries=2, tier="balanced", icon="Bot",
         cost=1.0, latency=1000) -> AgentDef:
    return AgentDef(
        slug=slug, name=name, department=dept, description=desc,
        responsibilities=resp or [role.split(".")[0]],
        capabilities=caps, role_prompt=role,
        required_tools=tools or [], optional_tools=opt or [],
        priority=priority, can_run_in_parallel=parallel, max_retries=retries,
        model_tier=tier, icon=icon, cost_weight=cost, avg_latency_ms=latency,
    )


def _build_agent_defs() -> list[AgentDef]:
    COMMAND = "Command & Planning"
    CODING = "Coding"
    RESEARCH = "Research"
    CONTENT = "Content"
    VISUAL = "Visual"
    DATA = "Data"
    PRODUCT = "Product"
    AI_ML = "AI/ML"
    AUTOMATION = "Automation"
    BUSINESS = "Business & Quality"

    agents: list[AgentDef] = []

    # ------------------------ 1. COMMAND & PLANNING ------------------------
    agents += [
        _def("supreme-commander", "Supreme Commander", COMMAND,
             "High-level strategic planning, task-group coordination, conflict resolution, overall execution strategy.",
             ["planning", "strategy", "executive_review"],
             "You coordinate major task groups, resolve high-level conflicts, and recommend the overall execution strategy. Only activated for complex tasks.",
             resp=["strategic planning", "coordination", "high-level conflict resolution"], priority=95, tier="strong"),
        _def("intent-detector", "Intent Detector", COMMAND,
             "Determines what the user actually wants: intent, task type, explicit + implicit requirements, constraints.",
             ["intent_analysis", "requirements"],
             "Analyze the request and produce a structured intent object: task type, explicit requirements, implicit requirements, and constraints. Be precise and conservative.",
             resp=["intent detection", "requirement discovery"], priority=90, tier="cheap"),
        _def("requirement-analyst", "Requirement Analyst", COMMAND,
             "Turns vague requests into concrete, testable requirements.",
             ["requirements", "intent_analysis"],
             "Extract functional requirements, technical requirements, constraints, missing requirements, and assumptions from the request.",
             resp=["requirements engineering"], priority=88, tier="balanced"),
        _def("master-planner", "Master Planner", COMMAND,
             "Creates the overall execution plan: tasks, dependencies, execution order, parallelizable buckets.",
             ["planning", "decomposition"],
             "Convert requirements into an ordered execution plan with clear dependencies and parallelizable buckets.",
             resp=["execution planning"], priority=85, tier="strong"),
        _def("department-router", "Department Router", COMMAND,
             "Determines which departments are relevant to a request.",
             ["routing", "planning"],
             "Map the request to the relevant departments (Coding, Research, Content, Visual, Data, Product, AI/ML, Automation, Business/Quality). Return only the relevant ones.",
             resp=["department selection"], priority=82, tier="cheap"),
        _def("specialist-router", "Specialist Router", COMMAND,
             "Chooses the best specialist agents per subtask: capability match, dependencies, minimal sufficient team.",
             ["routing", "planning"],
             "Match tasks to specialist capabilities, compare candidates, and select the smallest sufficient team.",
             resp=["agent selection"], priority=80, tier="balanced"),
        _def("task-decomposer", "Task Decomposer", COMMAND,
             "Breaks complex tasks into executable, ordered subtasks.",
             ["decomposition", "planning"],
             "Decompose the goal into granular executable subtasks with dependencies and parallelism annotations.",
             resp=["task decomposition"], priority=78, tier="strong"),
        _def("context-manager", "Context Manager", COMMAND,
             "Maintains relevant task context: requirements, previous results, task state.",
             ["context_management", "planning"],
             "Track user requirements and prior results, prune irrelevant context, and keep task state coherent.",
             resp=["context maintenance"], priority=85, tier="balanced"),
        _def("progress-controller", "Progress Controller", COMMAND,
             "Monitors pending/running/completed tasks and surfaces stalls and failures.",
             ["progress_tracking", "planning"],
             "Track pending, running, completed, and stalled tasks; notify coordination of failures.",
             resp=["progress monitoring"], priority=80, tier="cheap"),
        _def("final-synthesizer", "Final Synthesizer", COMMAND,
             "Produces the final structured result from all relevant outputs.",
             ["synthesis", "context_management"],
             "Merge results, remove duplication, resolve conflicts, maintain consistency, and produce the user-facing answer.",
             resp=["final synthesis"], priority=95, tier="strong"),
    ]

    # ------------------------------ 2. CODING ------------------------------
    agents += [
        _def("python-developer", "Python Developer", CODING,
             "Python implementation, architecture, libraries, optimization, debugging.",
             ["code_python", "debugging", "backend"],
             "Design and implement robust, idiomatic Python. Optimize and debug where needed.",
             tools=[], priority=70, icon="FileCode"),
        _def("javascript-developer", "JavaScript Developer", CODING,
             "JavaScript/TypeScript browser and Node.js logic.",
             ["code_javascript", "code_typescript", "backend", "frontend"],
             "Write clean JavaScript/TypeScript for browser and Node.js environments.",
             priority=70, icon="FileCode"),
        _def("frontend-developer", "Frontend Developer", CODING,
             "React/Next.js UI implementation, components, state, accessibility.",
             ["frontend", "react", "code_javascript", "code_typescript", "ui_design"],
             "Implement accessible, performant React/Next.js interfaces, components, and state management.",
             priority=75, icon="Layout"),
        _def("backend-developer", "Backend Developer", CODING,
             "Server architecture, APIs, authentication, business logic.",
             ["backend", "api_design", "security"],
             "Design and implement server architecture, APIs, authentication, and business logic.",
             priority=75, icon="Server"),
        _def("api-architect", "API Architect", CODING,
             "REST/GraphQL API contracts, versioning, error handling, rate limiting.",
             ["api_design", "backend"],
             "Design clean API contracts (REST/GraphQL) with versioning, consistent error handling, and rate limiting.",
             priority=68, icon="Plug"),
        _def("database-engineer", "Database Engineer", CODING,
             "Database architecture, schema, indexes, queries, migrations, integrity.",
             ["database_design", "backend", "sql"],
             "Design schemas, indexes, migrations, and maintain data integrity and query performance.",
             priority=72, icon="Database"),
        _def("debugging-specialist", "Debugging Specialist", CODING,
             "Analyzes errors, reproduces bugs, identifies root causes, proposes fixes.",
             ["debugging", "testing"],
             "Reproduce failures, identify root causes, and propose verified fixes.",
             priority=70, icon="Bug"),
        _def("code-tester", "Code Tester", CODING,
             "Unit, integration, e2e, regression testing; edge cases.",
             ["testing"],
             "Design and run unit, integration, and end-to-end tests incl. edge cases and regression.",
             priority=72, icon="TestTube"),
        _def("security-reviewer", "Security Reviewer", CODING,
             "Authentication, authorization, input validation, secrets, OWASP risks, data exposure.",
             ["security", "verification"],
             "Audit for authN/authZ weaknesses, injection, secret leakage, OWASP issues, and data exposure.",
             priority=90, icon="Shield"),
        _def("deployment-engineer", "Deployment Engineer", CODING,
             "Production builds, deployment, env config, CI/CD, hosting.",
             ["deployment", "devops", "backend"],
             "Produce production builds, environment configuration, CI/CD pipelines, and deployment guidance.",
             priority=65, icon="Rocket"),
    ]

    # ----------------------------- 3. RESEARCH -----------------------------
    agents += [
        _def("web-researcher", "Web Researcher", RESEARCH,
             "Searches the web, gathers sources, extracts relevant current information.",
             ["web_search", "research"],
             "Search the web and return current, well-sourced findings relevant to the objective.",
             tools=["web_search"], priority=75, icon="Search"),
        _def("deep-researcher", "Deep Researcher", RESEARCH,
             "Multi-source investigation, long-form research, cross-source comparison, pattern identification.",
             ["deep_research", "research", "web_search"],
             "Conduct deep multi-source investigation, cross-source comparison, and synthesize long-form findings.",
             tools=["web_search"], priority=70, icon="Radar"),
        _def("fact-checker", "Fact Checker", RESEARCH,
             "Verifies factual claims, detects unsupported claims, compares sources.",
             ["fact_checking", "verification", "web_search"],
             "Verify claims against multiple sources; flag unsupported or contradictory assertions.",
             tools=["web_search"], priority=92, icon="CheckCircle"),
        _def("source-evaluator", "Source Evaluator", RESEARCH,
             "Evaluates source quality, ranks sources, identifies primary vs unreliable sources.",
             ["source_evaluation", "web_search"],
             "Rank sources by credibility, identify primary sources, and flag unreliable ones.",
             tools=["web_search"], priority=75, icon="Scale"),
        _def("technical-researcher", "Technical Researcher", RESEARCH,
             "Researches technical subjects, documentation, APIs, frameworks, architecture.",
             ["technical_research", "web_search", "documentation_research"],
             "Research technical subjects, frameworks, APIs, and architecture with authoritative sources.",
             tools=["web_search"], priority=72, icon="Microscope"),
        _def("academic-researcher", "Academic Researcher", RESEARCH,
             "Papers, research literature, academic sources, scientific evidence.",
             ["academic_research", "web_search"],
             "Find and summarize academic papers, literature, and scientific evidence.",
             tools=["web_search"], priority=70, icon="GraduationCap"),
        _def("documentation-researcher", "Documentation Researcher", RESEARCH,
             "Official documentation, SDKs, libraries, configuration, usage examples.",
             ["documentation_research", "technical_research", "web_search"],
             "Study official docs, SDKs, and libraries; return accurate configuration and usage details.",
             tools=["web_search"], priority=70, icon="BookOpen"),
        _def("competitive-researcher", "Competitive Researcher", RESEARCH,
             "Competitor research, feature comparisons, market positioning, product differences.",
             ["competitive_research", "market_analysis", "web_search"],
             "Research competitors, compare features and positioning, and summarize market differences.",
             tools=["web_search"], priority=72, icon="Crosshair"),
        _def("information-extractor", "Information Extractor", RESEARCH,
             "Extracts structured information, converts unstructured content into data, summarizes evidence.",
             ["information_extraction", "research_synthesis"],
             "Extract structured, factual information from unstructured content and summarize evidence inline.",
             tools=["knowledge_search"], priority=70, icon="ClipboardList"),
        _def("research-synthesizer", "Research Synthesizer", RESEARCH,
             "Combines research outputs, removes duplication, resolves source conflicts, draws conclusions.",
             ["research_synthesis", "synthesis"],
             "Merge research outputs into a coherent conclusion; de-duplicate and resolve conflicts.",
             priority=75, tier="strong", icon="Layers"),
    ]

    # ------------------------------ 4. CONTENT -----------------------------
    agents += [
        _def("hindi-scriptwriter", "Hindi Scriptwriter", CONTENT,
             "Creates native-quality Hindi scripts and content.",
             ["scriptwriting", "content_writing"],
             "Write fluent, natural Hindi scripts and content with correct script and register.",
             priority=60, icon="PenLine"),
        _def("english-scriptwriter", "English Scriptwriter", CONTENT,
             "Creates English scripts and content.",
             ["scriptwriting", "content_writing"],
             "Write polished English scripts and content for video, web, or narrative use.",
             priority=60, icon="PenLine"),
        _def("copywriter", "Copywriter", CONTENT,
             "Creates persuasive marketing copy.",
             ["copywriting", "content_writing", "seo_writing"],
             "Write persuasive, benefit-driven marketing copy with clear calls to action.",
             priority=62, icon="Megaphone"),
        _def("story-writer", "Story Writer", CONTENT,
             "Creates narratives and storytelling structures.",
             ["storywriting", "content_writing"],
             "Craft compelling narratives with strong structure, tension, and payoff.",
             priority=58, icon="BookText"),
        _def("technical-writer", "Technical Writer", CONTENT,
             "Creates technical documentation and reference material.",
             ["technical_writing", "documentation"],
             "Write clear, accurate technical documentation, guides, and references.",
             priority=62, icon="FileText"),
        _def("seo-writer", "SEO Writer", CONTENT,
             "Creates search-optimized content that remains human-readable.",
             ["seo_writing", "content_writing"],
             "Write search-optimized content with natural keyword usage and strong readability.",
             priority=60, icon="TrendingUp"),
        _def("hook-specialist", "Hook Specialist", CONTENT,
             "Creates attention-grabbing openings.",
             ["hooks", "content_writing"],
             "Design attention-grabbing openings (hooks) for articles, videos, emails, or scripts.",
             priority=58, icon="Sparkles"),
        _def("editor", "Editor", CONTENT,
             "Improves structure, clarity and flow of content.",
             ["editing", "content_writing"],
             "Edit draft content to improve structure, clarity, tone, and flow.",
             priority=64, icon="Scissors"),
        _def("grammar-reviewer", "Grammar Reviewer", CONTENT,
             "Checks grammar, spelling and language correctness.",
             ["grammar", "editing"],
             "Review content for grammar, spelling, punctuation, and language correctness.",
             priority=90, tier="cheap", icon="SpellCheck"),
        _def("writing-critic", "Writing Critic", CONTENT,
             "Reviews writing quality and identifies weaknesses.",
             ["critique_writing", "editing"],
             "Critique writing quality; identify weak areas with specific, actionable feedback.",
             priority=70, icon="MessageSquareWarning"),
    ]

    # ------------------------------ 5. VISUAL ------------------------------
    agents += [
        _def("image-director", "Image Director", VISUAL,
             "Plans visual requirements for a project.",
             ["visual_design", "image_prompting"],
             "Define visual requirements: style, subjects, formats, and quantities needed.",
             priority=58, icon="Image"),
        _def("prompt-engineer", "Prompt Engineer", VISUAL,
             "Creates effective prompts for generative image models.",
             ["image_prompting", "prompt_engineering"],
             "Craft precise, well-structured prompts for generative image models.",
             priority=62, icon="Wand"),
        _def("thumbnail-strategist", "Thumbnail Strategist", VISUAL,
             "Designs thumbnail concepts that maximize click-through.",
             ["thumbnail_design", "visual_design"],
             "Design high-CTR thumbnail concepts: focal subject, contrast, text hierarchy.",
             priority=58, icon="MousePointerClick"),
        _def("composition-designer", "Composition Designer", VISUAL,
             "Plans visual composition.",
             ["composition", "visual_design"],
             "Plan compositional layout: focal points, balance, leading lines, rule of thirds.",
             priority=56, icon="LayoutGrid"),
        _def("lighting-specialist", "Lighting Specialist", VISUAL,
             "Designs lighting requirements for scenes.",
             ["lighting", "visual_design"],
             "Specify lighting direction, quality, mood, and fixtures for the intended look.",
             priority=54, icon="Lightbulb"),
        _def("colour-grading-specialist", "Colour-Grading Specialist", VISUAL,
             "Defines visual color direction.",
             ["color_grading", "visual_design"],
             "Define a cohesive color palette and grading direction for the project.",
             priority=56, icon="Palette"),
        _def("ui-designer", "UI Designer", VISUAL,
             "Creates interface design concepts.",
             ["ui_design", "visual_design"],
             "Produce interface design concepts: layout, spacing, typography, visual hierarchy.",
             priority=64, icon="MonitorSmartphone"),
        _def("ux-designer", "UX Designer", VISUAL,
             "Designs user experience and flows.",
             ["ux_design", "ux_research"],
             "Design user flows, information architecture, and interaction patterns.",
             priority=64, icon="MousePointer2"),
        _def("brand-designer", "Brand Designer", VISUAL,
             "Develops visual identity and brand systems.",
             ["branding", "visual_design"],
             "Develop visual identity: logo direction, color system, typography, brand guidelines.",
             priority=58, icon="Fingerprint"),
        _def("visual-critic", "Visual Critic", VISUAL,
             "Reviews visual output for quality and consistency.",
             ["critique_visual", "visual_design"],
             "Review visual work for quality, consistency, and objective alignment.",
             priority=70, icon="Eye"),
    ]

    # ------------------------------- 6. DATA -------------------------------
    agents += [
        _def("data-analyst", "Data Analyst", DATA,
             "Analyzes datasets and answers data-driven questions.",
             ["data_analysis", "statistics"],
             "Analyze datasets; produce clear quantitative findings and interpretations.",
             required_tools=["calculator"], priority=70, icon="BarChart"),
        _def("spreadsheet-specialist", "Spreadsheet Specialist", DATA,
             "Works with spreadsheets: formulas, structure, cleanup.",
             ["spreadsheets", "data_analysis"],
             "Work with spreadsheet data: formulas, structuring, and cleaning.",
             priority=60, icon="Table"),
        _def("sql-analyst", "SQL Analyst", DATA,
             "Creates and optimizes SQL queries.",
             ["sql", "database_design"],
             "Write and optimize correct, performant SQL queries.",
             priority=64, icon="Database"),
        _def("statistics-specialist", "Statistics Specialist", DATA,
             "Performs statistical analysis and interprets results.",
             ["statistics", "data_analysis"],
             "Apply and interpret statistical methods correctly; state assumptions and limitations.",
             required_tools=["calculator"], priority=66, icon="Sigma"),
        _def("chart-designer", "Chart Designer", DATA,
             "Determines appropriate visualizations for data.",
             ["chart_design", "visual_design", "reporting"],
             "Choose and specify the right chart/visualization type for the data and audience (Mermaid/ASCII acceptable).",
             priority=58, icon="PieChart"),
        _def("data-cleaner", "Data Cleaner", DATA,
             "Cleans and validates datasets.",
             ["data_cleaning", "data_analysis"],
             "Clean and validate datasets: missing values, outliers, type consistency.",
             priority=62, icon="Brush"),
        _def("forecasting-agent", "Forecasting Agent", DATA,
             "Performs forecasting and trend projection.",
             ["forecasting", "statistics", "data_analysis"],
             "Project trends and forecast future values with stated assumptions and confidence.",
             required_tools=["calculator"], priority=60, icon="TrendingUp"),
        _def("report-generator", "Report Generator", DATA,
             "Creates structured reports from analysis.",
             ["reporting", "content_writing"],
             "Structure analysis into a clear, decision-ready report.",
             priority=64, tier="balanced", icon="FileText"),
        _def("data-verifier", "Data Verifier", DATA,
             "Checks data correctness and consistency.",
             ["data_verification", "verification"],
             "Verify data correctness: totals, derivations, and logical consistency.",
             priority=88, icon="BadgeCheck"),
        _def("insight-synthesizer", "Insight Synthesizer", DATA,
             "Converts data into actionable insights.",
             ["insight_synthesis", "data_analysis"],
             "Synthesize data into prioritized, decision-ready insights.",
             priority=66, tier="balanced", icon="Lightbulb"),
    ]

    # ------------------------------ 7. PRODUCT -----------------------------
    agents += [
        _def("product-manager", "Product Manager", PRODUCT,
             "Defines product direction, scope, and priorities.",
             ["product_strategy", "planning"],
             "Define product direction, prioritize features, and manage scope trade-offs.",
             priority=74, tier="strong", icon="Target"),
        _def("product-researcher", "Product Researcher", PRODUCT,
             "Researches product opportunities.",
             ["product_research", "research"],
             "Research product opportunities, user problems, and market fit.",
             priority=64, icon="Search"),
        _def("feature-analyst", "Feature Analyst", PRODUCT,
             "Evaluates features against goals and constraints.",
             ["feature_analysis", "product_strategy"],
             "Evaluate proposed features: value, cost, feasibility, and risk.",
             priority=64, icon="ListChecks"),
        _def("user-researcher", "User Researcher", PRODUCT,
             "Analyzes user needs and personas.",
             ["user_research", "ux_research"],
             "Analyze user needs, pain points, and personas from available signals.",
             priority=64, icon="Users"),
        _def("ux-researcher", "UX Researcher", PRODUCT,
             "Studies user behavior and usability.",
             ["ux_research", "user_research"],
             "Study usability and user behavior; derive implications for design.",
             priority=64, icon="SearchCheck"),
        _def("market-analyst", "Market Analyst", PRODUCT,
             "Analyzes markets, sizing, and trends.",
             ["market_analysis", "market_research"],
             "Analyze market size, growth, segments, and trends.",
             tools=["web_search"], priority=64, icon="TrendingUp"),
        _def("competitor-analyst", "Competitor Analyst", PRODUCT,
             "Analyzes competitors and their positions.",
             ["competitor_analysis", "competitive_research"],
             "Analyze competitor offerings, positioning, and gaps.",
             tools=["web_search"], priority=64, icon="Crosshair"),
        _def("pricing-strategist", "Pricing Strategist", PRODUCT,
             "Develops pricing strategies.",
             ["pricing", "financial_analysis", "strategy"],
             "Develop pricing strategies grounded in value, costs, and market benchmarks.",
             priority=60, icon="Tags"),
        _def("growth-strategist", "Growth Strategist", PRODUCT,
             "Develops growth strategies and channels.",
             ["growth", "strategy", "market_analysis"],
             "Develop growth strategies, channel plans, and acquisition/retention levers.",
             priority=62, icon="Rocket"),
        _def("product-critic", "Product Critic", PRODUCT,
             "Challenges product decisions and assumptions.",
             ["critique_product", "risk_analysis"],
             "Stress-test product decisions: unproven assumptions, weak differentiators, missing trade-offs.",
             priority=78, icon="ShieldAlert"),
    ]

    # ----------------------------- 8. AI/ML --------------------------------
    agents += [
        _def("ai-researcher", "AI Researcher", AI_ML,
             "Researches AI technologies and approaches.",
             ["ai_research", "technical_research", "web_search"],
             "Research AI approaches, models, and techniques with recent authoritative sources.",
             tools=["web_search"], priority=68, icon="BrainCircuit"),
        _def("ml-engineer", "ML Engineer", AI_ML,
             "Designs machine-learning systems.",
             ["ml", "code_python", "data_analysis"],
             "Design ML systems: problem framing, data, features, models, and evaluation.",
             priority=66, icon="Cpu"),
        _def("deep-learning-engineer", "Deep Learning Engineer", AI_ML,
             "Works with deep learning architectures.",
             ["deep_learning", "ml", "code_python"],
             "Design deep learning architectures appropriate to the problem and data.",
             priority=62, icon="Network"),
        _def("llm-specialist", "LLM Specialist", AI_ML,
             "Handles LLM architecture, inference, and prompting.",
             ["llm", "prompt_engineering", "ai_optimization"],
             "Apply LLM best practices: architecture, inference, context design, and prompting.",
             priority=70, tier="strong", icon="Bot"),
        _def("rag-specialist", "RAG Specialist", AI_ML,
             "Designs retrieval-augmented generation systems.",
             ["rag", "llm", "information_extraction"],
             "Design RAG systems: chunking, embeddings, retrieval, reranking, and grounding.",
             priority=72, icon="LibraryBig"),
        _def("ai-prompt-specialist", "AI Prompt Specialist", AI_ML,
             "Designs and optimizes prompts.",
             ["prompt_engineering", "llm"],
             "Design and optimize prompts for quality, consistency, and cost.",
             priority=66, icon="Wand"),
        _def("ai-evaluator", "AI Evaluator", AI_ML,
             "Evaluates model / system outputs.",
             ["model_evaluation", "verification"],
             "Evaluate outputs for correctness, safety, and quality; report structured findings.",
             priority=88, icon="ClipboardCheck"),
        _def("model-selector", "Model Selector", AI_ML,
             "Chooses appropriate models based on requirements.",
             ["model_selection", "ai_optimization"],
             "Recommend models by complexity, quality, latency, cost, and context needs.",
             priority=70, tier="cheap", icon="SlidersHorizontal"),
        _def("ai-safety-reviewer", "AI Safety Reviewer", AI_ML,
             "Reviews AI behavior and risks.",
             ["ai_safety", "verification", "risk_analysis"],
             "Review AI behavior for safety risks: bias, jailbreaks, harmful outputs, and misuse.",
             priority=90, icon="ShieldCheck"),
        _def("ai-optimizer", "AI Optimizer", AI_ML,
             "Optimizes AI pipelines for quality, latency, and cost.",
             ["ai_optimization", "model_selection"],
             "Optimize AI pipelines: latency, token cost, caches, and model choices.",
             priority=64, icon="Gauge"),
    ]

    # ---------------------------- 9. AUTOMATION ----------------------------
    agents += [
        _def("workflow-architect", "Workflow Architect", AUTOMATION,
             "Designs automation workflows.",
             ["workflow_design", "automation"],
             "Design reliable automation workflows with explicit triggers, steps, and error paths.",
             required_tools=["calculator"], priority=64, icon="Workflow"),
        _def("automation-engineer", "Automation Engineer", AUTOMATION,
             "Implements automation workflows.",
             ["automation", "workflow_design", "code_python"],
             "Implement automation workflows that are robust to failures and re-runs.",
             priority=64, icon="Bot"),
        _def("browser-automation-agent", "Browser Automation Agent", AUTOMATION,
             "Handles browser automation and UI flows.",
             ["browser_automation", "automation"],
             "Specify browser automation flows: selectors, waits, and assertions.",
             priority=58, icon="Globe"),
        _def("api-automation-agent", "API Automation Agent", AUTOMATION,
             "Handles API-based automation.",
             ["api_automation", "api_design", "automation"],
             "Specify API automation flows: endpoints, auth, retries, and rate handling.",
             priority=60, icon="Plug"),
        _def("scraping-specialist", "Scraping Specialist", AUTOMATION,
             "Handles permitted web data extraction.",
             ["scraping", "web_search"],
             "Plan permitted web data extraction: sources, selectors, and rate limits.",
             tools=["web_search"], priority=58, icon="Download"),
        _def("file-management-agent", "File Management Agent", AUTOMATION,
             "Handles file organization and processing.",
             ["file_management", "automation"],
             "Specify file organization and processing workflows, incl. naming and cleanup.",
             tools=["drive"], priority=56, icon="FolderOpen"),
        _def("email-automation-agent", "Email Automation Agent", AUTOMATION,
             "Handles email workflows.",
             ["email_automation", "automation"],
             "Specify email workflows: templates, triggers, and sending rules.",
             priority=56, icon="Mail"),
        _def("scheduling-agent", "Scheduling Agent", AUTOMATION,
             "Handles scheduling workflows.",
             ["scheduling", "workflow_design"],
             "Specify scheduling workflows: cadence, time zones, and missed-run handling.",
             priority=58, icon="Clock"),
        _def("integration-specialist", "Integration Specialist", AUTOMATION,
             "Connects external services.",
             ["integrations", "api_design"],
             "Design integrations between external services with auth and error handling.",
             priority=60, icon="Share2"),
        _def("automation-tester", "Automation Tester", AUTOMATION,
             "Tests automation reliability.",
             ["automation_testing", "testing"],
             "Validate automation workflows for reliability, idempotency, and failure recovery.",
             priority=72, icon="TestTube"),
    ]

    # ---------------------- 10. BUSINESS & QUALITY -------------------------
    agents += [
        _def("business-analyst", "Business Analyst", BUSINESS,
             "Analyzes business requirements and processes.",
             ["business_analysis", "requirements"],
             "Analyze business requirements, processes, and stakeholder needs.",
             priority=66, icon="Briefcase"),
        _def("market-researcher", "Market Researcher", BUSINESS,
             "Researches market conditions.",
             ["market_research", "market_analysis", "web_search"],
             "Research market conditions, demand, and competitive landscape.",
             tools=["web_search"], priority=64, icon="Search"),
        _def("financial-analyst", "Financial Analyst", BUSINESS,
             "Performs financial analysis.",
             ["financial_analysis", "data_analysis"],
             "Perform financial analysis: costs, pricing, margins, and scenarios.",
             required_tools=["calculator"], priority=66, icon="Coins"),
        _def("strategy-consultant", "Strategy Consultant", BUSINESS,
             "Develops strategic recommendations.",
             ["strategy", "business_analysis"],
             "Develop clear, evidence-backed strategic recommendations with trade-offs.",
             priority=70, icon="Compass"),
        _def("risk-analyst", "Risk Analyst", BUSINESS,
             "Identifies risks and mitigations.",
             ["risk_analysis", "verification"],
             "Identify risks, likelihood/impact, and mitigations.",
             priority=88, icon="Shield"),
        _def("policy-researcher", "Policy Researcher", BUSINESS,
             "Researches policies, regulations, and compliance requirements.",
             ["policy_research", "research", "web_search"],
             "Research relevant policies and regulations; summarize applicability and obligations.",
             tools=["web_search"], priority=70, icon="ScrollText"),
        _def("quality-controller", "Quality Controller", BUSINESS,
             "Performs overall quality checks.",
             ["quality_control", "verification"],
             "Check overall quality: completeness, consistency, correctness, and presentation.",
             priority=92, icon="BadgeCheck"),
        _def("verification-agent", "Verification Agent", BUSINESS,
             "Verifies important outputs before delivery.",
             ["verification", "quality_control"],
             "Verify the deliverable against the original objective; report discrepancies.",
             priority=95, tier="strong", icon="CheckCheck"),
        _def("red-team-critic", "Red-Team Critic", BUSINESS,
             "Finds weaknesses, failures, and incorrect assumptions.",
             ["red_team", "verification", "risk_analysis"],
             "Actively hunt for incorrect assumptions, missing requirements, contradictions, security problems, and edge cases. Return structured issues, do not rewrite the whole deliverable.",
             priority=94, tier="strong", icon="Skull"),
        _def("executive-reviewer", "Executive Reviewer", BUSINESS,
             "Performs final executive-level review before completion.",
             ["executive_review", "verification"],
             "Perform the final executive review: does the deliverable fully, correctly and credibly fulfil the request?",
             priority=98, tier="strong", icon="Crown"),
    ]

    expected = 100
    if len(agents) != expected:
        raise RuntimeError(f"Agentic registry expected {expected} agents, got {len(agents)}")
    return agents


_AGENT_DEFS: list[AgentDef] | None = None


def get_agent_defs() -> list[AgentDef]:
    global _AGENT_DEFS
    if _AGENT_DEFS is None:
        _AGENT_DEFS = _build_agent_defs()
    return _AGENT_DEFS


# ---------------------------------------------------------------------------
# Executive Agent Registry
# ---------------------------------------------------------------------------

class ExecutiveRegistry:
    """Registry of the 100 specialized agents with capability-based discovery.

    Kept separate from the operational AgentRegistry so existing features and
    tests are untouched. Constructed lazily — no work at import time.
    """

    _instance = None

    def __init__(self) -> None:
        self._agents: dict[str, RoleAgent] = {}
        self._by_department: dict[str, list[RoleAgent]] = {}
        for definition in get_agent_defs():
            agent = RoleAgent(definition)
            self._agents[definition.slug] = agent
            self._by_department.setdefault(definition.department, []).append(agent)

    @classmethod
    def get(cls) -> "ExecutiveRegistry":
        if cls._instance is None:
            cls._instance = ExecutiveRegistry()
        return cls._instance

    def all_agents(self) -> list[RoleAgent]:
        return list(self._agents.values())

    def count(self) -> int:
        return len(self._agents)

    def get_agent(self, slug: str) -> RoleAgent | None:
        return self._agents.get(slug)

    def departments(self) -> list[str]:
        return list(self._by_department.keys())

    def agents_in_department(self, department: str) -> list[RoleAgent]:
        return self._by_department.get(department, [])

    def get_manifests(self) -> list[AgentManifest]:
        return [a.manifest for a in self._agents.values()]

    def find_by_capabilities(self, required: list[str], limit: int = 5) -> list[RoleAgent]:
        """Score every enabled agent by capability overlap against `required`."""
        wanted = set(c.strip().lower() for c in required if c and str(c).strip())
        scored: list[tuple[float, RoleAgent]] = []
        for agent in self._agents.values():
            manifest = agent.manifest
            if not manifest.enabled:
                continue
            have = set(c.lower() for c in manifest.capabilities)
            overlap = len(wanted & have)
            coverage = overlap / max(len(wanted), 1)
            precision = overlap / max(len(have), 1)
            pool_penalty = 0.0 if manifest.can_run_in_parallel else 0.05
            score = (0.75 * coverage + 0.25 * precision) * (manifest.priority / 100.0)
            if manifest.model_tier == "strong":
                score *= 0.92  # slightly prefer cheaper balanced workers when they suffice
            score -= pool_penalty + 0.001 * manifest.cost_weight
            scored.append((score, agent))
        scored.sort(key=lambda item: (-item[0], item[1].manifest.priority))
        return [a for _, a in scored[:limit] if payload(a)]


def payload(agent: RoleAgent) -> bool:
    """Return True for any agent (keeps sorting stable and self-documenting)."""
    return True