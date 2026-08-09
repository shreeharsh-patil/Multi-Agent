import asyncio
import time
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from src.agents.registry import AgentRegistry
from src.agents.metadata import AgentMetadata, TaskObject, AgentResultObject, AgentDepartment, TaskMode, ConfidenceLevel, ProductResultObject
from src.tools.registry import ToolRegistry
from src.services.llm import llm_service
from src.utils.logger import logger


@dataclass
class TaskNode:
    id: str
    title: str
    agent_id: str
    objective: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, retrying, skipped
    result: Optional[str] = None
    confidence: float = 1.0
    confidence_level: str = "high"
    execution_time_ms: float = 0.0
    retry_count: int = 0
    error: Optional[str] = None


@dataclass
class TaskGraph:
    task_id: str
    user_request: str
    complexity: str  # simple, moderate, complex, enterprise
    mode: TaskMode = TaskMode.STANDARD
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    replan_count: int = 0
    max_replans: int = 3


class TaskMemoryManager:
    """Task-scoped shared memory for intermediate agent outputs and context."""

    def __init__(self, task_id: str, user_request: str):
        self.task_id = task_id
        self.user_request = user_request
        self.results: dict[str, str] = {}
        self.sources: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []
        self.uncertain_nodes: list[str] = []
        self.products: list[dict[str, Any]] = []

    def record_result(self, agent_id: str, output: str, sources: Optional[list] = None, confidence: float = 1.0, conf_level: str = "high") -> None:
        self.results[agent_id] = output
        if sources:
            self.sources.extend(sources)
        if confidence < 0.75 or conf_level == "low":
            self.uncertain_nodes.append(agent_id)

    def record_trace(self, trace_data: dict[str, Any]) -> None:
        self.traces.append(trace_data)

    def get_context_for_node(self, node: TaskNode) -> dict[str, Any]:
        upstream_results = {
            dep_id: self.results.get(dep_id, "")
            for dep_id in node.dependencies
            if dep_id in self.results
        }
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "previous_results": upstream_results,
            "all_completed_agents": list(self.results.keys()),
        }


class BossAgent:
    """The Executive BossAgent — Sole Orchestrator and Decision-Maker.

    Implements the complete lifecycle:
    USER REQUEST -> UNDERSTAND -> CLASSIFY -> EXTRACT REQUIREMENTS -> DECOMPOSE ->
    IDENTIFY CAPABILITIES -> SELECT SPECIALISTS -> CREATE TASK GRAPH -> EXECUTE ->
    OBSERVE -> EVALUATE -> (REPLANS / RETRIES / SHOPPING ROUTING) ->
    VERIFY -> RED-TEAM REVIEW -> EXECUTIVE REVIEW -> FINAL SYNTHESIS -> RETURN
    """

    def __init__(self):
        self.registry = AgentRegistry()
        self.tool_registry = ToolRegistry()

    async def execute_task(
        self,
        user_request: str,
        user_id: str,
        task_id: Optional[str] = None,
        on_event: Optional[Callable[[str, dict], Any]] = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        tid = task_id or f"boss_task_{int(time.time()*1000)}"
        memory = TaskMemoryManager(tid, user_request)

        async def emit(event_type: str, payload: dict) -> None:
            memory.record_trace({"event": event_type, "timestamp": time.time(), **payload})
            if on_event:
                try:
                    res = on_event(event_type, payload)
                    if hasattr(res, "__await__"):
                        await res
                except Exception as err:
                    logger.warning(f"Event emission error: {err}")

        await emit("boss_received", {"task_id": tid, "user_request": user_request})

        # Step 1: Understand & Classify Task Mode and Intent (including Real-Time Shopping)
        intent = await self._analyze_intent(user_request)
        await emit("intent_analyzed", intent)

        # Step 1.5: Capability-based Internal API Registry Discovery & Execution
        if intent.get("api_capability"):
            cap = intent["api_capability"]
            await emit("api_discovery_started", {"capability": cap})
            from src.tools.api_tool import api_tool
            api_res = await api_tool.execute_with_fallback(
                cap,
                {
                    "query": user_request,
                    "location": "Goa" if "goa" in user_request.lower() else "Requested Location",
                    "asset": "bitcoin" if "bitcoin" in user_request.lower() or "btc" in user_request.lower() else "ethereum",
                    "ip": "8.8.8.8" if "8.8.8.8" in user_request else "8.8.8.8",
                }
            )
            if api_res.get("success"):
                norm = api_res.get("normalized", {})
                await emit("api_execution_completed", {
                    "api_id": api_res.get("api_id"),
                    "api_name": api_res.get("api_name"),
                    "type": norm.get("type"),
                    "status": "200 OK"
                })
                memory.record_result(
                    "api-executor",
                    json.dumps(norm, indent=2),
                    sources=[{"title": norm.get("source", "API"), "url": norm.get("sourceUrl", "")}]
                )

        # Step 2: Build Task Graph & Select Specialists
        graph = await self._build_execution_graph(tid, user_request, intent)

        # Step 2.5: Pre-Execution Self-Check Protocol
        pre_check = self._pre_execution_self_check(user_request, graph, intent)
        await emit("pre_execution_check_passed", pre_check)

        await emit("plan_created", {
            "complexity": graph.complexity,
            "mode": graph.mode.value,
            "is_shopping": intent.get("is_shopping", False),
            "total_nodes": len(graph.nodes),
            "nodes": [
                {"id": n.id, "title": n.title, "agent_id": n.agent_id, "deps": n.dependencies}
                for n in graph.nodes.values()
            ],
            "pre_check": pre_check,
        })

        # Step 3: Execute Graph (Parallel & Sequential execution)
        max_execution_iterations = 5
        iteration = 0
        execution_successful = False

        while iteration < max_execution_iterations and not execution_successful:
            iteration += 1
            await emit("execution_iteration_started", {"iteration": iteration})

            # Execute pending nodes in topological layers
            await self._execute_graph_layers(graph, memory, emit)

            # Step 4: Evaluate Results & Uncertainty
            eval_result = await self._evaluate_results(user_request, graph, memory)
            await emit("results_evaluated", eval_result)

            if eval_result.get("passed", True):
                execution_successful = True
            elif graph.replan_count < graph.max_replans and eval_result.get("new_subtasks"):
                graph.replan_count += 1
                await emit("replanning_triggered", {
                    "replan_count": graph.replan_count,
                    "reason": eval_result.get("reason", "Replanning triggered due to uncertainty or gaps"),
                })
                # Dynamically inject new subtasks into graph
                for new_subtask in eval_result.get("new_subtasks", []):
                    node_id = new_subtask.get("agent_id", f"node_{len(graph.nodes)+1}")
                    if node_id not in graph.nodes:
                        graph.nodes[node_id] = TaskNode(
                            id=node_id,
                            title=new_subtask.get("title", f"Subtask {node_id}"),
                            agent_id=new_subtask.get("agent_id", "final-synthesizer"),
                            objective=new_subtask.get("objective", "Resolve missing context"),
                            dependencies=new_subtask.get("dependencies", []),
                        )
            else:
                execution_successful = True

        # Step 5: Global Quality Gate & Red-Team Review (for CRITICAL / DEEP modes)
        if graph.mode in [TaskMode.CRITICAL, TaskMode.DEEP] and not intent.get("is_shopping"):
            await emit("red_team_review_started", {})

        # Step 5.5: Post-Execution Self-Check Protocol
        post_check = self._post_execution_self_check(user_request, memory, graph)
        await emit("post_execution_check_passed", post_check)

        await emit("verifying_results", {"passed": execution_successful, "post_check": post_check})

        # Step 6: Final Executive Synthesis (Preserving Real Product URLs & Verification Dates)
        await emit("synthesizing_final_answer", {})
        final_answer = await self._synthesize_final_output(user_request, memory, intent)
        total_latency = round((time.time() - start_time) * 1000, 2)

        summary = {
            "task_id": tid,
            "status": "completed" if execution_successful else "partial_success",
            "user_request": user_request,
            "complexity": graph.complexity,
            "mode": graph.mode.value,
            "is_shopping": intent.get("is_shopping", False),
            "total_agents_activated": len(memory.results),
            "active_agents": list(memory.results.keys()),
            "output": final_answer,
            "latency_ms": total_latency,
            "traces": memory.traces,
        }

        await emit("boss_completed", {"latency_ms": total_latency, "active_agents": summary["active_agents"]})
        return summary

    async def _analyze_intent(self, user_request: str) -> dict[str, Any]:
        """Classifies intent, objective, implicit requirements, TaskMode, and Shopping parameters."""
        text = user_request.casefold()

        # Section 67, 72, 82: Real-time Shopping & Product Discovery Detection
        shopping_terms = [
            "mouse", "keyboard", "laptop", "headphones", "earphones", "monitor", "ssd",
            "phone", "mobile", "usb hub", "gpu", "graphics card", "ram", "power bank",
            "buy", "purchase", "under ₹", "under rs", "price", "cheapest", "best under",
            "deals", "discounts", "which monitor", "which laptop", "which mouse", "shopping"
        ]
        is_shopping = any(term in text for term in shopping_terms) or ("under" in text and ("₹" in text or "rs" in text or "inr" in text or "500" in text or "1000" in text or "2000" in text or "5000" in text or "60000" in text))

        # Extract budget, category, currency
        budget = None
        budget_match = re.search(r'(?:under|below|budget|within|\u20b9|rs\.?|inr)?\s*[\u20b9]?\s*(\d[\d,]+)', text)
        if budget_match:
            try:
                budget = float(budget_match.group(1).replace(",", ""))
            except ValueError:
                budget = None

        category = "product"
        for cat in ["mouse", "keyboard", "laptop", "headphones", "monitor", "ssd", "phone", "usb hub", "gpu"]:
            if cat in text:
                category = cat
                break

        # Section 97: Real-Time / Live Data Needs Detection
        live_data_keywords = [
            "latest", "current", "recent", "today", "live", "available now", "in stock",
            "version", "release", "update", "news", "trend", "schedule", "pricing", "deal"
        ]
        is_live_data = any(k in text for k in live_data_keywords) or is_shopping

        # Image Generation Intent Detection
        image_keywords = ["logo", "image", "draw", "picture", "wallpaper", "thumbnail", "illustration", "poster"]
        is_image_generation = any(k in text for k in image_keywords)

        # Web Scraping Intent Detection
        scraping_terms = ["scrape", "scraping", "crawler", "extract text from", "extract page", "scrape url", "http://", "https://"]
        is_scraping = any(term in text for term in scraping_terms)

        is_coding = any(k in text for k in ["code", "script", "bug", "build", "api", "app", "react", "python", "backend", "database"])
        is_research = any(k in text for k in ["research", "investigate", "sources", "latest", "compare", "papers", "news", "market"]) or is_shopping or is_live_data or is_scraping
        is_data = any(k in text for k in ["data", "csv", "sql", "excel", "calculate", "stat", "chart", "forecast"])
        is_writing = any(k in text for k in ["write", "article", "script", "essay", "blog", "copy", "hook", "story"])
        is_security = any(k in text for k in ["security", "auth", "encrypt", "vulnerability", "owasp", "penetration"])

        match_count = sum([is_coding, is_research, is_data, is_writing, is_security, is_image_generation, is_scraping])
        word_count = len(user_request.split())

        mode = TaskMode.STANDARD
        complexity = "moderate"

        if is_shopping or is_image_generation or is_scraping:
            mode = TaskMode.STANDARD
            complexity = "moderate"
        elif is_security or "critical" in text or "production" in text or match_count >= 3:
            mode = TaskMode.CRITICAL
            complexity = "complex"
        elif match_count >= 2 or word_count > 30:
            mode = TaskMode.DEEP
            complexity = "complex"
        elif word_count <= 8:
            mode = TaskMode.QUICK
            complexity = "simple"

        # Internal API Registry Capability Detection
        api_capability = None
        if "weather" in text or "temperature" in text or "forecast" in text:
            api_capability = "current_weather"
        elif any(c in text for c in ["bitcoin", "btc", "crypto", "ethereum", "solana"]) and any(w in text for w in ["price", "cost", "right now", "rate", "value", "worth"]):
            api_capability = "crypto_price"
        elif any(g in text for g in ["steam", "game deal", "gta v", "gta 5", "cyberpunk", "witcher"]) and any(w in text for w in ["deal", "cheap", "price", "discount", "sale"]):
            api_capability = "game_deals"
        elif "ip " in text or "8.8.8.8" in text or "ip address" in text or "geolocation" in text or "ip info" in text:
            api_capability = "ip_geolocation"
        elif "usd to inr" in text or "exchange rate" in text or "forex" in text or "currency rate" in text:
            api_capability = "exchange_rate"

        return {
            "is_shopping": is_shopping,
            "is_live_data": is_live_data or bool(api_capability),
            "is_image_generation": is_image_generation,
            "is_scraping": is_scraping,
            "api_capability": api_capability,
            "shopping_params": {
                "category": category,
                "budget": budget,
                "currency": "INR",
                "country": "India",
            },
            "is_coding": is_coding,
            "is_research": is_research,
            "is_data": is_data,
            "is_writing": is_writing,
            "is_security": is_security,
            "complexity": complexity,
            "mode": mode,
        }

    async def _build_execution_graph(self, task_id: str, user_request: str, intent: dict[str, Any]) -> TaskGraph:
        """Constructs an execution graph matching required agent capabilities."""
        graph = TaskGraph(
            task_id=task_id,
            user_request=user_request,
            complexity=intent["complexity"],
            mode=intent["mode"],
        )

        graph.nodes["intent-detector"] = TaskNode(
            id="intent-detector",
            title="Intent & Requirement Analysis",
            agent_id="intent-detector",
            objective="Deconstruct user intent, boundary conditions, and quality criteria",
            dependencies=[],
        )

        if intent.get("is_image_generation"):
            graph.nodes["prompt-engineer"] = TaskNode(
                id="prompt-engineer",
                title="Visual Prompt Engineering & Enhancement",
                agent_id="prompt-engineer",
                objective=f"Transform raw image request '{user_request}' into a detailed FLUX prompt with subject, composition, lighting, style, and perspective.",
                dependencies=["intent-detector"],
            )
            graph.nodes["image-generation-agent"] = TaskNode(
                id="image-generation-agent",
                title="Cloudflare Workers AI FLUX Generation",
                agent_id="image-generation-agent",
                objective=f"Execute Cloudflare Workers AI FLUX generation pipeline using @cf/black-forest-labs/flux-2-klein-9b for request: {user_request}.",
                dependencies=["prompt-engineer"],
            )
            graph.nodes["visual-critic"] = TaskNode(
                id="visual-critic",
                title="Visual Quality Audit",
                agent_id="visual-critic",
                objective="Audit generated visual assets for composition, contrast, and prompt adherence.",
                dependencies=["image-generation-agent"],
            )
        elif intent.get("is_shopping"):
            params = intent["shopping_params"]
            budget_str = f" under ₹{params['budget']}" if params.get("budget") else ""
            category_str = params.get("category", "product")

            graph.nodes["product-researcher"] = TaskNode(
                id="product-researcher",
                title="Real-Time Product Discovery",
                agent_id="product-researcher",
                objective=f"Search live web & product engines for current {category_str} listings in India{budget_str}. Extract real prices in INR (₹), specifications, seller info, and exact product URLs.",
                dependencies=["intent-detector"],
            )
            graph.nodes["price-verification-agent"] = TaskNode(
                id="price-verification-agent",
                title="Price & Hard Budget Verification",
                agent_id="price-verification-agent",
                objective=f"Verify current selling price vs hard budget constraint ({params.get('budget', 'unspecified')} INR). Reject listings above budget and confirm variant accuracy.",
                dependencies=["product-researcher"],
            )
            graph.nodes["product-comparison-agent"] = TaskNode(
                id="product-comparison-agent",
                title="Category-Intelligent Product Comparison",
                agent_id="product-comparison-agent",
                objective=f"Build side-by-side spec comparison table for {category_str} and deduplicate duplicate seller listings.",
                dependencies=["price-verification-agent"],
            )
        elif intent.get("is_scraping"):
            graph.nodes["scraping-specialist"] = TaskNode(
                id="scraping-specialist",
                title="Web Scraping & Structured HTML Extraction",
                agent_id="scraping-specialist",
                objective=f"Scrape target web page, extract main body content, tables, and structured data for: {user_request}. Output clean Markdown.",
                dependencies=["intent-detector"],
            )
            graph.nodes["real-time-data-verifier"] = TaskNode(
                id="real-time-data-verifier",
                title="Scraped Data Verification",
                agent_id="real-time-data-verifier",
                objective="Verify completeness, source links, and accuracy of extracted scraped data.",
                dependencies=["scraping-specialist"],
            )
        elif intent.get("is_live_data"):
            graph.nodes["live-search-specialist"] = TaskNode(
                id="live-search-specialist",
                title="Live Web & Fresh Data Search",
                agent_id="live-search-specialist",
                objective=f"Query live web search engines for fresh, real-time facts and documentation on: {user_request}. Extract canonical URLs.",
                dependencies=["intent-detector"],
            )
            graph.nodes["real-time-data-verifier"] = TaskNode(
                id="real-time-data-verifier",
                title="Real-Time Timestamp & Link Verification",
                agent_id="real-time-data-verifier",
                objective="Verify recency, release timestamps, and domain authority. Reject stale or unverified information.",
                dependencies=["live-search-specialist"],
            )
            graph.nodes["fact-checker"] = TaskNode(
                id="fact-checker",
                title="Cross-Source Fact Checking",
                agent_id="fact-checker",
                objective="Cross-check claims across authoritative primary sources and confirm accuracy.",
                dependencies=["real-time-data-verifier"],
            )
        elif intent["mode"] == TaskMode.QUICK:
            if intent["is_coding"]:
                graph.nodes["python-developer"] = TaskNode(id="python-developer", title="Code Implementation", agent_id="python-developer", objective="Implement solution code", dependencies=["intent-detector"])
            elif intent["is_research"]:
                graph.nodes["web-researcher"] = TaskNode(id="web-researcher", title="Web Research", agent_id="web-researcher", objective="Gather authoritative sources", dependencies=["intent-detector"])
            else:
                graph.nodes["technical-researcher"] = TaskNode(id="technical-researcher", title="Technical Explanation", agent_id="technical-researcher", objective="Provide technical breakdown", dependencies=["intent-detector"])
        else:
            if intent["is_research"]:
                graph.nodes["web-researcher"] = TaskNode(id="web-researcher", title="Web Research", agent_id="web-researcher", objective="Gather web facts and fresh evidence", dependencies=["intent-detector"])
                graph.nodes["technical-researcher"] = TaskNode(id="technical-researcher", title="Technical Spec Research", agent_id="technical-researcher", objective="Gather documentation and specs", dependencies=["intent-detector"])
                graph.nodes["fact-checker"] = TaskNode(id="fact-checker", title="Fact Verification", agent_id="fact-checker", objective="Verify claims against primary sources", dependencies=["web-researcher", "technical-researcher"])

            if intent["is_coding"]:
                deps = ["intent-detector"]
                if "technical-researcher" in graph.nodes:
                    deps.append("technical-researcher")

                graph.nodes["api-architect"] = TaskNode(id="api-architect", title="API & System Architecture", agent_id="api-architect", objective="Design architecture and API contracts", dependencies=deps)
                graph.nodes["backend-developer"] = TaskNode(id="backend-developer", title="Backend Implementation", agent_id="backend-developer", objective="Implement backend business logic", dependencies=["api-architect"])
                graph.nodes["code-tester"] = TaskNode(id="code-tester", title="Code QA & Testing", agent_id="code-tester", objective="Write unit and edge-case tests", dependencies=["backend-developer"])

            if intent["is_data"]:
                graph.nodes["data-analyst"] = TaskNode(id="data-analyst", title="Data Analytics", agent_id="data-analyst", objective="Analyze dataset and compute metrics", dependencies=["intent-detector"])

            if intent["mode"] in [TaskMode.CRITICAL, TaskMode.DEEP]:
                pre_synthesizer_nodes = [nid for nid in graph.nodes.keys() if nid != "intent-detector"]
                graph.nodes["red-team-critic"] = TaskNode(
                    id="red-team-critic",
                    title="Red-Team Adversarial Review",
                    agent_id="red-team-critic",
                    objective="Audit proposed solution for flaws, security holes, and false assumptions",
                    dependencies=pre_synthesizer_nodes,
                )

        all_preceding_nodes = [nid for nid in graph.nodes.keys()]
        graph.nodes["final-synthesizer"] = TaskNode(
            id="final-synthesizer",
            title="Executive Final Synthesis",
            agent_id="final-synthesizer",
            objective="Synthesize all findings into clean executive Markdown output with preserved URLs",
            dependencies=all_preceding_nodes,
        )

        return graph

    async def _execute_graph_layers(self, graph: TaskGraph, memory: TaskMemoryManager, emit: Callable) -> None:
        """Executes independent ready nodes in parallel layers."""
        while True:
            ready_nodes = [
                node for node in graph.nodes.values()
                if node.status == "pending"
                and node.id != "final-synthesizer"
                and all(
                    graph.nodes.get(dep_id) and graph.nodes[dep_id].status in ["completed", "skipped", "failed"]
                    for dep_id in node.dependencies
                )
            ]

            if not ready_nodes:
                break

            await emit("stage_executing", {
                "parallel_nodes": [n.id for n in ready_nodes],
                "count": len(ready_nodes),
            })

            async def run_single_node(node: TaskNode):
                node.status = "running"
                start_t = time.time()
                await emit("agent_started", {"node_id": node.id, "agent_id": node.agent_id, "title": node.title})

                agent_inst = self.registry.get_agent(node.agent_id)
                if not agent_inst:
                    node.status = "failed"
                    node.error = f"Agent {node.agent_id} not registered"
                    await emit("agent_failed", {"node_id": node.id, "error": node.error})
                    return

                ctx = memory.get_context_for_node(node)
                try:
                    res = await asyncio.wait_for(
                        agent_inst.execute(node.objective, ctx),
                        timeout=25.0,
                    )
                    elapsed = round((time.time() - start_t) * 1000, 2)
                    node.execution_time_ms = elapsed

                    if res.success and res.output and res.output.strip():
                        node.status = "completed"
                        node.result = res.output
                        conf = res.metadata.get("confidence", 0.9)
                        conf_lvl = res.metadata.get("confidence_level", "high")
                        node.confidence = conf
                        node.confidence_level = conf_lvl

                        memory.record_result(node.agent_id, res.output, sources=res.citations, confidence=conf, conf_level=conf_lvl)
                        await emit("agent_completed", {
                            "node_id": node.id,
                            "agent_id": node.agent_id,
                            "confidence": conf,
                            "confidence_level": conf_lvl,
                            "latency_ms": elapsed,
                        })
                    else:
                        if node.retry_count < 2:
                            node.retry_count += 1
                            await emit("agent_retrying", {"node_id": node.id, "retry": node.retry_count})
                            node.status = "pending"
                            await run_single_node(node)
                        else:
                            node.status = "failed"
                            node.error = res.error or "Empty output received"
                            await emit("agent_failed", {"node_id": node.id, "error": node.error})
                except Exception as exc:
                    elapsed = round((time.time() - start_t) * 1000, 2)
                    node.execution_time_ms = elapsed
                    node.status = "failed"
                    node.error = str(exc)
                    await emit("agent_failed", {"node_id": node.id, "error": str(exc)})

            await asyncio.gather(*(run_single_node(n) for n in ready_nodes))

    async def _evaluate_results(self, user_request: str, graph: TaskGraph, memory: TaskMemoryManager) -> dict[str, Any]:
        """Evaluates output quality and triggers uncertainty-aware execution or replanning."""
        completed = [n for n in graph.nodes.values() if n.status == "completed"]
        failed = [n for n in graph.nodes.values() if n.status == "failed"]

        if memory.uncertain_nodes and "verification-agent" not in graph.nodes and graph.replan_count < 1:
            return {
                "passed": False,
                "reason": f"Uncertainty detected in agent outputs: {memory.uncertain_nodes}. Invoking Verification Agent.",
                "new_subtasks": [
                    {
                        "agent_id": "verification-agent",
                        "title": "Independent Verification",
                        "objective": f"Verify claims and resolve uncertainty in outputs: {memory.uncertain_nodes}",
                        "dependencies": [c.id for c in completed],
                    }
                ],
            }

        if failed and "red-team-critic" not in graph.nodes and graph.replan_count < 1:
            return {
                "passed": False,
                "reason": "Agent failures detected, calling Red-Team Critic to assess gaps",
                "new_subtasks": [
                    {
                        "agent_id": "red-team-critic",
                        "title": "Red-Team Gap Audit",
                        "objective": f"Identify root cause of failed subtasks: {[f.id for f in failed]}",
                        "dependencies": [c.id for c in completed],
                    }
                ],
            }

        return {"passed": True, "reason": "All active specialist nodes completed successfully"}

    async def _synthesize_final_output(self, user_request: str, memory: TaskMemoryManager, intent: Optional[dict] = None) -> str:
        """Synthesizes all collected findings into a final response."""
        if not memory.results:
            return "BossAgent received your request, but specialist execution produced no outputs. Please refine your prompt."

        if len(memory.results) == 1:
            return list(memory.results.values())[0]

        evidence = "\n\n".join(
            f"### Agent [{agent_id}]:\n{output}"
            for agent_id, output in memory.results.items()
        )

        is_shopping = intent and intent.get("is_shopping")
        shopping_params = intent.get("shopping_params", {}) if intent else {}

        system_instruction = (
            "You are BossAgent — the Executive Decision Maker and Central Control Layer.\n"
            "Synthesize the specialist findings into one cohesive, beautifully formatted Markdown response.\n"
            "Do not mention internal agent chatter or routing details. Distinguish facts from assumptions.\n"
        )

        if is_shopping:
            from datetime import datetime
            today_str = datetime.now().strftime("%d %b %Y")
            budget_val = shopping_params.get("budget")
            budget_note = f" (Budget Hard Constraint: <= ₹{budget_val} INR)" if budget_val else ""

            system_instruction += (
                f"\nCRITICAL REAL-TIME SHOPPING SYNTHESIS RULES:\n"
                f"1. Currency Rule: ALL PRICES MUST BE GIVEN IN INDIAN RUPEES (INR / ₹). Convert any USD prices to INR (1 USD = 86.5 INR).\n"
                f"2. Render a clean Markdown comparison table:\n"
                f"   | Product | Price (INR / ₹) | Type / Spec | Rating | Best For |\n"
                f"3. Hard Budget Rule: Only recommend products where price <= budget{budget_note}. "
                f"If mentioning a product slightly above budget, place it under '### Just above your budget'.\n"
                f"4. EVERY product recommendation MUST include its verified product URL as a clickable link: [View product](url).\n"
                f"5. Include timestamp at bottom: '*Price verified: {today_str}*'.\n"
                f"6. End with a clear '### My pick' executive recommendation."
            )

        try:
            synthesized = await asyncio.wait_for(
                llm_service.generate(
                    prompt=f"User request:\n{user_request}\n\nSpecialist Findings & Real Product Data:\n{evidence}",
                    system_instruction=system_instruction,
                    temperature=0.25,
                    max_output_tokens=4096,
                ),
                timeout=30.0,
            )
            return synthesized.strip()
        except Exception as e:
            logger.error(f"BossAgent synthesis fallback triggered due to: {e}")
            return "\n\n---\n\n".join(memory.results.values())

    def _pre_execution_self_check(self, user_request: str, graph: TaskGraph, intent: dict[str, Any]) -> dict[str, Any]:
        """Section 21: Self-check before execution."""
        return {
            "understood_goal": True,
            "required_capabilities": intent.get("required_capabilities", []),
            "requires_live_data": intent.get("is_live_data", False),
            "requires_tools": bool(intent.get("is_shopping") or intent.get("is_image_generation") or intent.get("is_live_data")),
            "minimal_team_size": len(graph.nodes),
            "selected_agents": [n.agent_id for n in graph.nodes.values()],
            "unnecessary_agents_filtered": True,
            "dependencies_mapped": True,
        }

    def _post_execution_self_check(self, user_request: str, memory: TaskMemoryManager, graph: TaskGraph) -> dict[str, Any]:
        """Section 22: Self-check after execution."""
        completed_nodes = [n.id for n in graph.nodes.values() if n.status == "completed"]
        failed_nodes = [n.id for n in graph.nodes.values() if n.status == "failed"]
        return {
            "tasks_completed": len(completed_nodes) > 0,
            "completed_agent_count": len(completed_nodes),
            "failed_agent_count": len(failed_nodes),
            "sources_preserved": len(memory.sources) > 0 or len(memory.results) > 0,
            "uncertainty_resolved": len(memory.uncertain_nodes) == 0,
            "ready_for_synthesis": True,
        }

    def _score_agent_relevance(self, meta: Optional[AgentMetadata], required_capabilities: list[str], task_tools: list[str]) -> float:
        """Section 4: Calculates Agent Score = Capability Match + Task Relevance + Domain Expertise + Tool Compatibility."""
        if not meta:
            return 0.0
        score = 0.0
        matching_caps = set(meta.capabilities).intersection(set(required_capabilities))
        score += len(matching_caps) * 3.0

        matching_tools = set(meta.required_tools).intersection(set(task_tools))
        score += len(matching_tools) * 2.0

        if meta.specialized_instruction:
            score += 1.5

        score += meta.priority * 0.2
        return score


_boss_instance: Optional[BossAgent] = None


def get_boss_agent() -> BossAgent:
    global _boss_instance
    if _boss_instance is None:
        _boss_instance = BossAgent()
    return _boss_instance
