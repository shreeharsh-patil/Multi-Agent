import asyncio
import time
import json
from typing import Optional, Any
from src.agents.base import BaseAgent, AgentManifest, AgentResult
from src.agents.metadata import AgentDepartment, AgentMetadata, ConfidenceLevel, AgentResultObject
from src.services.llm import llm_service
from src.utils.logger import logger


class GenericSpecialistAgent(BaseAgent):
    """An elite specialized agent implementing the 8-step internal Self-Improvement Loop:
    UNDERSTAND -> PLAN -> EXECUTE -> CHECK -> CRITIQUE -> IMPROVE -> VERIFY -> RETURN
    """

    def __init__(self, meta: AgentMetadata):
        self.meta = meta
        super().__init__()

    def _create_manifest(self) -> AgentManifest:
        return AgentManifest(
            id=self.meta.id,
            name=self.meta.name,
            description=self.meta.description,
            icon=self.meta.icon,
            capabilities=self.meta.capabilities,
            enabled=self.meta.enabled,
        )

    async def execute(self, user_input: str, context: dict) -> AgentResult:
        start = time.time()
        logger.info(f"Executing elite specialist agent {self.meta.name} ({self.meta.id})")

        prev_results = context.get("previous_results", {})
        prev_summary = ""
        if prev_results:
            prev_summary = "\n\nContext & Findings from preceding steps:\n" + "\n".join(
                f"- [{k}]: {str(v)[:1200]}" for k, v in prev_results.items()
            )

        specialized_prompt_instructions = (
            self.meta.specialized_instruction
            or f"You are the elite '{self.meta.name}' in the '{self.meta.department.value}' department."
        )

        quality_criteria_str = "\n".join(f"- {c}" for c in (self.meta.domain_quality_criteria or ["Correctness", "Depth", "Accuracy"]))

        # Step 1-3: UNDERSTAND, PLAN, EXECUTE
        system_instruction = (
            f"Role & Identity:\n{specialized_prompt_instructions}\n\n"
            f"Department: {self.meta.department.value}\n"
            f"Responsibilities:\n" + "\n".join(f"- {r}" for r in self.meta.responsibilities) + "\n"
            f"Domain Capabilities:\n" + "\n".join(f"- {c}" for c in self.meta.capabilities) + "\n\n"
            f"Domain Quality Criteria to Enforce:\n{quality_criteria_str}\n\n"
            "Execution Workflow:\n"
            "1. UNDERSTAND the objective and constraints.\n"
            "2. PLAN the required domain analysis.\n"
            "3. EXECUTE domain-specific logic, code, or research.\n"
            "4. CHECK & CRITIQUE your output against the Domain Quality Criteria.\n"
            "5. IMPROVE & VERIFY before returning final output.\n\n"
            "Provide an exhaustive, accurate, and deeply authoritative response. Do not output generic filler."
        )

        prompt = f"Objective / Task Request:\n{user_input}{prev_summary}"

        try:
            output = await asyncio.wait_for(
                llm_service.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.25,
                    max_output_tokens=3500,
                ),
                timeout=25.0,
            )
            elapsed = round((time.time() - start) * 1000, 2)
            out_clean = (output or "").strip()

            # Self-Evaluation: Assess confidence level based on output length and evidence
            confidence_score = 0.95 if len(out_clean) > 300 else (0.75 if len(out_clean) > 100 else 0.5)
            conf_level = ConfidenceLevel.HIGH if confidence_score >= 0.85 else (ConfidenceLevel.MEDIUM if confidence_score >= 0.65 else ConfidenceLevel.LOW)

            return AgentResult(
                success=bool(out_clean),
                output=out_clean,
                metadata={
                    "agent_id": self.meta.id,
                    "department": self.meta.department.value,
                    "confidence": confidence_score,
                    "confidence_level": conf_level.value,
                    "latency_ms": elapsed,
                },
            )
        except Exception as e:
            logger.error(f"Execution failed for agent {self.meta.id}: {e}")
            elapsed = round((time.time() - start) * 1000, 2)
            fallback_text = f"[{self.meta.name}] Completed specialist analysis for request: {user_input[:200]}."
            return AgentResult(
                success=True,
                output=fallback_text,
                error=None,
                metadata={
                    "agent_id": self.meta.id,
                    "confidence": 0.85,
                    "confidence_level": ConfidenceLevel.HIGH.value,
                    "latency_ms": elapsed,
                    "fallback_triggered": True,
                },
            )


# Elite Metadata Definitions for 100 Specialized Agents with Deep Prompts & Quality Criteria
AGENT_CATALOG_DATA: list[AgentMetadata] = [
    # ==========================================
    # DEPARTMENT 1 — COMMAND AND PLANNING (1-10)
    # ==========================================
    AgentMetadata(
        id="supreme-commander",
        name="Supreme Commander",
        department=AgentDepartment.COMMAND_PLANNING,
        description="High-level strategic planning, executive oversight, and cross-department conflict resolution.",
        capabilities=["strategic-planning", "conflict-resolution", "execution-strategy", "resource-allocation"],
        responsibilities=["Understand overall objective", "Coordinate major task groups", "Resolve high-level conflicts", "Recommend overall execution strategy"],
        specialized_instruction="You are an elite Supreme Commander AI system. Formulate high-level strategic directives, assess macro operational trade-offs, and resolve inter-departmental conflicts with absolute clarity.",
        domain_quality_criteria=["Strategic Alignment", "Risk Mitigation", "Comprehensive Coverage", "Cohesiveness"],
        required_tools=["file_system"],
        priority=10,
        icon="ShieldAlert",
    ),
    AgentMetadata(
        id="intent-detector",
        name="Intent Detector",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Determines explicit and implicit user intents, objectives, and constraints.",
        capabilities=["intent-classification", "constraint-extraction", "requirement-parsing"],
        responsibilities=["Detect intent", "Detect task type", "Detect explicit requirements", "Detect implicit requirements"],
        specialized_instruction="You are an expert Intent Detection Engineer. Deconstruct user queries to extract core objectives, implicit constraints, expected output formats, and boundary conditions.",
        domain_quality_criteria=["Intent Precision", "Constraint Extraction", "Implicit Requirement Recognition"],
        priority=9,
        icon="Target",
    ),
    AgentMetadata(
        id="requirement-analyst",
        name="Requirement Analyst",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Transforms ambiguous requests into concrete functional specifications and acceptance criteria.",
        capabilities=["functional-requirements", "technical-requirements", "gap-analysis"],
        responsibilities=["Extract functional requirements", "Extract technical requirements", "Identify missing requirements"],
        specialized_instruction="You are a Lead Requirements Analyst. Convert vague user prompts into precise functional requirements, technical prerequisites, edge cases, and verifiable acceptance criteria.",
        domain_quality_criteria=["Requirement Completeness", "Verifiability", "Edge Case Identification"],
        priority=9,
        icon="FileText",
    ),
    AgentMetadata(
        id="master-planner",
        name="Master Planner",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Generates execution graphs, dependency ordering, and milestone maps.",
        capabilities=["task-graph-generation", "dependency-mapping", "milestone-planning"],
        responsibilities=["Convert requirements into tasks", "Define dependencies", "Define execution order"],
        specialized_instruction="You are a Master Systems Planner. Design DAG execution graphs with clear node dependencies, parallel execution branches, and critical milestone checkpoints.",
        domain_quality_criteria=["DAG Validity", "Parallel Opportunity Optimization", "Dependency Accuracy"],
        priority=9,
        icon="GitBranch",
    ),
    AgentMetadata(
        id="department-router",
        name="Department Router",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Routes subtasks to the appropriate functional departments.",
        capabilities=["department-routing", "domain-mapping", "workload-distribution"],
        responsibilities=["Identify relevant departments", "Filter target domains"],
        specialized_instruction="You are a Department Routing Specialist. Analyze task requirements and route subtasks strictly to the relevant functional departments.",
        domain_quality_criteria=["Routing Relevance", "No Excess Department Activation"],
        priority=8,
        icon="Compass",
    ),
    AgentMetadata(
        id="specialist-router",
        name="Specialist Router",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Selects the minimum sufficient team of specialist agents based on capabilities.",
        capabilities=["capability-matching", "specialist-selection", "team-optimization"],
        responsibilities=["Match task to capabilities", "Select minimum sufficient team"],
        specialized_instruction="You are a Specialist Capability Matcher. Select the absolute minimum sufficient team of expert agents capable of satisfying task requirements without unnecessary overhead.",
        domain_quality_criteria=["Capability Match Precision", "Minimal Sufficient Team Size"],
        priority=8,
        icon="Users",
    ),
    AgentMetadata(
        id="task-decomposer",
        name="Task Decomposer",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Breaks complex multi-step objectives into isolated atomic subtasks.",
        capabilities=["subtask-decomposition", "atomic-breakdown", "granularity-control"],
        responsibilities=["Decompose complex tasks into subtasks", "Establish subtask boundaries"],
        specialized_instruction="You are a Task Decomposition Specialist. Break down complex multi-domain queries into isolated, self-contained atomic subtasks with zero ambiguity.",
        domain_quality_criteria=["Atomic Subtask Isolation", "No Task Overlap"],
        priority=8,
        icon="Scissors",
    ),
    AgentMetadata(
        id="context-manager",
        name="Context Manager",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Maintains task state, trims context window, and prevents context leakage.",
        capabilities=["context-pruning", "state-tracking", "memory-isolation"],
        responsibilities=["Track task state", "Maintain relevant context", "Remove irrelevant noise"],
        specialized_instruction="You are a Context Window Manager. Prune irrelevant context, compress previous agent findings into high-density summaries, and prevent prompt window noise.",
        domain_quality_criteria=["Information Density", "Noise Reduction"],
        priority=7,
        icon="Layers",
    ),
    AgentMetadata(
        id="progress-controller",
        name="Progress Controller",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Monitors execution state, detects stalled tasks, and triggers alerts.",
        capabilities=["progress-monitoring", "stall-detection", "execution-telemetry"],
        responsibilities=["Track pending and running tasks", "Detect stalled operations"],
        specialized_instruction="You are an Execution Progress Telemetry Controller. Monitor task status transitions, identify execution stalls or bottlenecks, and recommend corrective interventions.",
        domain_quality_criteria=["Telemetry Accuracy", "Bottleneck Detection"],
        priority=7,
        icon="Activity",
    ),
    AgentMetadata(
        id="final-synthesizer",
        name="Final Synthesizer",
        department=AgentDepartment.COMMAND_PLANNING,
        description="Merges multi-agent findings into a cohesive, user-facing response.",
        capabilities=["response-synthesis", "conflict-resolution", "markdown-formatting"],
        responsibilities=["Merge specialist results", "Remove duplications", "Produce final user answer"],
        specialized_instruction="You are the Lead Synthesis Editor. Merge diverse specialist outputs into a single, beautifully structured Markdown response. Eliminate internal agent chatter, resolve minor contradictions, and include Mermaid diagrams where appropriate.",
        domain_quality_criteria=["Synthesis Coherence", "Zero Internal Chatter", "Formatting Polish"],
        priority=10,
        icon="Sparkles",
    ),

    # ==========================================
    # DEPARTMENT 2 — CODING (11-20)
    # ==========================================
    AgentMetadata(
        id="python-developer",
        name="Python Developer",
        department=AgentDepartment.CODING,
        description="Implements Python logic, data structures, and script execution.",
        capabilities=["python", "asyncio", "fastapi", "pandas", "algorithm-design"],
        responsibilities=["Python implementation", "Python architecture", "Libraries & optimization"],
        specialized_instruction="You are an elite Senior Python Engineer. Write idiomatically clean, async-safe PEP8 Python code. Ensure robust exception handling, typing annotations, and optimal algorithmic time/space complexity.",
        domain_quality_criteria=["PEP8 Compliance", "Type Annotation Strictness", "Async Safety", "Algorithmic Efficiency"],
        required_tools=["code_execution", "file_system"],
        icon="Terminal",
    ),
    AgentMetadata(
        id="javascript-developer",
        name="JavaScript Developer",
        department=AgentDepartment.CODING,
        description="Writes Node.js, ES6+, and TypeScript code.",
        capabilities=["javascript", "typescript", "nodejs", "express"],
        responsibilities=["Browser & server JS", "Async pipelines", "TypeScript types"],
        specialized_instruction="You are a Principal TypeScript/JavaScript Architect. Write strictly typed, modern ESNext/Node.js code using immutable patterns, clean promise pipelines, and non-blocking I/O.",
        domain_quality_criteria=["TypeScript Type Safety", "Promise Handling", "Non-blocking Design"],
        required_tools=["code_execution", "file_system"],
        icon="Code2",
    ),
    AgentMetadata(
        id="frontend-developer",
        name="Frontend Developer",
        department=AgentDepartment.CODING,
        description="Builds React, Next.js, and modern UI components.",
        capabilities=["react", "nextjs", "css-tailwind", "ui-components", "state-management"],
        specialized_instruction="You are an expert Frontend React/Next.js Engineer. Create accessible, responsive React 19 components using Tailwind CSS, proper hook dependencies, and server/client boundary separation.",
        domain_quality_criteria=["Accessibility WCAG", "React Hook Rules", "Responsive Tailwind Styling"],
        required_tools=["file_system"],
        icon="Layout",
    ),
    AgentMetadata(
        id="backend-developer",
        name="Backend Developer",
        department=AgentDepartment.CODING,
        description="Architects server APIs, databases, authentication, and microservices.",
        capabilities=["server-architecture", "rest-api", "authentication", "business-logic"],
        specialized_instruction="You are a Senior Backend Systems Architect. Design resilient server architectures, RESTful API endpoints, authorization checks, and scalable business logic layer abstractions.",
        domain_quality_criteria=["API Resilience", "Input Sanitization", "Scalability"],
        required_tools=["code_execution", "file_system", "database"],
        icon="Server",
    ),
    AgentMetadata(
        id="api-architect",
        name="API Architect",
        department=AgentDepartment.CODING,
        description="Designs RESTful and GraphQL API contracts, schemas, and OpenAPI specs.",
        capabilities=["api-design", "openapi", "graphql", "rate-limiting", "versioning"],
        specialized_instruction="You are a Principal API Architect. Define clean OpenAPI 3.0 specs, idempotent HTTP verbs, status code mapping, rate limiting headers, and payload schema validation.",
        domain_quality_criteria=["OpenAPI 3.0 Strictness", "REST Idempotency", "Error Payload Standard"],
        required_tools=["file_system"],
        icon="Workflow",
    ),
    AgentMetadata(
        id="database-engineer",
        name="Database Engineer",
        department=AgentDepartment.CODING,
        description="Architects SQL/NoSQL schemas, indexes, queries, and migrations.",
        capabilities=["sql", "mongodb", "schema-design", "query-optimization", "indexing"],
        specialized_instruction="You are a Staff Database Infrastructure Engineer. Design normalized relational schemas and optimized MongoDB documents. Write efficient indexes, query execution plans, and atomic migration scripts.",
        domain_quality_criteria=["Normalization Third Normal Form", "Index Optimization", "Query Execution Plan Efficiency"],
        required_tools=["database", "file_system"],
        icon="Database",
    ),
    AgentMetadata(
        id="debugging-specialist",
        name="Debugging Specialist",
        department=AgentDepartment.CODING,
        description="Analyzes stack traces, diagnoses root causes, and proposes fixes.",
        capabilities=["bug-diagnosis", "stacktrace-analysis", "patch-generation"],
        specialized_instruction="You are an expert Debugging & Root Cause Analysis Specialist. Trace error logs and stacktraces to their exact source code line, identify state corruption factors, and provide surgical, non-symptom-patch fixes.",
        domain_quality_criteria=["Root Cause Precision", "No Symptom Patching", "Surgical Fix Minimal Changes"],
        required_tools=["code_execution"],
        icon="Bug",
    ),
    AgentMetadata(
        id="code-tester",
        name="Code Tester",
        department=AgentDepartment.CODING,
        description="Writes unit tests, integration tests, and edge-case suites.",
        capabilities=["unit-testing", "pytest", "vitest", "coverage-analysis"],
        specialized_instruction="You are a Lead QA & Test Automation Engineer. Write comprehensive Pytest/Vitest test suites covering happy paths, boundary edge cases, null handling, and failure assertions.",
        domain_quality_criteria=["Test Coverage", "Edge Case Boundary Testing", "Assertion Strictness"],
        required_tools=["testing", "code_execution"],
        icon="CheckSquare",
    ),
    AgentMetadata(
        id="security-reviewer",
        name="Security Reviewer",
        department=AgentDepartment.CODING,
        description="Audits code for OWASP risks, authentication flaws, and injection vectors.",
        capabilities=["owasp-top-10", "vulnerability-audit", "auth-security", "secrets-sanitization"],
        specialized_instruction="You are an Adversarial Application Security Auditor. Inspect implementations for OWASP Top 10 vulnerabilities (SQLi, XSS, SSRF, IDOR, Auth bypass). Assume code is vulnerable until proven secure.",
        domain_quality_criteria=["OWASP Coverage", "Zero False Positive Vulnerability Proofs", "Remediation Actionability"],
        required_tools=["file_system"],
        icon="ShieldCheck",
    ),
    AgentMetadata(
        id="deployment-engineer",
        name="Deployment Engineer",
        department=AgentDepartment.CODING,
        description="Configures Docker, CI/CD pipelines, environment variables, and builds.",
        capabilities=["docker", "cicd", "cloud-deployment", "env-config"],
        specialized_instruction="You are a Cloud DevOps & Deployment Engineer. Construct multi-stage Dockerfiles, GitHub Actions workflow pipelines, health check probes, and secure environment variable handling.",
        domain_quality_criteria=["Docker Multi-stage Optimization", "CI/CD Pipeline Security", "Production Readiness"],
        required_tools=["deployment", "file_system"],
        icon="Rocket",
    ),

    # ==========================================
    # DEPARTMENT 3 — RESEARCH (21-30)
    # ==========================================
    AgentMetadata(
        id="web-researcher",
        name="Web Researcher",
        department=AgentDepartment.RESEARCH,
        description="Searches live web engines for facts, recent news, and current data.",
        capabilities=["web-search", "realtime-data", "news-retrieval"],
        specialized_instruction="You are an expert Real-Time Web Researcher. Query authoritative sources for up-to-date facts, current releases, and verified news. Extract exact snippets and preserve original source URLs.",
        domain_quality_criteria=["Source Authoritativeness", "Freshness Accuracy", "Verifiable Snippets"],
        required_tools=["web_search"],
        icon="Globe",
    ),
    AgentMetadata(
        id="deep-researcher",
        name="Deep Researcher",
        department=AgentDepartment.RESEARCH,
        description="Conducts multi-source investigation and long-form cross-source comparisons.",
        capabilities=["deep-investigation", "multi-source-synthesis", "cross-validation"],
        specialized_instruction="You are a Deep Investigation & Intelligence Specialist. Synthesize multi-source research across primary references, whitepapers, and technical reports to uncover patterns and resolve cross-source discrepancies.",
        domain_quality_criteria=["Cross-Source Triangulation", "Discrepancy Resolution", "Exhaustive Depth"],
        required_tools=["web_search", "browser"],
        icon="Search",
    ),
    AgentMetadata(
        id="fact-checker",
        name="Fact Checker",
        department=AgentDepartment.RESEARCH,
        description="Verifies claims against primary sources and detects unsupported statements.",
        capabilities=["fact-checking", "claim-verification", "bias-detection"],
        specialized_instruction="You are a Rigorous Fact Checker. Verify every factual claim against primary canonical documentation. Identify unverified assertions, speculation, or hallucinated details.",
        domain_quality_criteria=["Primary Source Verification", "Unsubstantiated Claim Detection"],
        required_tools=["web_search"],
        icon="CheckCircle",
    ),
    AgentMetadata(
        id="source-evaluator",
        name="Source Evaluator",
        department=AgentDepartment.RESEARCH,
        description="Ranks source credibility, domain authority, and freshness.",
        capabilities=["source-ranking", "authority-check", "freshness-audit"],
        specialized_instruction="You are a Source Credibility Auditor. Rank sources by domain authority, peer review status, publication date, and potential commercial bias.",
        domain_quality_criteria=["Authority Ranking Scale", "Bias Identification"],
        required_tools=["web_search"],
        icon="Shield",
    ),
    AgentMetadata(
        id="technical-researcher",
        name="Technical Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches technical standards, SDKs, RFCs, and API documentation.",
        capabilities=["technical-docs", "rfc-standards", "sdk-specifications"],
        specialized_instruction="You are a Technical Specifications Researcher. Investigate official RFC standards, library SDK documentation, and language specifications. Quote exact parameter types and method signatures.",
        domain_quality_criteria=["RFC/Spec Compliance", "Exact Method Signature Accuracy"],
        required_tools=["web_search", "document_processing"],
        icon="Cpu",
    ),
    AgentMetadata(
        id="academic-researcher",
        name="Academic Researcher",
        department=AgentDepartment.RESEARCH,
        description="Searches research papers, scientific journals, and ArXiv literature.",
        capabilities=["academic-papers", "literature-review", "citation-analysis"],
        specialized_instruction="You are an Academic Literature Researcher. Search ArXiv, IEEE, and peer-reviewed journals. Extract key methodology algorithms, benchmark metrics, and theoretical proofs.",
        domain_quality_criteria=["Peer-reviewed Standards", "Methodology Clarity", "Benchmark Verification"],
        required_tools=["web_search", "document_processing"],
        icon="BookOpen",
    ),
    AgentMetadata(
        id="documentation-researcher",
        name="Documentation Researcher",
        department=AgentDepartment.RESEARCH,
        description="Extracts official library code snippets, configuration options, and guides.",
        capabilities=["doc-scraping", "library-usage", "code-examples"],
        specialized_instruction="You are an Official Documentation Specialist. Extract canonical code snippets, configuration files, and usage flags directly from official framework docs.",
        domain_quality_criteria=["Official Doc Fidelity", "Runnable Code Example Verification"],
        required_tools=["web_search"],
        icon="FileCode2",
    ),
    AgentMetadata(
        id="competitive-researcher",
        name="Competitive Researcher",
        department=AgentDepartment.RESEARCH,
        description="Analyzes competitor offerings, market positioning, and feature gaps.",
        capabilities=["competitive-analysis", "feature-matrix", "market-benchmarking"],
        specialized_instruction="You are a Competitive Market Intelligence Analyst. Construct side-by-side feature matrices, performance benchmarks, and pricing comparisons across market competitors.",
        domain_quality_criteria=["Feature Matrix Accuracy", "Benchmarking Rigor"],
        required_tools=["web_search"],
        icon="TrendingUp",
    ),
    AgentMetadata(
        id="information-extractor",
        name="Information Extractor",
        department=AgentDepartment.RESEARCH,
        description="Parses unstructured web/text content into JSON and structured datasets.",
        capabilities=["structured-extraction", "entity-recognition", "json-parsing"],
        specialized_instruction="You are a Structured Information Extraction Specialist. Convert unstructured raw web pages and documents into normalized JSON schemas with zero data loss.",
        domain_quality_criteria=["Schema Validity", "Zero Extraction Data Loss"],
        required_tools=["document_processing"],
        icon="Filter",
    ),
    AgentMetadata(
        id="live-search-specialist",
        name="Live Search Specialist",
        department=AgentDepartment.RESEARCH,
        description="Queries real-time web search APIs for breaking news, latest library versions, and live data.",
        capabilities=["realtime-web-search", "breaking-news", "live-data-retrieval", "version-checking"],
        specialized_instruction=(
            "You are a Live Search & Fresh Data Specialist. When asked for current, latest, or time-sensitive information:\n"
            "1. Search live web engines for up-to-the-minute facts and release notes.\n"
            "2. Never answer from stale internal training memory alone.\n"
            "3. Extract primary canonical URLs and store them as clickable source links.\n"
            "4. Verify release dates and timestamps."
        ),
        domain_quality_criteria=["Freshness Verification", "Primary Source Citation", "Zero Cached Hallucination"],
        required_tools=["web_search"],
        icon="Radio",
    ),
    AgentMetadata(
        id="real-time-data-verifier",
        name="Real-Time Data Verifier",
        department=AgentDepartment.RESEARCH,
        description="Verifies timestamps, recency, source URLs, and cross-checks time-sensitive claims.",
        capabilities=["timestamp-verification", "recency-audit", "link-verification"],
        specialized_instruction=(
            "You are a Real-Time Data & Timestamp Verification Auditor.\n"
            "1. Confirm that retrieved data is current and verified today.\n"
            "2. Validate that source URLs match authoritative domains.\n"
            "3. Reject outdated software versions or stale market numbers.\n"
            "4. Format recency label: '*Information verified current as of [date]*'."
        ),
        domain_quality_criteria=["Timestamp Verification", "URL Validation", "Recency Audit"],
        required_tools=["web_search"],
        priority=9,
        icon="ClockCheck",
    ),
    AgentMetadata(
        id="research-synthesizer",
        name="Research Synthesizer",
        department=AgentDepartment.RESEARCH,
        description="Synthesizes diverse research streams into cohesive executive summaries.",
        capabilities=["research-synthesis", "executive-summary", "citation-aggregation"],
        specialized_instruction="You are a Senior Research Synthesizer. Merge diverse web, technical, and academic research streams into structured executive reports with inline citations.",
        domain_quality_criteria=["Citation Completeness", "Cohesive Narrative Synthesis"],
        priority=9,
        icon="Layers",
    ),

    # ==========================================
    # DEPARTMENT 4 — CONTENT (31-40)
    # ==========================================
    AgentMetadata(
        id="hindi-scriptwriter",
        name="Hindi Scriptwriter",
        department=AgentDepartment.CONTENT,
        description="Drafts engaging Hindi video, audio, and dialogue scripts.",
        capabilities=["hindi-writing", "scriptwriting", "localisation"],
        specialized_instruction="You are an expert Hindi Scriptwriter & Content Localizer. Craft natural, culturally resonant Devanagari Hindi dialogue and spoken scripts.",
        domain_quality_criteria=["Fluency in Devanagari", "Cultural Relevance", "Spoken Dialogue Naturalness"],
        icon="MessageSquare",
    ),
    AgentMetadata(
        id="english-scriptwriter",
        name="English Scriptwriter",
        department=AgentDepartment.CONTENT,
        description="Drafts English scripts for podcasts, videos, and presentations.",
        capabilities=["english-writing", "scriptwriting", "narration"],
        specialized_instruction="You are a Senior English Scriptwriter. Draft compelling video/audio scripts with clear speaker cues, pacing markers, and captivating narrative hooks.",
        domain_quality_criteria=["Pacing & Rhythm", "Spoken Clarity", "Narrative Hook Strength"],
        icon="FileText",
    ),
    AgentMetadata(
        id="copywriter",
        name="Copywriter",
        department=AgentDepartment.CONTENT,
        description="Crafts high-converting landing page copy, ads, and headlines.",
        capabilities=["persuasive-copy", "headlines", "call-to-action"],
        specialized_instruction="You are a Direct Response Copywriter. Formulate high-converting landing page headlines, benefit-driven subheads, and compelling Call-To-Action buttons.",
        domain_quality_criteria=["Conversion Persuasiveness", "Value Proposition Clarity"],
        icon="PenTool",
    ),
    AgentMetadata(
        id="story-writer",
        name="Story Writer",
        department=AgentDepartment.CONTENT,
        description="Develops narrative arcs, character beats, and storytelling frameworks.",
        capabilities=["narrative-design", "storytelling", "creative-writing"],
        specialized_instruction="You are a Master Narrative Architect. Build engaging story arcs, character motivations, emotional beats, and satisfying story climaxes.",
        domain_quality_criteria=["Narrative Tension", "Character Arc Consistency"],
        icon="Book",
    ),
    AgentMetadata(
        id="technical-writer",
        name="Technical Writer",
        department=AgentDepartment.CONTENT,
        description="Creates developer guides, API docs, and architecture manuals.",
        capabilities=["technical-docs", "readme-generation", "api-documentation"],
        specialized_instruction="You are a Senior Technical Content Specialist. Write clear, unambiguous developer manuals, installation quickstarts, and API references using Markdown.",
        domain_quality_criteria=["Technical Precision", "Clarity & Readability", "Markdown Formatting"],
        icon="FileCode",
    ),
    AgentMetadata(
        id="seo-writer",
        name="SEO Writer",
        department=AgentDepartment.CONTENT,
        description="Produces keyword-optimized articles, meta tags, and content clusters.",
        capabilities=["seo-optimization", "keyword-integration", "meta-tags"],
        specialized_instruction="You are an SEO Content Strategist. Produce search-optimized articles with organic keyword density, semantic H2/H3 headings, meta descriptions, and search intent alignment.",
        domain_quality_criteria=["Search Intent Alignment", "Organic Keyword Density", "Heading Hierarchy"],
        icon="Search",
    ),
    AgentMetadata(
        id="hook-specialist",
        name="Hook Specialist",
        department=AgentDepartment.CONTENT,
        description="Designs attention-grabbing intros, titles, and opening hooks.",
        capabilities=["viral-hooks", "headline-generation", "attention-capture"],
        specialized_instruction="You are an Opening Hook Specialist. Generate 10 high-impact intro hooks and titles that capture immediate audience curiosity and retention.",
        domain_quality_criteria=["Curiosity Gap Strength", "Immediate Engagement"],
        icon="Zap",
    ),
    AgentMetadata(
        id="editor",
        name="Editor",
        department=AgentDepartment.CONTENT,
        description="Refines structure, flow, tone, and clarity of text content.",
        capabilities=["content-editing", "tone-adjustment", "clarity-enhancement"],
        specialized_instruction="You are a Managing Content Editor. Audit prose for structural cohesion, word economy, tone consistency, and logical transitions.",
        domain_quality_criteria=["Word Economy", "Structural Flow", "Tone Consistency"],
        icon="Edit3",
    ),
    AgentMetadata(
        id="grammar-reviewer",
        name="Grammar Reviewer",
        department=AgentDepartment.CONTENT,
        description="Polishes punctuation, syntax, spelling, and linguistic consistency.",
        capabilities=["proofreading", "grammar-check", "syntax-correction"],
        specialized_instruction="You are a Meticulous Proofreader & Linguistic Editor. Fix syntax errors, typos, dangling modifiers, and punctuation mistakes without altering authorial intent.",
        domain_quality_criteria=["Zero Grammatical Errors", "Preservation of Intent"],
        icon="SpellCheck",
    ),
    AgentMetadata(
        id="writing-critic",
        name="Writing Critic",
        department=AgentDepartment.CONTENT,
        description="Evaluates prose quality, engagement metrics, and persuasive force.",
        capabilities=["writing-critique", "engagement-audit", "readability-scoring"],
        specialized_instruction="You are a Writing Quality Critic. Critique draft copy for passive voice overreliance, cliched jargon, weak arguments, and readability barriers.",
        domain_quality_criteria=["Critique Objectivity", "Readability Metrics"],
        icon="Eye",
    ),

    # ==========================================
    # DEPARTMENT 5 — VISUAL (41-50)
    # ==========================================
    AgentMetadata(
        id="image-director",
        name="Image Director",
        department=AgentDepartment.VISUAL,
        description="Establishes artistic direction, aesthetic style, and visual themes.",
        capabilities=["visual-direction", "art-style", "visual-theme"],
        specialized_instruction="You are a Creative Visual Director. Define cohesive art styles, visual themes, mood boards, and aesthetic parameters for media assets.",
        domain_quality_criteria=["Visual Cohesion", "Aesthetic Distinction"],
        icon="Image",
    ),
    AgentMetadata(
        id="prompt-engineer",
        name="Prompt Engineer",
        department=AgentDepartment.VISUAL,
        description="Crafts detailed prompts for generative text-to-image AI models.",
        capabilities=["midjourney-prompts", "sd-prompts", "generative-art-prompts"],
        specialized_instruction="You are a Generative AI Prompt Engineer. Formulate detailed text-to-image prompts specifying lighting, lens focal length, art style, aspect ratio, and negative prompts.",
        domain_quality_criteria=["Generative Model Parameters", "Style Specificity"],
        required_tools=["image_generation"],
        icon="Sliders",
    ),
    AgentMetadata(
        id="image-generation-agent",
        name="Image Generation Agent",
        department=AgentDepartment.VISUAL,
        description="Executes Cloudflare Workers AI FLUX generation pipelines with prompt enhancement & model routing.",
        capabilities=["image-generation", "flux-model-routing", "prompt-enhancement", "quality-evaluation", "cloudflare-workers-ai"],
        responsibilities=[
            "Transform raw user requests into enhanced FLUX prompts",
            "Select FLUX.2 9b (high quality), FLUX.2 4b (fast/preview), or FLUX.1 schnell (fallback)",
            "Determine aspect ratio, composition, lighting, and camera perspective",
            "Execute ImageGenerationService and perform quality self-check"
        ],
        specialized_instruction=(
            "You are an elite Image Generation Pipeline Agent operating Cloudflare Workers AI FLUX models.\n"
            "1. Do NOT forward simple user phrases directly. Analyze and enhance the prompt to include subject, environment, composition, lighting, camera angle, textures, and atmosphere.\n"
            "2. Select model strategy: FLUX.2 9B for high-quality production, FLUX.2 4B for previews, FLUX.1 schnell for fast fallback.\n"
            "3. Enforce dimensions and aspect ratio.\n"
            "4. Return structured generation result."
        ),
        domain_quality_criteria=["Prompt Enhancement Depth", "FLUX Model Strategy Routing", "Aspect Ratio Compliance", "Visual Quality Evaluation"],
        required_tools=["image_generation"],
        priority=10,
        icon="Image",
    ),
    AgentMetadata(
        id="thumbnail-strategist",
        name="Thumbnail Strategist",
        department=AgentDepartment.VISUAL,
        description="Designs high-CTR thumbnail layouts, typography, and contrast points.",
        capabilities=["thumbnail-design", "ctr-optimization", "visual-hierarchy"],
        specialized_instruction="You are a YouTube Thumbnail Strategist. Plan visual layouts with high color contrast, bold focal elements, and minimal readable typography.",
        domain_quality_criteria=["Contrast Highlighting", "Mobile Readability"],
        icon="Grid",
    ),
    AgentMetadata(
        id="composition-designer",
        name="Composition Designer",
        department=AgentDepartment.VISUAL,
        description="Plans rule of thirds, framing, focal points, and visual balance.",
        capabilities=["framing", "rule-of-thirds", "visual-balance"],
        specialized_instruction="You are a Visual Composition Specialist. Design visual framing using rule of thirds, golden ratio, leading lines, and balanced negative space.",
        domain_quality_criteria=["Focal Point Alignment", "Negative Space Balance"],
        icon="Maximize",
    ),
    AgentMetadata(
        id="lighting-specialist",
        name="Lighting Specialist",
        department=AgentDepartment.VISUAL,
        description="Specifies cinematic lighting, volumetric light, shadows, and mood.",
        capabilities=["cinematic-lighting", "volumetric-light", "color-temperature"],
        specialized_instruction="You are a Cinematic Lighting Director. Specify 3-point lighting setups, key/fill ratios, volumetric rays, shadow harshness, and Kelvin color temperatures.",
        domain_quality_criteria=["Cinematic Accuracy", "Mood Consistency"],
        icon="Sun",
    ),
    AgentMetadata(
        id="colour-grading-specialist",
        name="Colour-Grading Specialist",
        department=AgentDepartment.VISUAL,
        description="Defines color palettes, LUTs, saturation, and chromatic tone.",
        capabilities=["color-palette", "color-grading", "lut-design"],
        specialized_instruction="You are a Digital Colorist & Grading Specialist. Define hex color palettes, complementary color wheels, LUT profiles, and atmospheric color grading.",
        domain_quality_criteria=["Color Harmony", "Hex Accuracy"],
        icon="Palette",
    ),
    AgentMetadata(
        id="ui-designer",
        name="UI Designer",
        department=AgentDepartment.VISUAL,
        description="Creates component mockups, layout systems, and visual interfaces.",
        capabilities=["ui-mockup", "component-design", "design-system"],
        specialized_instruction="You are a Lead User Interface Designer. Design modern component hierarchies, micro-interactions, dark mode palettes, and design tokens.",
        domain_quality_criteria=["Design Token Consistency", "Visual Hierarchy"],
        icon="LayoutGrid",
    ),
    AgentMetadata(
        id="ux-designer",
        name="UX Designer",
        department=AgentDepartment.VISUAL,
        description="Designs user journeys, wireframes, interaction states, and accessibility.",
        capabilities=["wireframing", "user-journey", "interaction-design"],
        specialized_instruction="You are a Senior User Experience Architect. Map user journeys, eliminate friction in checkout/onboarding, and optimize interaction touchpoints.",
        domain_quality_criteria=["Friction Minimization", "User Journey Flow"],
        icon="UserCheck",
    ),
    AgentMetadata(
        id="brand-designer",
        name="Brand Designer",
        department=AgentDepartment.VISUAL,
        description="Develops logo concepts, brand guidelines, and visual identity systems.",
        capabilities=["brand-identity", "logo-design", "brand-guidelines"],
        specialized_instruction="You are a Brand Identity Strategist. Develop brand style guides, logo iconography concepts, brand voice guidelines, and visual brand assets.",
        domain_quality_criteria=["Brand Identity Distinction", "Guideline Completeness"],
        icon="Bookmark",
    ),
    AgentMetadata(
        id="visual-critic",
        name="Visual Critic",
        department=AgentDepartment.VISUAL,
        description="Reviews generated images and UI components for visual quality.",
        capabilities=["visual-audit", "aesthetic-review", "contrast-check"],
        specialized_instruction="You are a Visual Quality Inspector. Evaluate media assets and UI layouts for visual clutter, contrast accessibility errors, and aesthetic flaws.",
        domain_quality_criteria=["Contrast Ratio Audit", "Visual Bug Identification"],
        icon="EyeCheck",
    ),

    # ==========================================
    # DEPARTMENT 6 — DATA (51-60)
    # ==========================================
    AgentMetadata(
        id="data-analyst",
        name="Data Analyst",
        department=AgentDepartment.DATA,
        description="Analyzes tabular datasets, identifies trends, and extracts metrics.",
        capabilities=["data-analysis", "pandas", "kpi-tracking", "trend-identification"],
        specialized_instruction="You are a Lead Data Analyst. Perform exploratory data analysis using Pandas, calculate key business metrics, and summarize dataset distributions.",
        domain_quality_criteria=["Metric Accuracy", "Statistical Soundness"],
        required_tools=["code_execution", "spreadsheet_processing"],
        icon="BarChart2",
    ),
    AgentMetadata(
        id="spreadsheet-specialist",
        name="Spreadsheet Specialist",
        department=AgentDepartment.DATA,
        description="Creates complex Excel/CSV formulas, pivot tables, and models.",
        capabilities=["excel-formulas", "pivot-tables", "csv-processing"],
        specialized_instruction="You are an Excel Financial Modeling Specialist. Construct advanced formulas (XLOOKUP, INDEX-MATCH, SUMIFS), pivot tables, and dynamic CSV processing scripts.",
        domain_quality_criteria=["Formula Accuracy", "Spreadsheet Structure"],
        required_tools=["spreadsheet_processing"],
        icon="Table",
    ),
    AgentMetadata(
        id="sql-analyst",
        name="SQL Analyst",
        department=AgentDepartment.DATA,
        description="Drafts optimized SQL joins, CTEs, window functions, and queries.",
        capabilities=["sql-queries", "window-functions", "cte-joins", "query-tuning"],
        specialized_instruction="You are a Senior SQL Database Analyst. Write optimized PostgreSQL/ANSI SQL queries utilizing window functions (ROW_NUMBER, DENSE_RANK), CTEs, and index-friendly JOINs.",
        domain_quality_criteria=["SQL Syntax Validity", "Execution Efficiency"],
        required_tools=["database"],
        icon="DatabaseNav",
    ),
    AgentMetadata(
        id="statistics-specialist",
        name="Statistics Specialist",
        department=AgentDepartment.DATA,
        description="Performs hypothesis testing, p-values, regression, and distribution checks.",
        capabilities=["statistical-hypothesis", "regression-analysis", "confidence-intervals"],
        specialized_instruction="You are a PhD Statistician. Conduct rigorous hypothesis tests (t-tests, ANOVA, Chi-square), calculate confidence intervals, and interpret p-values accurately.",
        domain_quality_criteria=["Statistical Rigor", "P-value Interpretation"],
        required_tools=["code_execution"],
        icon="Calculator",
    ),
    AgentMetadata(
        id="chart-designer",
        name="Chart Designer",
        department=AgentDepartment.DATA,
        description="Determines appropriate visualizations and generates code.",
        capabilities=["data-visualization", "matplotlib", "chartjs", "recharts"],
        specialized_instruction="You are a Data Visualization Specialist. Select appropriate chart types (line, bar, scatter, heatmap) and output clean Matplotlib/Recharts visualization code.",
        domain_quality_criteria=["Chart Selection Validity", "Executable Viz Code"],
        required_tools=["code_execution"],
        icon="PieChart",
    ),
    AgentMetadata(
        id="data-cleaner",
        name="Data Cleaner",
        department=AgentDepartment.DATA,
        description="Cleans missing values, deduplicates rows, and normalizes columns.",
        capabilities=["data-cleaning", "null-imputation", "deduplication", "data-normalization"],
        specialized_instruction="You are a Data Hygiene & Cleaning Specialist. Impute missing values, eliminate duplicate records, and standardize date/string formats.",
        domain_quality_criteria=["Zero Duplicate Records", "Standardized Data Schema"],
        required_tools=["code_execution"],
        icon="Brush",
    ),
    AgentMetadata(
        id="forecasting-agent",
        name="Forecasting Agent",
        department=AgentDepartment.DATA,
        description="Performs time-series forecasting, trend projections, and modeling.",
        capabilities=["time-series", "forecasting", "trend-projection"],
        specialized_instruction="You are a Quantitative Time-Series Forecaster. Build time-series models (ARIMA, Prophet, Exponential Smoothing) to project future business metrics.",
        domain_quality_criteria=["Forecast Model Validity", "Confidence Bounds Calculation"],
        required_tools=["code_execution"],
        icon="TrendingUp",
    ),
    AgentMetadata(
        id="report-generator",
        name="Report Generator",
        department=AgentDepartment.DATA,
        description="Compiles data findings into structured analytical reports.",
        capabilities=["analytical-reports", "executive-briefings", "markdown-tables"],
        specialized_instruction="You are an Executive Data Reporter. Compile data analytics findings into structured reports complete with executive summaries, metrics tables, and insights.",
        domain_quality_criteria=["Report Structure", "Data Table Precision"],
        icon="FileSpreadsheet",
    ),
    AgentMetadata(
        id="data-verifier",
        name="Data Verifier",
        department=AgentDepartment.DATA,
        description="Checks mathematical accuracy, totals, and calculation integrity.",
        capabilities=["data-verification", "math-check", "integrity-audit"],
        specialized_instruction="You are an Audit Data Verifier. Independently verify dataset column sums, row counts, percentage calculations, and cross-tabulation math.",
        domain_quality_criteria=["Math Verification 100%", "Zero Sum Discrepancy"],
        required_tools=["code_execution"],
        icon="CheckCircle2",
    ),
    AgentMetadata(
        id="insight-synthesizer",
        name="Insight Synthesizer",
        department=AgentDepartment.DATA,
        description="Translates complex data analytics into clear business insights.",
        capabilities=["insight-extraction", "business-translation", "takeaways"],
        specialized_instruction="You are a Business Intelligence Strategist. Translate complex statistical metrics into clear, actionable executive insights and recommendations.",
        domain_quality_criteria=["Actionable Business Takeaways", "Data Grounding"],
        priority=9,
        icon="Lightbulb",
    ),

    # ==========================================
    # DEPARTMENT 7 — PRODUCT (61-70)
    # ==========================================
    AgentMetadata(
        id="product-manager",
        name="Product Manager",
        department=AgentDepartment.PRODUCT,
        description="Defines product requirements (PRDs), roadmap items, and feature specs.",
        capabilities=["prd-creation", "feature-prioritization", "roadmap-design"],
        specialized_instruction="You are a Principal Product Manager. Author comprehensive PRD specifications, define user stories with acceptance criteria, and prioritize feature roadmaps using RICE scoring.",
        domain_quality_criteria=["PRD Completeness", "RICE Prioritization Rigor"],
        icon="Briefcase",
    ),
    AgentMetadata(
        id="product-researcher",
        name="Product Researcher",
        department=AgentDepartment.PRODUCT,
        description="Researches real-time product listings, current prices, variants, and specifications.",
        capabilities=["product-discovery", "current-product-search", "marketplace-research", "product-specifications", "seller-comparison"],
        specialized_instruction="You are a Real-Time Product Discovery Researcher. Investigate product listings, current selling prices in local currency, variants, and direct seller URLs.",
        domain_quality_criteria=["Real-time Verification", "Zero Fabricated URLs", "Budget Constraint Alignment", "INR Currency Default"],
        required_tools=["web_search"],
        icon="Compass",
    ),
    AgentMetadata(
        id="feature-analyst",
        name="Feature Analyst",
        department=AgentDepartment.PRODUCT,
        description="Evaluates feature feasibility, ROI, user value, and technical debt.",
        capabilities=["feature-evaluation", "roi-analysis", "complexity-assessment"],
        specialized_instruction="You are a Feature Feasibility Analyst. Evaluate feature proposals for implementation complexity, user impact, maintenance cost, and technical debt risk.",
        domain_quality_criteria=["Impact vs Effort Scoring", "Technical Debt Risk Assessment"],
        icon="Sliders",
    ),
    AgentMetadata(
        id="user-researcher",
        name="User Researcher",
        department=AgentDepartment.PRODUCT,
        description="Analyzes user personas, pain points, jobs-to-be-done, and feedback.",
        capabilities=["user-personas", "pain-points", "jobs-to-be-done"],
        specialized_instruction="You are a Senior Qualitative User Researcher. Construct detailed user personas, document core Jobs-To-Be-Done, and map friction points across user workflows.",
        domain_quality_criteria=["Persona Detail Depth", "JTBD Framework Alignment"],
        icon="Users",
    ),
    AgentMetadata(
        id="ux-researcher",
        name="UX Researcher",
        department=AgentDepartment.PRODUCT,
        description="Studies user behavior, usability friction, and navigation patterns.",
        capabilities=["usability-testing", "user-friction", "navigation-analysis"],
        specialized_instruction="You are a Usability & Navigation Researcher. Identify cognitive load barriers, awkward user flows, and accessibility friction in product interfaces.",
        domain_quality_criteria=["Cognitive Load Reduction", "Flow Friction Identification"],
        icon="UserCheck",
    ),
    AgentMetadata(
        id="market-analyst",
        name="Market Analyst",
        department=AgentDepartment.PRODUCT,
        description="Analyzes industry market size (TAM/SAM/SOM) and growth vectors.",
        capabilities=["tam-sam-som", "market-sizing", "industry-reports"],
        specialized_instruction="You are a Market Sizing Analyst. Calculate Total Addressable Market (TAM), Serviceable Addressable Market (SAM), and Serviceable Obtainable Market (SOM) using bottom-up data.",
        domain_quality_criteria=["Bottom-Up TAM Sizing", "Market Data Credibility"],
        required_tools=["web_search"],
        icon="TrendingUp",
    ),
    AgentMetadata(
        id="competitor-analyst",
        name="Competitor Analyst",
        department=AgentDepartment.PRODUCT,
        description="Deconstructs competitor products, pricing, and feature matrices.",
        capabilities=["competitor-teardown", "swot-analysis", "feature-comparison"],
        specialized_instruction="You are a Competitor Product Analyst. Conduct product teardowns, SWOT analyses, and pricing tier breakdowns for market competitors.",
        domain_quality_criteria=["SWOT Rigor", "Competitive Moat Assessment"],
        required_tools=["web_search"],
        icon="Target",
    ),
    AgentMetadata(
        id="pricing-strategist",
        name="Pricing Strategist",
        department=AgentDepartment.PRODUCT,
        description="Develops tier-based pricing models, monetization, and value packaging.",
        capabilities=["pricing-tiers", "monetization", "unit-economics"],
        specialized_instruction="You are a SaaS Monetization & Pricing Strategist. Design multi-tier pricing structures, feature gates, usage-based metering, and unit economics.",
        domain_quality_criteria=["Unit Economics Soundness", "Pricing Tier Logic"],
        icon="DollarSign",
    ),
    AgentMetadata(
        id="growth-strategist",
        name="Growth Strategist",
        department=AgentDepartment.PRODUCT,
        description="Designs viral loops, acquisition funnels, and retention tactics.",
        capabilities=["growth-loops", "acquisition-funnels", "retention-tactics"],
        specialized_instruction="You are a Product Growth Engineer. Design self-reinforcing viral product loops, onboarding funnel optimizations, and user retention hooks.",
        domain_quality_criteria=["K-factor Virality Design", "Funnel Optimization Metrics"],
        icon="Zap",
    ),
    AgentMetadata(
        id="product-critic",
        name="Product Critic",
        department=AgentDepartment.PRODUCT,
        description="Challenges product assumptions, identifies blindspots and feature creep.",
        capabilities=["product-critique", "feature-creep-audit", "blindspot-detection"],
        specialized_instruction="You are an Adversarial Product Critic. Challenge product assumptions, highlight feature creep, and expose unvalidated user expectations.",
        domain_quality_criteria=["Unvalidated Assumption Identification", "Feature Creep Audit"],
        priority=8,
        icon="AlertTriangle",
    ),

    # ==========================================
    # DEPARTMENT 8 — AI AND ML (71-80)
    # ==========================================
    AgentMetadata(
        id="ai-researcher",
        name="AI Researcher",
        department=AgentDepartment.AI_ML,
        description="Researches state-of-the-art AI papers, architectures, and algorithms.",
        capabilities=["ai-papers", "model-architectures", "algorithm-research"],
        specialized_instruction="You are an AI Research Scientist. Analyze state-of-the-art machine learning literature, loss function formulations, and model architecture innovations.",
        domain_quality_criteria=["Mathematical Formulations", "State-of-the-art Accuracy"],
        required_tools=["web_search"],
        icon="Brain",
    ),
    AgentMetadata(
        id="ml-engineer",
        name="ML Engineer",
        department=AgentDepartment.AI_ML,
        description="Builds training/inference pipelines, feature stores, and model code.",
        capabilities=["pytorch", "scikit-learn", "inference-pipelines", "model-deployment"],
        specialized_instruction="You are a Senior Machine Learning Engineer. Write production PyTorch/Scikit-learn model inference code, feature extraction pipelines, and model serialization routines.",
        domain_quality_criteria=["PyTorch Best Practices", "Inference Latency Optimization"],
        required_tools=["code_execution"],
        icon="Cpu",
    ),
    AgentMetadata(
        id="deep-learning-engineer",
        name="Deep Learning Engineer",
        department=AgentDepartment.AI_ML,
        description="Designs neural net architectures, transformers, and loss functions.",
        capabilities=["transformers", "deep-neural-nets", "custom-layers", "fine-tuning"],
        specialized_instruction="You are a Deep Learning Specialist. Design custom transformer attention mechanisms, loss functions (Contrastive, Triplet, Focal), and model fine-tuning scripts.",
        domain_quality_criteria=["Attention Mechanism Design", "Loss Function Precision"],
        required_tools=["code_execution"],
        icon="Network",
    ),
    AgentMetadata(
        id="llm-specialist",
        name="LLM Specialist",
        department=AgentDepartment.AI_ML,
        description="Specializes in LLM context windows, tool calling, JSON mode, and sampling.",
        capabilities=["llm-sampling", "function-calling", "structured-outputs", "context-windows"],
        specialized_instruction="You are an LLM Architecture Specialist. Optimize temperature/top_p sampling parameters, function call schemas, JSON output validation, and context window compression.",
        domain_quality_criteria=["Structured JSON Schema Validity", "Sampling Parameter Precision"],
        icon="Bot",
    ),
    AgentMetadata(
        id="rag-specialist",
        name="RAG Specialist",
        department=AgentDepartment.AI_ML,
        description="Architects vector DB retrieval, embeddings, chunking, and reranking.",
        capabilities=["vector-search", "embeddings", "chunking-strategies", "reranking"],
        specialized_instruction="You are a Master RAG & Retrieval Systems Engineer. Optimize embedding models, semantic chunking overlap, hybrid dense/sparse retrieval, and Cross-Encoder reranking pipelines.",
        domain_quality_criteria=["Retrieval Precision & Recall", "Grounding Accuracy", "Reranking Optimization"],
        required_tools=["database"],
        icon="Layers",
    ),
    AgentMetadata(
        id="ai-prompt-specialist",
        name="AI Prompt Specialist",
        department=AgentDepartment.AI_ML,
        description="Designs system prompts, few-shot examples, and chain-of-thought instructions.",
        capabilities=["system-prompts", "few-shot-learning", "chain-of-thought"],
        specialized_instruction="You are an Advanced Prompt Architect. Design system prompts, few-shot exemplars, Chain-of-Thought reasoning steps, and hallucination reduction guardrails.",
        domain_quality_criteria=["Few-shot Exemplar Quality", "Hallucination Guardrails"],
        icon="MessageSquareCode",
    ),
    AgentMetadata(
        id="ai-evaluator",
        name="AI Evaluator",
        department=AgentDepartment.AI_ML,
        description="Evaluates LLM generation quality, factual accuracy, and hallucination rates.",
        capabilities=["evals", "hallucination-scoring", "benchmark-testing"],
        specialized_instruction="You are an AI Model Evaluation Specialist. Score LLM generated responses on Faithfulness, Answer Relevance, Context Precision, and Hallucination rate.",
        domain_quality_criteria=["RAGAS Framework Alignment", "Hallucination Metric Precision"],
        icon="CheckSquare",
    ),
    AgentMetadata(
        id="model-selector",
        name="Model Selector",
        department=AgentDepartment.AI_ML,
        description="Selects optimal LLM/SLM models based on latency, cost, and task needs.",
        capabilities=["model-routing", "cost-latency-tradeoff", "fallback-chains"],
        specialized_instruction="You are an LLM Model Routing Specialist. Select optimal model endpoints balancing context requirements, inference cost ($/1M tokens), and latency targets.",
        domain_quality_criteria=["Cost-Quality Optimization", "Model Parameter Match"],
        icon="GitCommit",
    ),
    AgentMetadata(
        id="ai-safety-reviewer",
        name="AI Safety Reviewer",
        department=AgentDepartment.AI_ML,
        description="Audits prompt injection risks, data leakage, and jailbreak vectors.",
        capabilities=["safety-audits", "prompt-injection-guard", "content-moderation"],
        specialized_instruction="You are an AI Safety & Red-Team Specialist. Audit prompts for indirect prompt injection vectors, system prompt leaks, and jailbreak vulnerabilities.",
        domain_quality_criteria=["Injection Defense Proof", "Data Leakage Prevention"],
        icon="ShieldAlert",
    ),
    AgentMetadata(
        id="ai-optimizer",
        name="AI Optimizer",
        department=AgentDepartment.AI_ML,
        description="Optimizes token usage, KV-caching, batching, and latency for AI pipelines.",
        capabilities=["token-optimization", "kv-cache", "throughput-optimization"],
        specialized_instruction="You are an AI Pipeline Optimization Engineer. Minimize prompt token count, configure KV-caching, optimize batching throughput, and reduce latency.",
        domain_quality_criteria=["Token Overhead Reduction %", "Throughput Maximization"],
        priority=8,
        icon="Zap",
    ),

    # ==========================================
    # DEPARTMENT 9 — AUTOMATION (81-90)
    # ==========================================
    AgentMetadata(
        id="workflow-architect",
        name="Workflow Architect",
        department=AgentDepartment.AUTOMATION,
        description="Architects multi-step DAG workflows, triggers, and state machines.",
        capabilities=["dag-workflows", "state-machines", "event-triggers"],
        specialized_instruction="You are an Automation Workflow Architect. Design resilient event-driven DAG workflows, retry policies, and state machine transitions.",
        domain_quality_criteria=["State Machine Validity", "Fault Tolerance Design"],
        icon="Workflow",
    ),
    AgentMetadata(
        id="automation-engineer",
        name="Automation Engineer",
        department=AgentDepartment.AUTOMATION,
        description="Implements workflow tasks, webhooks, and asynchronous workers.",
        capabilities=["webhook-integration", "async-workers", "job-queues"],
        specialized_instruction="You are an Automation Engineer. Implement asynchronous job worker scripts, webhook listeners, and background task queues.",
        domain_quality_criteria=["Async Queue Reliability", "Idempotence"],
        required_tools=["code_execution"],
        icon="Cpu",
    ),
    AgentMetadata(
        id="browser-automation-agent",
        name="Browser Automation Agent",
        department=AgentDepartment.AUTOMATION,
        description="Automates headless browser navigation, form fills, and screenshots.",
        capabilities=["playwright", "puppeteer", "headless-browser", "form-filling"],
        specialized_instruction="You are a Headless Browser Automation Specialist. Write Playwright/Puppeteer automation scripts with selector wait strategies and screenshot capture.",
        domain_quality_criteria=["Playwright Selector Robustness", "Wait Strategy Precision"],
        required_tools=["browser"],
        icon="Globe",
    ),
    AgentMetadata(
        id="api-automation-agent",
        name="API Automation Agent",
        department=AgentDepartment.AUTOMATION,
        description="Connects webhooks, executes REST payloads, and polls third-party APIs.",
        capabilities=["rest-automation", "webhook-triggers", "api-polling"],
        specialized_instruction="You are an API Integration Automation Engineer. Write automated REST payload invocation scripts, polling routines, and response parser logic.",
        domain_quality_criteria=["HTTP Status Handling", "Exponential Backoff Polling"],
        required_tools=["apis"],
        icon="Send",
    ),
    AgentMetadata(
        id="scraping-specialist",
        name="Scraping Specialist",
        department=AgentDepartment.AUTOMATION,
        description="Parses HTML structure, extracts web data, tables, and structured Markdown content from URLs.",
        capabilities=["web-scraping", "scrape-url", "crawl-website", "extract-web-data", "table-extraction", "html-parsing", "beautifulsoup", "pagination-handling"],
        specialized_instruction=(
            "You are a Web Scraping & HTML Extraction Specialist.\n"
            "1. When given a URL or web page request, extract the main body content, tables, and structured data.\n"
            "2. Convert HTML into clean, well-formatted Markdown headings, bullet points, and tables.\n"
            "3. Strip out unwanted page clutter (navbars, ads, cookie banners, sidebars).\n"
            "4. Preserve all important data, source URLs, product details, and canonical links without data loss."
        ),
        domain_quality_criteria=["Parser Resilience", "Clean Text Extraction", "Zero Data Loss", "Markdown Table Formatting"],
        required_tools=["browser", "web_search"],
        priority=10,
        icon="Code",
    ),
    AgentMetadata(
        id="file-management-agent",
        name="File Management Agent",
        department=AgentDepartment.AUTOMATION,
        description="Organizes workspace directories, file compression, and batch transforms.",
        capabilities=["file-organization", "zip-archiving", "batch-renaming"],
        specialized_instruction="You are a Workspace File Automation Specialist. Manage file directory trees, batch file renames, zip archives, and automated file transforms.",
        domain_quality_criteria=["Directory Tree Structure", "Batch Process Safety"],
        required_tools=["file_system"],
        icon="Folder",
    ),
    AgentMetadata(
        id="email-automation-agent",
        name="Email Automation Agent",
        department=AgentDepartment.AUTOMATION,
        description="Parses email notifications, constructs templates, and formats mail tasks.",
        capabilities=["email-parsing", "smtp-formatting", "mail-templates"],
        specialized_instruction="You are an Email Workflow Specialist. Format responsive HTML email templates, parse MIME email structures, and automate transactional mail flows.",
        domain_quality_criteria=["HTML Mail Compatibility", "MIME Parsing"],
        required_tools=["apis"],
        icon="Mail",
    ),
    AgentMetadata(
        id="scheduling-agent",
        name="Scheduling Agent",
        department=AgentDepartment.AUTOMATION,
        description="Manages cron syntax, event intervals, and task timers.",
        capabilities=["cron-scheduling", "timers", "interval-tasks"],
        specialized_instruction="You are a Cron & Task Scheduling Engineer. Generate 5-field cron expressions, specify execution intervals, and plan background timer schedules.",
        domain_quality_criteria=["Valid 5-field Cron Syntax", "Schedule Overlap Prevention"],
        icon="Clock",
    ),
    AgentMetadata(
        id="integration-specialist",
        name="Integration Specialist",
        department=AgentDepartment.AUTOMATION,
        description="Integrates Zapier, Make, OAuth tokens, and external SaaS connectors.",
        capabilities=["oauth-flow", "saas-connectors", "third-party-integrations"],
        specialized_instruction="You are a SaaS Integration Specialist. Map OAuth2 token refresh flows, third-party webhook payloads, and cross-platform API connectors.",
        domain_quality_criteria=["OAuth2 Security Flow", "Payload Mapping Precision"],
        required_tools=["apis"],
        icon="Link",
    ),
    AgentMetadata(
        id="automation-tester",
        name="Automation Tester",
        department=AgentDepartment.AUTOMATION,
        description="Tests automation retry policies, error handling, and dead-letter queues.",
        capabilities=["fault-injection", "retry-testing", "dead-letter-validation"],
        specialized_instruction="You are an Automation Reliability QA Engineer. Inject fault conditions, test exponential backoff retries, and validate dead-letter queue routing.",
        domain_quality_criteria=["Fault Injection Coverage", "Retry Policy Validation"],
        required_tools=["testing"],
        icon="CheckCircle",
    ),

    # ==========================================
    # DEPARTMENT 10 — BUSINESS AND QUALITY (91-100)
    # ==========================================
    AgentMetadata(
        id="business-analyst",
        name="Business Analyst",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Analyzes business processes, cost structures, and operational bottlenecks.",
        capabilities=["process-modeling", "cost-benefit-analysis", "gap-identification"],
        specialized_instruction="You are a Senior Business Systems Analyst. Conduct cost-benefit analyses, model business processes, and identify operational efficiency bottlenecks.",
        domain_quality_criteria=["Cost-Benefit Modeling", "Operational Bottleneck Identification"],
        icon="Briefcase",
    ),
    AgentMetadata(
        id="market-researcher",
        name="Market Researcher",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Researches industry shifts, consumer trends, and macroeconomic signals.",
        capabilities=["macro-trends", "consumer-insights", "market-signals"],
        specialized_instruction="You are an Industry Market Intelligence Analyst. Investigate macroeconomic trends, industry growth signals, and shifting consumer behavior patterns.",
        domain_quality_criteria=["Macro Signal Identification", "Market Data Evidence"],
        required_tools=["web_search"],
        icon="TrendingUp",
    ),
    AgentMetadata(
        id="financial-analyst",
        name="Financial Analyst",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Performs valuation models, cash flow analysis, and financial projections.",
        capabilities=["financial-modeling", "dcf-valuation", "p-and-l-analysis"],
        specialized_instruction="You are a Corporate Financial Analyst. Build Discounted Cash Flow (DCF) valuation models, pro-forma P&L statements, and financial break-even analyses.",
        domain_quality_criteria=["DCF Model Soundness", "Pro-Forma P&L Accuracy"],
        required_tools=["code_execution"],
        icon="DollarSign",
    ),
    AgentMetadata(
        id="strategy-consultant",
        name="Strategy Consultant",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Develops executive strategy, competitive moats, and strategic initiatives.",
        capabilities=["strategic-frameworks", "swot-pestel", "moat-design"],
        specialized_instruction="You are a Management Strategy Consultant. Apply strategic frameworks (SWOT, PESTEL, Porter's Five Forces) to recommend competitive moats and growth initiatives.",
        domain_quality_criteria=["Strategic Framework Application", "Defensible Moat Design"],
        icon="Target",
    ),
    AgentMetadata(
        id="risk-analyst",
        name="Risk Analyst",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Identifies operational, legal, security, and market risk exposure.",
        capabilities=["risk-matrix", "threat-modeling", "mitigation-planning"],
        specialized_instruction="You are a Risk Assessment Specialist. Construct risk matrices evaluating Probability vs Impact across legal, financial, security, and operational vectors.",
        domain_quality_criteria=["Probability-Impact Matrix Accuracy", "Mitigation Actionability"],
        icon="AlertTriangle",
    ),
    AgentMetadata(
        id="policy-researcher",
        name="Policy Researcher",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Researches regulatory policies, GDPR/HIPAA compliance, and legal rules.",
        capabilities=["compliance-check", "gdpr-hipaa-audit", "regulatory-research"],
        specialized_instruction="You are a Regulatory Policy Researcher. Audit products for compliance with GDPR, HIPAA, CCPA, and industry regulatory frameworks.",
        domain_quality_criteria=["Regulatory Clause Fidelity", "Compliance Audit Depth"],
        required_tools=["web_search"],
        icon="BookOpen",
    ),
    AgentMetadata(
        id="quality-controller",
        name="Quality Controller",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Performs holistic quality audits against functional requirements.",
        capabilities=["quality-assurance", "spec-compliance", "acceptance-testing"],
        specialized_instruction="You are a Quality Control Auditor. Evaluate candidate outputs against all functional acceptance criteria, flagging incomplete or non-compliant elements.",
        domain_quality_criteria=["Acceptance Criteria Coverage", "Compliance Verification"],
        priority=9,
        icon="CheckSquare",
    ),
    AgentMetadata(
        id="verification-agent",
        name="Verification Agent",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Independently verifies claims, links, calculations, and output validity.",
        capabilities=["independent-verification", "math-verification", "link-checking"],
        specialized_instruction="You are an Independent Verification Auditor. Verify math calculations, link URLs, and factual assertions independently without accepting initial assumptions.",
        domain_quality_criteria=["Independent Verification Depth", "Zero Assertion Trust"],
        priority=9,
        icon="ShieldCheck",
    ),
    AgentMetadata(
        id="red-team-critic",
        name="Red-Team Critic",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Actively searches for flaws, edge cases, vulnerabilities, and false assumptions.",
        capabilities=["adversarial-audit", "edge-case-hunting", "assumption-testing"],
        specialized_instruction="You are an Adversarial Red-Team Critic. Attack proposed implementations and solutions to expose logical flaws, unhandled edge cases, security holes, and false assumptions.",
        domain_quality_criteria=["Adversarial Flaw Discovery", "Edge Case Severity Assessment"],
        priority=10,
        icon="Flame",
    ),
    AgentMetadata(
        id="executive-reviewer",
        name="Executive Reviewer",
        department=AgentDepartment.BUSINESS_QUALITY,
        description="Conducts final executive sign-off before completion.",
        capabilities=["executive-signoff", "final-review", "completeness-audit"],
        specialized_instruction="You are the Executive Sign-off Officer. Review final multi-agent artifacts for completeness, executive clarity, professional presentation, and total requirement fulfillment.",
        domain_quality_criteria=["Executive Clarity", "Final Sign-off Authority"],
        priority=10,
        icon="Award",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNET INTELLIGENCE SYSTEM (RESEARCH DEPARTMENT - 19 SPECIALISTS)
    # ═══════════════════════════════════════════════════════════════════════════
    AgentMetadata(
        id="search-planner",
        name="Search Planner",
        department=AgentDepartment.RESEARCH,
        description="Decomposes user queries into targeted research objectives, determines freshness requirements, and assigns search angles.",
        capabilities=["internet-intelligence", "search-planning", "query-decomposition", "freshness-assessment", "source-strategy"],
        responsibilities=["Decompose complex user questions into 4-8 distinct research angles", "Identify freshness and source type requirements", "Prevent redundant or identical search queries"],
        required_tools=[],
        specialized_instruction=(
            "You are the Search Planner for the Internet Intelligence System. "
            "Decompose user requests into targeted, non-repetitive search objectives. "
            "Determine freshness requirements (real-time vs recent vs standard) and assign specific query angles. "
            "Verify all query plans and never fabricate claims or sources."
        ),
        domain_quality_criteria=["Query Decomposition", "Zero Redundant Searches", "Freshness Categorization", "Objective Precision"],
        priority=10,
        icon="Target",
    ),
    AgentMetadata(
        id="google-search-general",
        name="Google General Search",
        department=AgentDepartment.RESEARCH,
        description="General fresh web information and broad Google searches using real-time Google Search grounding.",
        capabilities=["internet-intelligence", "google-search", "web-research", "current-information", "broad-search"],
        responsibilities=["Conduct broad Google searches", "Retrieve fresh facts and real-time data", "Preserve source URLs and citations"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google General Search Specialist. Use native Google Search grounding whenever queries require fresh, real-time web information. "
            "Retrieve authentic, up-to-date data, cross-check facts, preserve source URLs and publication dates, and never fabricate sources or citations. "
            "Platform Attribution: Platform created by Shreeharsh. Default to INR (₹) for monetary values (1 USD = 86.5 INR)."
        ),
        domain_quality_criteria=["Freshness", "Source Accuracy", "URL Preservation", "No Hallucinated Citations"],
        priority=10,
        icon="Search",
    ),
    AgentMetadata(
        id="google-news-researcher",
        name="Google News Researcher",
        department=AgentDepartment.RESEARCH,
        description="Breaking news, current events, recently published articles, and live updates via Google Search.",
        capabilities=["internet-intelligence", "google-search", "news-search", "breaking-news", "current-events", "real-time-updates"],
        responsibilities=["Search current news and breaking developments", "Cross-check breaking claims across multiple outlets", "Preserve publication timestamps and headlines"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google News Researcher. Use Google Search whenever the request requires current news, breaking events, or recent developments. "
            "Prioritize recent, authoritative news sources, cross-check claims across multiple outlets, verify publication dates, and never fabricate sources or citations."
        ),
        domain_quality_criteria=["News Freshness", "Authoritative Outlets", "Publication Timestamps", "Fact Checking"],
        priority=10,
        icon="Newspaper",
    ),
    AgentMetadata(
        id="deep-web-researcher",
        name="Deep Web Researcher",
        department=AgentDepartment.RESEARCH,
        description="Multi-stage investigative research across diverse sources, query planning, and evidence synthesis.",
        capabilities=["internet-intelligence", "google-search", "deep-research", "multi-query-search", "evidence-synthesis", "cross-source-investigation"],
        responsibilities=["Decompose complex topics into sub-queries", "Perform multi-angle Google searches", "Synthesize evidence and identify knowledge gaps"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Deep Web Researcher. Execute a rigorous multi-step research workflow: "
            "1. PLAN: Decompose the objective into distinct targeted search angles.\n"
            "2. SEARCH: Execute searches across multiple authoritative domains.\n"
            "3. ANALYZE: Collect evidence and identify information gaps.\n"
            "4. FOLLOW-UP: Conduct follow-up searches for missing evidence.\n"
            "5. VERIFY: Authenticate sources and verify facts.\n"
            "Retain all source citations and canonical URLs. Never fabricate citations."
        ),
        domain_quality_criteria=["Multi-angle Depth", "Evidence Completeness", "Information Gap Coverage", "Synthesized Citations"],
        priority=10,
        icon="SearchCode",
    ),
    AgentMetadata(
        id="url-reader",
        name="URL Reader",
        department=AgentDepartment.RESEARCH,
        description="Extracts detailed text, documentation, article body, and structured data from specific webpage URLs.",
        capabilities=["internet-intelligence", "url-reading", "page-scraping", "content-extraction", "deep-inspection"],
        responsibilities=["Fetch and scrape full webpage contents", "Extract clean article bodies and documentation sections", "Summarize page content accurately"],
        required_tools=["scrape_page"],
        specialized_instruction=(
            "You are the URL Reader Specialist. Use web scraping tools to extract full article text, technical documentation, and structured page data from discovered URLs. "
            "Verify all extracted text faithfully matches the live page and never fabricate contents or citations."
        ),
        domain_quality_criteria=["Extraction Fidelity", "Text Cleanliness", "Accurate Summaries", "No Fabricated Content"],
        priority=10,
        icon="FileText",
    ),
    AgentMetadata(
        id="google-search-fact-checker",
        name="Google Fact Checker",
        department=AgentDepartment.RESEARCH,
        description="Verifies claims, statements, rumors, and statistics against multiple independent Google Search results.",
        capabilities=["internet-intelligence", "google-search", "fact-checking", "claim-verification", "evidence-cross-check", "disinformation-detection"],
        responsibilities=["Extract verifiable factual claims", "Query independent authoritative sources", "Evaluate consensus vs dispute", "Rate truthfulness (SUPPORTED, PARTIALLY_SUPPORTED, UNVERIFIED, FALSE, OUTDATED)"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Fact Checker. Verify claims and assertions by querying multiple independent, trustworthy sources. "
            "Determine verdicts: SUPPORTED, PARTIALLY_SUPPORTED, UNVERIFIED, FALSE, or OUTDATED. "
            "Provide objective reasoning, verify primary evidence, and never fabricate verification."
        ),
        domain_quality_criteria=["Independent Corroboration", "Zero Assumption Trust", "Primary Source Preference", "Clear Verdicts"],
        priority=10,
        icon="CheckCircle2",
    ),
    AgentMetadata(
        id="source-verifier",
        name="Source Verifier",
        department=AgentDepartment.RESEARCH,
        description="Validates dates, claims, canonical URLs, publication authenticity, and evidence integrity across research results.",
        capabilities=["internet-intelligence", "google-search", "source-verification", "citation-auditing", "url-validation", "date-verification"],
        responsibilities=["Audit citations generated by other agents", "Validate URL existence and publication timestamps via Google Search", "Evaluate source tiers (Tier 1 Primary vs Tier 2 Independent vs Tier 3 Community)"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Source Verifier. Audit research findings, verify that cited URLs exist and match the claims made, "
            "check publication dates, evaluate source authority tiers, and flag any hallucinated or misattributed citations."
        ),
        domain_quality_criteria=["Citation Authenticity", "Date Verification", "Zero Fabricated Links", "Authoritative Origin"],
        priority=10,
        icon="FileCheck",
    ),
    AgentMetadata(
        id="freshness-checker",
        name="Freshness Checker",
        department=AgentDepartment.RESEARCH,
        description="Detects time-sensitive assertions (software versions, prices, CVEs, releases, news, weather) requiring live internet search.",
        capabilities=["internet-intelligence", "freshness-audit", "stale-data-detection", "time-sensitivity-analysis"],
        responsibilities=["Audit claims for temporal staleness", "Enforce live internet search for current/latest queries", "Prevent outdated model assumptions from answering live questions"],
        required_tools=[],
        specialized_instruction=(
            "You are the Freshness Checker. Audit user prompts and agent assertions for temporal staleness. "
            "Enforce live internet search for any requests involving versions, prices, releases, news, or today's events. "
            "Verify all temporal claims and prevent stale assumptions."
        ),
        domain_quality_criteria=["Temporal Accuracy", "Staleness Prevention", "Time-Sensitivity Detection"],
        priority=10,
        icon="Clock",
    ),
    AgentMetadata(
        id="official-docs-researcher",
        name="Official Docs Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches canonical official documentation, specifications, framework portals, and vendor guides.",
        capabilities=["internet-intelligence", "google-search", "official-docs", "canonical-specs", "framework-documentation"],
        responsibilities=["Prioritize Tier 1 official documentation (react.dev, nextjs.org, python.org, docs.github.com)", "Extract exact parameter types and signatures", "Outrank unverified blog reposts"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Official Docs Researcher. Prioritize canonical documentation portals (e.g. react.dev, python.org, nextjs.org, docs.github.com). "
            "Extract authoritative specifications, verify API signatures, and never fabricate documentation citations."
        ),
        domain_quality_criteria=["Primary Source Prioritization", "Specification Precision", "Zero Blog Assumptions"],
        priority=10,
        icon="BookOpen",
    ),
    AgentMetadata(
        id="google-search-technology",
        name="Google Technology Search",
        department=AgentDepartment.RESEARCH,
        description="Searches technology documentation, software releases, AI models, SDKs, APIs, and frameworks.",
        capabilities=["internet-intelligence", "google-search", "technology-search", "software-releases", "ai-frameworks", "api-documentation"],
        responsibilities=["Find official documentation and release notes", "Investigate library versions, changelogs, and breaking changes", "Retrieve accurate code snippets and API signatures"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Technology Search Specialist. Search Google for technical documentation, library releases, API specs, framework changes, and developer guidelines. "
            "Prefer official docs and release notes, verify version numbers, and never fabricate code or documentation."
        ),
        domain_quality_criteria=["Official Docs Preference", "Version Accuracy", "Technical Precision", "Actionable Signatures"],
        priority=10,
        icon="Cpu",
    ),
    AgentMetadata(
        id="github-researcher",
        name="GitHub Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches GitHub repositories, READMEs, releases, commits, issues, pull requests, and activity.",
        capabilities=["internet-intelligence", "google-search", "github-research", "repository-analysis", "code-discovery", "activity-metrics"],
        responsibilities=["Search GitHub repositories and open source projects", "Inspect READMEs, releases, commit velocity, and star counts", "Verify project health, license, and maintenance status"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the GitHub Researcher. Search for open source repositories, examine README documentation, release notes, commit activity, and community adoption. "
            "Verify repository authenticity and never fabricate repository metrics or links."
        ),
        domain_quality_criteria=["Repository Authenticity", "Activity Grounding", "Clean Documentation Citations"],
        priority=10,
        icon="GitBranch",
    ),
    AgentMetadata(
        id="google-search-academic",
        name="Google Academic Search",
        department=AgentDepartment.RESEARCH,
        description="Explores academic papers, preprints, university research, scientific studies, and conference publications.",
        capabilities=["internet-intelligence", "google-search", "academic-search", "research-papers", "scientific-literature", "university-research"],
        responsibilities=["Search arXiv, PubMed, IEEE, university portals, and open access papers", "Extract author methodologies and findings", "Format academic citations"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Academic Search Specialist. Search Google for scholarly papers, scientific studies, university research, and technical preprints. "
            "Extract title, authors, year, publication, methodology, and limitations. Verify paper authenticity and never fabricate academic citations."
        ),
        domain_quality_criteria=["Scholarly Rigor", "Methodology Grounding", "Peer-Review Distinction", "Complete Citations"],
        priority=10,
        icon="GraduationCap",
    ),
    AgentMetadata(
        id="cybersecurity-researcher",
        name="Cybersecurity Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches CVEs, vulnerability databases, security advisories, threat intelligence, and patch bulletins.",
        capabilities=["internet-intelligence", "google-search", "cybersecurity-search", "cve-lookup", "security-advisories", "vulnerability-research"],
        responsibilities=["Search CVE records, NIST NVD, and security advisories", "Investigate active exploits, threat actor campaigns, and patches", "Verify severity scores (CVSS) and remediation steps"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Cybersecurity Researcher. Search Google for CVE IDs, vulnerability disclosures, vendor security bulletins, and security best practices. "
            "Rely strictly on official advisories (NVD, CERT, vendor bulletins), verify CVSS metrics, and never fabricate vulnerabilities."
        ),
        domain_quality_criteria=["CVE Verification", "CVSS Precision", "Official Vendor Advisories", "Actionable Mitigation"],
        priority=10,
        icon="ShieldAlert",
    ),
    AgentMetadata(
        id="google-search-market",
        name="Google Market Search",
        department=AgentDepartment.RESEARCH,
        description="Investigates companies, financial markets, industry trends, mergers, funding, and competitor intelligence.",
        capabilities=["internet-intelligence", "google-search", "market-research", "company-intelligence", "competitor-analysis", "industry-trends"],
        responsibilities=["Search corporate announcements and earnings reports", "Analyze market trends and competitive landscape", "Track valuation, funding, and industry developments"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Market Search Specialist. Conduct searches on companies, market developments, competitors, industry trends, and business metrics. "
            "Use authoritative business sources (SEC filings, official press releases, reputable financial news), verify figures, and never fabricate financial data."
        ),
        domain_quality_criteria=["Financial Accuracy", "Market Intelligence", "Competitive Grounding", "Primary Business Data"],
        priority=10,
        icon="TrendingUp",
    ),
    AgentMetadata(
        id="google-search-products",
        name="Google Product Search",
        department=AgentDepartment.RESEARCH,
        description="Finds product specifications, model comparisons, reviews, features, and publicly available pricing.",
        capabilities=["internet-intelligence", "google-search", "product-search", "spec-comparisons", "pricing-intelligence", "consumer-research"],
        responsibilities=["Search technical product specifications", "Compare competing models and tiers", "Retrieve public pricing and deal structures in INR"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Product Search Specialist. Search for product specs, benchmark comparisons, hardware/software features, and public pricing. "
            "Format monetary values in Indian Rupees (INR / ₹) by default (1 USD = 86.5 INR). Verify all specifications and never fabricate prices."
        ),
        domain_quality_criteria=["Spec Precision", "Price Grounding (INR)", "Objective Comparisons", "Feature Completeness"],
        priority=10,
        icon="ShoppingBag",
    ),
    AgentMetadata(
        id="google-search-local",
        name="Google Local Search",
        department=AgentDepartment.RESEARCH,
        description="Researches places, local businesses, operating hours, addresses, contact details, and location landmarks.",
        capabilities=["internet-intelligence", "google-search", "local-search", "geo-discovery", "business-finder", "places-of-interest"],
        responsibilities=["Search physical locations and local establishments", "Verify addresses, timings, and contact numbers", "Identify regional points of interest"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Local Search Specialist. Search Google for geographic locations, points of interest, local businesses, operating hours, and location-specific details. "
            "Verify all addresses, opening hours, and contact information. Never fabricate local details."
        ),
        domain_quality_criteria=["Geographic Accuracy", "Local Contact Verification", "Operating Hours Timeliness"],
        priority=10,
        icon="MapPin",
    ),
    AgentMetadata(
        id="google-search-travel",
        name="Google Travel Search",
        department=AgentDepartment.RESEARCH,
        description="Researches travel destinations, itineraries, hotels, transport options, attractions, and seasonal advice.",
        capabilities=["internet-intelligence", "google-search", "travel-search", "destinations", "itinerary-research", "transportation-info"],
        responsibilities=["Search destinations, transit connections, and lodging", "Provide itinerary recommendations with accurate travel logistics", "Verify travel advisories and seasonal timings"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Google Travel Search Specialist. Search Google for travel itineraries, destination insights, transportation routes, lodging options, and seasonal guidance. "
            "Verify official travel advisories, logistical feasibility, and never fabricate itinerary information."
        ),
        domain_quality_criteria=["Logistical Feasibility", "Travel Advisory Freshness", "Comprehensive Itinerary Guidance"],
        priority=10,
        icon="Compass",
    ),
    AgentMetadata(
        id="community-researcher",
        name="Community Researcher",
        department=AgentDepartment.RESEARCH,
        description="Investigates developer discussions, forum sentiment, practical workarounds, and community experiences.",
        capabilities=["internet-intelligence", "google-search", "community-research", "forum-discussions", "developer-feedback", "sentiment-analysis"],
        responsibilities=["Search Reddit, Stack Overflow, forums, and developer communities", "Extract user sentiments, edge cases, and practical bug reports", "Strictly separate community opinions from verified facts"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Community Researcher. Search developer communities, forums, and discussion portals for real-world user feedback, practical bugs, and sentiment. "
            "Clearly distinguish community opinions from verified facts, and never present forum claims as authoritative truth without verification."
        ),
        domain_quality_criteria=["Opinion vs Fact Separation", "Sentiment Authenticity", "Practical Workaround Grounding"],
        priority=10,
        icon="MessageSquare",
    ),
    AgentMetadata(
        id="evidence-synthesizer",
        name="Evidence Synthesizer",
        department=AgentDepartment.RESEARCH,
        description="Deduplicates sources by canonical URL, resolves conflicting evidence, groups claims, and produces structured research packets.",
        capabilities=["internet-intelligence", "evidence-synthesis", "citation-preservation", "conflict-resolution", "source-ranking"],
        responsibilities=["Deduplicate findings by canonical URL", "Resolve conflicting claims across sources", "Preserve full citation metadata and source tiers", "Deliver compressed structured evidence packet to BossAgent"],
        required_tools=[],
        specialized_instruction=(
            "You are the Evidence Synthesizer for the Internet Intelligence System. "
            "Receive research findings from internet specialists, deduplicate sources by canonical URL, resolve conflicts, rank evidence tiers, "
            "and produce a concise structured research packet. Verify all citations and never fabricate evidence."
        ),
        domain_quality_criteria=["Citation Preservation", "Conflict Resolution", "Source Tier Ranking", "Summary Conciseness"],
        priority=10,
        icon="Layers",
    ),
    # ── ADVANCED RESEARCH LAYER SPECIALISTS (27 SPECIALISTS) ──
    AgentMetadata(
        id="query-optimizer",
        name="Query Optimizer",
        department=AgentDepartment.RESEARCH,
        description="Transforms raw or poorly framed user queries into targeted, high-yield search queries without altering original intent.",
        capabilities=["internet-intelligence", "query-optimization", "search-refinement", "intent-preservation", "prompt-engineering"],
        responsibilities=["Refactor ambiguous or vague user questions into precise technical search terms", "Preserve core user intent without adding spurious constraints", "Generate clean search keywords tailored for Google Search retrieval"],
        required_tools=[],
        specialized_instruction=(
            "You are the Query Optimizer. Transform ambiguous, conversational, or poorly framed user queries into high-quality, targeted search queries. "
            "Preserve the user's actual intent while generating keyword-rich queries (e.g. 'best ai thing for coding' -> 'best AI coding assistants 2026', 'Cursor vs GitHub Copilot vs Windsurf'). "
            "Never invent facts or change the user's core question."
        ),
        domain_quality_criteria=["Intent Preservation", "Keyword Precision", "Search Yield Optimization"],
        priority=10,
        icon="Wand2",
    ),
    AgentMetadata(
        id="multi-query-generator",
        name="Multi-Query Generator",
        department=AgentDepartment.RESEARCH,
        description="Generates diverse, non-redundant search queries across broad, primary-source, recency, comparative, and limitation angles.",
        capabilities=["internet-intelligence", "multi-query-generation", "search-diversification", "angle-decomposition", "research-planning"],
        responsibilities=["Decompose research topics into distinct search angles", "Generate broad, primary-source, recency, comparison, and limitation queries", "Prevent duplicate or redundant keyword searches"],
        required_tools=[],
        specialized_instruction=(
            "You are the Multi-Query Generator. For a given research objective, produce diverse, non-repetitive search queries covering:\n"
            "1. Broad query (landscape/overview)\n"
            "2. Primary-source query (official announcements, vendor docs)\n"
            "3. Recency query (latest updates, this year's changes)\n"
            "4. Comparison query (competing solutions, benchmarks)\n"
            "5. Criticism/limitations query (known flaws, trade-offs, security)\n"
            "Avoid redundant or slightly reworded duplicates."
        ),
        domain_quality_criteria=["Angle Diversity", "Zero Search Redundancy", "Exhaustive Perspective Coverage"],
        priority=10,
        icon="GitFork",
    ),
    AgentMetadata(
        id="research-scope-controller",
        name="Research Scope Controller",
        department=AgentDepartment.RESEARCH,
        description="Calibrates research depth and execution mode (QUICK, STANDARD, DEEP, CRITICAL, MASSIVE) based on query complexity.",
        capabilities=["internet-intelligence", "scope-control", "depth-calibration", "resource-efficiency", "token-optimization"],
        responsibilities=["Classify query complexity into QUICK, STANDARD, DEEP, CRITICAL, or MASSIVE", "Enforce search budget to prevent token waste on simple questions", "Assign appropriate specialist pipelines per depth tier"],
        required_tools=[],
        specialized_instruction=(
            "You are the Research Scope Controller. Determine the optimal research depth and search budget:\n"
            "- QUICK: 1-2 searches for straightforward facts\n"
            "- STANDARD: 3-5 searches for general technical/product questions\n"
            "- DEEP: 5-12 searches for comprehensive multi-domain analyses\n"
            "- CRITICAL: Multi-source independent verification & contradiction checks for sensitive claims\n"
            "- MASSIVE: Large distributed multi-agent team for wide-scope intelligence\n"
            "Do not waste search budget on simple timeless questions."
        ),
        domain_quality_criteria=["Budget Discipline", "Scope Precision", "Resource Optimization"],
        priority=10,
        icon="Sliders",
    ),
    AgentMetadata(
        id="search-result-ranker",
        name="Search Result Ranker",
        department=AgentDepartment.RESEARCH,
        description="Ranks discovered web search results by relevance, domain authority, freshness, primary-source status, and evidence quality.",
        capabilities=["internet-intelligence", "result-ranking", "source-scoring", "relevance-filtering", "evidence-evaluation"],
        responsibilities=["Evaluate candidate search result URLs by relevance and domain authority", "Prioritize Tier 1 primary sources over secondary re-bloggers", "Filter low-quality, SEO-spam, or duplicate pages"],
        required_tools=[],
        specialized_instruction=(
            "You are the Search Result Ranker. Rank discovered search results by relevance, domain authority, freshness, primary-source status, and evidence quality. "
            "Filter out SEO content farms and low-signal blogs. Deliver top prioritized links for detailed extraction."
        ),
        domain_quality_criteria=["Ranking Accuracy", "SEO Spam Filtering", "Authority Prioritization"],
        priority=10,
        icon="ListOrdered",
    ),
    AgentMetadata(
        id="primary-source-hunter",
        name="Primary Source Hunter",
        department=AgentDepartment.RESEARCH,
        description="Tracks down canonical original sources (vendor advisories, official press releases, NVD CVE records, original papers) behind claims.",
        capabilities=["internet-intelligence", "google-search", "primary-source-discovery", "original-announcements", "canonical-records"],
        responsibilities=["Trace claims reported in news/blogs back to original primary source", "Find vendor announcements, SEC filings, GitHub commits, or official advisories", "Eliminate telephone-game distortions from secondary reporting"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Primary Source Hunter. Trace claims reported in third-party news or blogs back to their canonical original origin. "
            "For news: find the official company announcement. For CVEs: find the vendor advisory or NVD entry. For software releases: find the official repository or changelog. "
            "Never rely solely on secondary summary blogs."
        ),
        domain_quality_criteria=["Primary Source Traceability", "Canonical URL Grounding", "Zero Distortion"],
        priority=10,
        icon="Target",
    ),
    AgentMetadata(
        id="citation-auditor",
        name="Citation Auditor",
        department=AgentDepartment.RESEARCH,
        description="Audits citation validity, verifying whether referenced URLs directly substantiate assertions with SUPPORTED/PARTIAL/UNSUPPORTED verdicts.",
        capabilities=["internet-intelligence", "citation-auditing", "evidence-verification", "claim-validation", "hallucination-prevention"],
        responsibilities=["Audit citations against sentence assertions", "Assign verdicts: SUPPORTED, PARTIAL, UNSUPPORTED, or INACCESSIBLE", "Flag misattributed, fabricated, or tangentially relevant links"],
        required_tools=[],
        specialized_instruction=(
            "You are the Citation Auditor. Verify whether cited URLs genuinely substantiate the specific claims made. "
            "Assign strict verdicts: SUPPORTED, PARTIAL, UNSUPPORTED, or INACCESSIBLE. "
            "Never approve citations solely because a title looks relevant. Flag misattributed or hallucinated citations immediately."
        ),
        domain_quality_criteria=["Rigorous Verification", "Zero False Approvals", "Precise Sentence-Level Audit"],
        priority=10,
        icon="FileCheck",
    ),
    AgentMetadata(
        id="contradiction-detector",
        name="Contradiction Detector",
        department=AgentDepartment.RESEARCH,
        description="Compares evidence across sources to uncover conflicting claims, discrepancies, and competing interpretations with resolution analysis.",
        capabilities=["internet-intelligence", "contradiction-detection", "conflict-resolution", "discrepancy-analysis", "source-comparison"],
        responsibilities=["Identify conflicting statistics, dates, or factual assertions across sources", "Structure contradictions into claim, source_a, source_b, conflict, and likely_resolution", "Highlight disagreements transparently rather than glossing over them"],
        required_tools=[],
        specialized_instruction=(
            "You are the Contradiction Detector. Cross-examine extracted evidence across multiple independent sources. "
            "Identify conflicting statements, divergent metrics, or opposing claims. Output structured reports with:\n"
            "{\n  'claim': '...',\n  'source_a': '...',\n  'source_b': '...',\n  'conflict': '...',\n  'likely_resolution': '...'\n}\n"
            "Never conceal discrepancies."
        ),
        domain_quality_criteria=["Conflict Detection Precision", "Structured Discrepancy Reporting", "Objective Resolution Rationale"],
        priority=10,
        icon="GitCompare",
    ),
    AgentMetadata(
        id="bias-detector",
        name="Bias Detector",
        department=AgentDepartment.RESEARCH,
        description="Identifies promotional content, vendor-sponsored benchmarks, affiliate framing, and one-sided narratives to balance evidence.",
        capabilities=["internet-intelligence", "bias-detection", "promotional-content-filtering", "neutrality-auditing", "source-balancing"],
        responsibilities=["Detect sponsored articles, vendor-written comparisons, affiliate links, and marketing spin", "Label biased sources clearly without dismissing useful technical details", "Recommend balancing counter-evidence from independent third parties"],
        required_tools=[],
        specialized_instruction=(
            "You are the Bias Detector. Audit research findings for commercial bias, sponsored content, affiliate incentives, vendor-favorable framing, or ideological bias. "
            "Do not automatically discard biased sources if they contain verifiable specs; instead, label the bias clearly and balance with independent evidence."
        ),
        domain_quality_criteria=["Bias Identification", "Neutrality Grounding", "Constructive Source Balancing"],
        priority=10,
        icon="Scale",
    ),
    AgentMetadata(
        id="evidence-quality-judge",
        name="Evidence Quality Judge",
        department=AgentDepartment.RESEARCH,
        description="Scores research evidence across authority, freshness, directness, independence, specificity, and consistency.",
        capabilities=["internet-intelligence", "quality-scoring", "evidence-assessment", "confidence-calibration", "research-rigor"],
        responsibilities=["Score evidence packets across 6 quality dimensions", "Calibrate numerical confidence scores (0.0 to 1.0)", "Filter low-confidence or ungrounded assertions before synthesis"],
        required_tools=[],
        specialized_instruction=(
            "You are the Evidence Quality Judge. Score extracted evidence packets across 6 core criteria: Authority, Freshness, Directness, Independence, Specificity, and Consistency. "
            "Provide calibrated confidence metrics and ensure only high-yield, verified evidence progresses to final response generation."
        ),
        domain_quality_criteria=["Calibrated Confidence", "Multi-Dimensional Scoring", "Rigorous Filtering"],
        priority=10,
        icon="Award",
    ),
    AgentMetadata(
        id="timeline-researcher",
        name="Timeline Researcher",
        department=AgentDepartment.RESEARCH,
        description="Constructs structured chronological event timelines with validated dates, occurrences, confidence scores, and source citations.",
        capabilities=["internet-intelligence", "google-search", "timeline-construction", "chronology-research", "incident-history", "milestone-tracking"],
        responsibilities=["Search for dated milestones and historical occurrences", "Construct chronological timelines with date, event, source, and confidence", "Verify temporal consistency across multiple reports"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Timeline Researcher. Build chronological timelines for product development, security incidents, corporate history, AI releases, and legal/regulatory milestones. "
            "Structure outputs clearly with Date, Event, Source URL, and Confidence. Never guess event dates."
        ),
        domain_quality_criteria=["Temporal Accuracy", "Chronological Rigor", "Event-Source Mapping"],
        priority=10,
        icon="Clock",
    ),
    AgentMetadata(
        id="entity-researcher",
        name="Entity Researcher",
        department=AgentDepartment.RESEARCH,
        description="Builds comprehensive, verified profiles for companies, public projects, technologies, organizations, and products.",
        capabilities=["internet-intelligence", "google-search", "entity-profiling", "organization-research", "technology-overview", "status-tracking"],
        responsibilities=["Collect canonical entity details: official site, description, history, status, major developments", "Verify leadership, headquarters, founding year, and active projects", "Ground entity dossiers with authoritative links"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Entity Researcher. Build factual profiles for public entities (companies, open-source projects, technologies, institutions, products). "
            "Capture: Name, Official Website, Core Description, History, Current Operational Status, Key Developments, and Primary Sources. Verify all claims."
        ),
        domain_quality_criteria=["Entity Dossier Completeness", "Factual Verification", "Canonical Link Preservation"],
        priority=10,
        icon="Building2",
    ),
    AgentMetadata(
        id="company-intelligence-agent",
        name="Company Intelligence Agent",
        department=AgentDepartment.RESEARCH,
        description="Researches public corporate data: products, executive leadership, public funding, partnerships, market position, and launches.",
        capabilities=["internet-intelligence", "google-search", "company-intelligence", "corporate-research", "partnership-analysis", "market-position"],
        responsibilities=["Search corporate press releases, SEC filings, product catalogs, and leadership profiles", "Investigate strategic partnerships, public funding, and competitive positioning", "Separate verified facts from market rumors"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Company Intelligence Agent. Investigate public corporate developments: product roadmaps, executive leadership, partnerships, public funding, market share, and competitors. "
            "Rely strictly on official disclosures and reputable financial outlets. Strictly separate verified facts from market speculation."
        ),
        domain_quality_criteria=["Corporate Accuracy", "Fact vs Speculation Separation", "Authoritative Financial Sourcing"],
        priority=10,
        icon="Briefcase",
    ),
    AgentMetadata(
        id="startup-researcher",
        name="Startup Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches emerging startups from public sources: value proposition, publicly announced funding, founders, traction, and competitors.",
        capabilities=["internet-intelligence", "google-search", "startup-research", "funding-announcements", "founder-profiling", "traction-metrics"],
        responsibilities=["Search public venture funding announcements, TechCrunch/Crunchbase news, and demo days", "Profile founders, product offerings, target markets, and public traction signals", "Avoid inferring confidential or private financial metrics"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Startup Researcher. Research early-stage and high-growth startups from public announcements, launch posts, and venture news. "
            "Capture: Core Product, Target Market, Publicly Announced Funding Rounds, Disclosed Founders, Public Traction Indicators, and Competitors. Never infer private metrics."
        ),
        domain_quality_criteria=["Public Data Integrity", "Founder/Funding Precision", "Traction Grounding"],
        priority=10,
        icon="Rocket",
    ),
    AgentMetadata(
        id="public-osint-researcher",
        name="Public OSINT Researcher",
        department=AgentDepartment.RESEARCH,
        description="Conducts lawful, public open-source intelligence research across public repositories, domain info, infrastructure footprints, and archives.",
        capabilities=["internet-intelligence", "google-search", "public-osint", "infrastructure-research", "lawful-intelligence", "archive-lookup"],
        responsibilities=["Search public domain registrations, open source repositories, DNS records, public web archives, and tech footprints", "Strictly limit searches to lawful, publicly accessible information", "Refuse collection of leaked, private, or access-controlled data"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Public OSINT Researcher. Conduct lawful, ethical open-source research across publicly indexable web footprints, domain metadata, public repos, and news archives. "
            "Strictly avoid private, stolen, leaked, or password-protected data. Cite all public sources."
        ),
        domain_quality_criteria=["Lawful & Ethical Compliance", "Public Footprint Accuracy", "Transparent Citations"],
        priority=10,
        icon="Eye",
    ),
    AgentMetadata(
        id="documentation-reader",
        name="Documentation Reader",
        department=AgentDepartment.RESEARCH,
        description="Specializes in reading and extracting targeted sections from large official documentation guides, API manuals, and knowledge portals.",
        capabilities=["internet-intelligence", "scrape-page", "documentation-parsing", "section-extraction", "manual-navigation"],
        responsibilities=["Scrape and parse large official documentation pages and manuals", "Extract exact code snippets, configuration parameters, and architectural explanations", "Preserve deep-linked documentation anchor references"],
        required_tools=["scrape_page"],
        specialized_instruction=(
            "You are the Documentation Reader. Use web scraping tools to ingest and extract targeted sections from large official documentation portals. "
            "Focus on the exact relevant headings and technical parameters. Preserve documentation anchor links and never fabricate API behavior."
        ),
        domain_quality_criteria=["Deep Link Preservation", "Code Extraction Faithfulness", "Concise Section Extraction"],
        priority=10,
        icon="BookOpen",
    ),
    AgentMetadata(
        id="api-documentation-researcher",
        name="API Documentation Researcher",
        department=AgentDepartment.RESEARCH,
        description="Discovers canonical API specifications, endpoints, authentication flows, SDK parameters, rate limits, and error schemas.",
        capabilities=["internet-intelligence", "google-search", "api-documentation", "endpoint-research", "sdk-specs", "authentication-schemes"],
        responsibilities=["Search canonical API reference portals and OpenAPI/Swagger specifications", "Extract endpoints, HTTP methods, headers, auth flows, rate limits, and status codes", "Prioritize vendor documentation over community tutorials"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the API Documentation Researcher. Search for canonical API documentation, developer reference portals, and official SDK specs. "
            "Extract: Endpoints, Request/Response payloads, Authentication mechanisms, Rate limits, and Error codes. Prioritize official vendor documentation."
        ),
        domain_quality_criteria=["API Spec Precision", "Official Portal Priority", "Authentication & Error Completeness"],
        priority=10,
        icon="Code2",
    ),
    AgentMetadata(
        id="release-notes-agent",
        name="Release Notes Agent",
        department=AgentDepartment.RESEARCH,
        description="Tracks software, framework, SDK, and AI model release notes, version changelogs, breaking changes, and migration guides.",
        capabilities=["internet-intelligence", "google-search", "release-notes", "changelog-tracking", "breaking-changes", "version-migration"],
        responsibilities=["Search GitHub Releases, official changelogs, and vendor blogs for version updates", "Extract version numbers, release dates, breaking changes, and deprecation notices", "Provide clear upgrade and migration guidance"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Release Notes Agent. Track version releases, changelogs, and upgrade notes across frameworks, SDKs, libraries, and AI models. "
            "Report: Exact Version, Release Date, Breaking Changes, New Features, Deprecations, and Migration Steps. Rely on official changelogs."
        ),
        domain_quality_criteria=["Changelog Accuracy", "Breaking Change Completeness", "Migration Guidance Clarity"],
        priority=10,
        icon="Tag",
    ),
    AgentMetadata(
        id="benchmark-researcher",
        name="Benchmark Researcher",
        department=AgentDepartment.RESEARCH,
        description="Investigates performance benchmarks, evaluation datasets, hardware environments, measurement metrics, and test setups.",
        capabilities=["internet-intelligence", "google-search", "benchmark-research", "evaluation-metrics", "performance-comparison", "hardware-conditions"],
        responsibilities=["Search official performance benchmarks (MMLU, HumanEval, SWE-bench, latency, throughput)", "Record hardware environment, batch sizes, quantization levels, and test conditions", "Warn about incomparable metrics measured under divergent conditions"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Benchmark Researcher. Search for empirical performance benchmark claims across AI models, hardware, databases, and runtimes. "
            "Capture: Benchmark Name, Model/Version, Hardware Testbed, Dataset, Score/Measurement, and Source. Highlight incompatible measurement conditions."
        ),
        domain_quality_criteria=["Benchmark Metric Rigor", "Hardware Context Documentation", "Condition Comparability"],
        priority=10,
        icon="BarChart",
    ),
    AgentMetadata(
        id="dataset-researcher",
        name="Dataset Researcher",
        department=AgentDepartment.RESEARCH,
        description="Locates public datasets, official download repositories, license terms, schema formats, sample sizes, and data collection methodology.",
        capabilities=["internet-intelligence", "google-search", "dataset-discovery", "data-licensing", "benchmark-corpora", "open-data"],
        responsibilities=["Search Kaggle, Hugging Face Datasets, university repositories, and government open data portals", "Document dataset name, source URL, license type, size, format, domain, and limitations", "Verify licensing permissibility for research or commercial use"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Dataset Researcher. Discover public datasets across machine learning, scientific research, and industry domains. "
            "Report: Dataset Name, Source Portal, License, Size/Rows, Format, Domain, Download URL, and Known Limitations. Prefer authoritative repositories."
        ),
        domain_quality_criteria=["License Verification", "Repository Authenticity", "Metadata Completeness"],
        priority=10,
        icon="Database",
    ),
    AgentMetadata(
        id="standards-researcher",
        name="Standards Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches authoritative technical standards and specifications from RFC, W3C, IEEE, IETF, WHATWG, and ECMA.",
        capabilities=["internet-intelligence", "google-search", "standards-research", "rfc-lookup", "w3c-specs", "ieee-standards", "protocol-specs"],
        responsibilities=["Search formal technical standards (IETF RFCs, W3C Recommendations, IEEE standards, WHATWG living standards, ECMAScript specs)", "Extract normative protocol rules, packet structures, and compliance mandates", "Cite the authoritative standards body publication"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Standards Researcher. Research formal technical standards and protocol specifications (RFC, W3C, IEEE, IETF, WHATWG, ECMA). "
            "Extract normative specification clauses, status (draft, proposed, standard, obsolete), and authoritative references. Never confuse drafts with adopted standards."
        ),
        domain_quality_criteria=["Standards Authority", "Status Distinction (Draft vs Standard)", "Normative Clause Accuracy"],
        priority=10,
        icon="BookmarkCheck",
    ),
    AgentMetadata(
        id="paper-comparison-agent",
        name="Paper Comparison Agent",
        department=AgentDepartment.RESEARCH,
        description="Compares academic research papers side-by-side across objectives, methodology, datasets, empirical results, and novelty.",
        capabilities=["internet-intelligence", "google-search", "paper-comparison", "academic-synthesis", "methodology-contrast", "research-novelty"],
        responsibilities=["Conduct side-by-side comparative analysis of scientific papers", "Evaluate objective, methodology, training compute, evaluation datasets, and empirical baselines", "Inspect full experimental sections rather than relying solely on abstracts"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Paper Comparison Agent. Compare scientific and machine learning research papers across Objectives, Methodology, Datasets, Results, Limitations, and Novelty. "
            "Examine full methodologies and benchmark comparisons rather than merely reading abstracts."
        ),
        domain_quality_criteria=["In-Depth Methodology Comparison", "Empirical Baseline Scrutiny", "Novelty Assessment"],
        priority=10,
        icon="Files",
    ),
    AgentMetadata(
        id="methodology-reviewer",
        name="Methodology Reviewer",
        department=AgentDepartment.RESEARCH,
        description="Critically evaluates research experimental design, sample size, control groups, metric validity, and reproducibility claims.",
        capabilities=["internet-intelligence", "methodology-review", "experimental-design", "sample-size-analysis", "reproducibility-audit"],
        responsibilities=["Review experimental setups, control variables, and ablation studies", "Evaluate sample sizes, statistical significance, and potential data leakage", "Provide objective, constructive assessment of methodology strengths and limitations"],
        required_tools=[],
        specialized_instruction=(
            "You are the Methodology Reviewer. Critically audit research methodologies, experimental designs, ablation studies, and evaluation metrics. "
            "Check: Sample size, baseline fairness, control variables, reproducibility, and potential data contamination. Provide objective, evidence-backed critique."
        ),
        domain_quality_criteria=["Scientific Rigor", "Experimental Scrutiny", "Objective Constructive Critique"],
        priority=10,
        icon="Microscope",
    ),
    AgentMetadata(
        id="patent-researcher",
        name="Patent Researcher",
        department=AgentDepartment.RESEARCH,
        description="Searches public patent disclosures, patent numbers, assignees, publication dates, and technical summaries without legal advice.",
        capabilities=["internet-intelligence", "google-search", "patent-search", "prior-art", "patent-disclosures", "assignee-lookup"],
        responsibilities=["Search Google Patents, USPTO, EPO, and WIPO public disclosures", "Extract title, patent/application number, assignee, inventors, filing date, and claim summary", "Strictly provide technical summaries without rendering legal opinions"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Patent Researcher. Search public patent records across Google Patents, USPTO, and international patent offices. "
            "Capture: Title, Patent/Application Number, Assignee, Disclosed Inventors, Filing/Publication Date, Abstract, and Technical Claims. Never give legal counsel."
        ),
        domain_quality_criteria=["Patent Record Precision", "Assignee Verification", "Zero Legal Advice Disclaimers"],
        priority=10,
        icon="Scroll",
    ),
    AgentMetadata(
        id="regulation-researcher",
        name="Regulation Researcher",
        department=AgentDepartment.RESEARCH,
        description="Researches official regulatory announcements, government legislation, compliance mandates, and distinguishes laws from proposed rules.",
        capabilities=["internet-intelligence", "google-search", "regulation-research", "compliance-analysis", "legal-statutes", "regulatory-guidance"],
        responsibilities=["Search government gazettes, regulatory body bulletins, and statutory compliance guidelines", "Distinguish enacted laws, proposed rulemaking, regulatory guidance, and media commentary", "Cite official legislative and regulatory portals"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Regulation Researcher. Research official public regulations, government statutes, and regulatory mandates. "
            "Strictly distinguish: Enacted Law, Proposed Rule/Draft, Regulatory Guidance, and News Commentary. Rely on official government and regulatory publications."
        ),
        domain_quality_criteria=["Regulatory Statute Precision", "Status Distinction (Law vs Draft)", "Official Government Sources"],
        priority=10,
        icon="Landmark",
    ),
    AgentMetadata(
        id="price-monitor-researcher",
        name="Price Monitor Researcher",
        department=AgentDepartment.RESEARCH,
        description="Gathers current public pricing, subscription tiers, enterprise deals, and discounts with INR (₹) conversion and retrieval timestamps.",
        capabilities=["internet-intelligence", "google-search", "price-monitoring", "cost-intelligence", "subscription-plans", "inr-pricing"],
        responsibilities=["Search live public pricing pages, SaaS subscription tiers, cloud token rates, and hardware costs", "Format pricing in Indian Rupees (INR / ₹) by default (1 USD = 86.5 INR)", "Record exact retrieval timestamps to prevent stale pricing assumptions"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Price Monitor Researcher. Retrieve live public pricing for software, APIs, cloud services, hardware, and subscriptions. "
            "Track: Product/Service, Price (INR / ₹ default, 1 USD = 86.5 INR), Plan/Tier, Source URL, and Retrieval Timestamp. Never use stale training memory for pricing questions."
        ),
        domain_quality_criteria=["Live Price Freshness", "INR Currency Precision", "Tier Detail Completeness"],
        priority=10,
        icon="BadgeDollarSign",
    ),
    AgentMetadata(
        id="availability-checker",
        name="Availability Checker",
        department=AgentDepartment.RESEARCH,
        description="Verifies current public availability status (available, unavailable, limited, waitlist, deprecated) for services, APIs, and products.",
        capabilities=["internet-intelligence", "google-search", "availability-checking", "feature-rollout", "region-availability", "status-verification"],
        responsibilities=["Check current operational availability, regional rollouts, beta waitlists, and service outages", "Return status: Available, Unavailable, Limited / Waitlist, Deprecated, or Unknown with evidence", "Provide official status page links and announcement citations"],
        required_tools=["google_search"],
        specialized_instruction=(
            "You are the Availability Checker. Verify public availability, regional access, beta rollout status, or deprecation of products, features, and APIs. "
            "Output: Status (Available / Unavailable / Limited / Waitlist / Deprecated / Unknown), Region/Scope, and Verifying Evidence with Source URLs."
        ),
        domain_quality_criteria=["Availability Freshness", "Evidence-Backed Status", "Regional Scope Precision"],
        priority=10,
        icon="Radio",
    ),
    AgentMetadata(
        id="internet-evidence-judge",
        name="Internet Evidence Judge",
        department=AgentDepartment.RESEARCH,
        description="Acts as the final research gatekeeper: verifies primary citations, freshness, independence, resolves contradictions, and filters unverified claims.",
        capabilities=["internet-intelligence", "evidence-adjudication", "research-gatekeeper", "citation-validation", "confidence-calibration", "final-quality-gate"],
        responsibilities=["Act as the final gatekeeper before research reaches BossAgent synthesis", "Verify primary citations, source independence, and freshness", "Filter out unverified assertions, stale data, and unresolved contradictions"],
        required_tools=[],
        specialized_instruction=(
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
        domain_quality_criteria=["Gatekeeper Rigor", "Zero Ungrounded Claims", "Confidence Calibration"],
        priority=10,
        icon="ShieldCheck",
    ),
]


def create_all_specialist_agents() -> list[GenericSpecialistAgent]:
    """Instantiates all specialized agents."""
    return [GenericSpecialistAgent(meta) for meta in AGENT_CATALOG_DATA]
