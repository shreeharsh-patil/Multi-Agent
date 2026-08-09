"""The Boss Agent — executive orchestrator of the 100-worker system.

Lifecycle implemented here:

    REQUEST -> UNDERSTAND -> CLASSIFY -> DECOMPOSE -> SELECT AGENTS
             -> BUILD GRAPH -> EXECUTE (parallel waves, sequential deps)
             -> OBSERVE + EVALUATE -> (replan/retry/fallback) -> VERIFY
             -> FINAL SYNTHESIS -> RESPONSE

The Boss is deliberately LLM-driven for *thinking* (intent, decomposition,
evaluation, synthesis) but *deterministic + capability-based* for agent
selection and graph scheduling (always reproducible, cheap, and testable).

Safety rails (infinite-loop prevention / cost limits):
* max agents per task        (default 14)
* max waves / graph depth    (default 8)
* max retries per agent      (default 2)
* max alternates per subtask (default 1)
* max replan rounds          (default 2)
* hard per-agent timeout
* total token/time budget guard via config
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import traceback

from src.agentic.agents import ExecutiveRegistry
from src.agentic.core import (
    ExecutionResult,
    Subtask,
    TaskRecord,
    TaskState,
    new_task_id,
)
from src.agentic.graph import build_waves, detect_cycles, normalize_dependencies
from src.agentic.memory import TaskMemory
from src.agentic.selector import build_team_plan, model_tier_for_complexity
from src.agentic.tools import run_authorized_tool
from src.config import settings
from src.utils.logger import logger

# Shared capability vocabulary passed to the LLM so decomposition produces
# tags the capability matcher actually understands.
_CAPABILITY_HINT = re.sub(
    r"\s+", " ", " ".join(sorted({
        "code_python", "code_javascript", "code_typescript", "frontend", "react",
        "backend", "api_design", "database_design", "debugging", "testing", "security",
        "deployment", "web_search", "research", "deep_research", "technical_research",
        "academic_research", "documentation_research", "competitive_research",
        "fact_checking", "source_evaluation", "information_extraction",
        "research_synthesis", "content_writing", "scriptwriting", "copywriting",
        "storywriting", "technical_writing", "seo_writing", "hooks", "editing",
        "grammar", "critique_writing", "visual_design", "image_prompting",
        "ui_design", "ux_design", "branding", "data_analysis", "statistics", "sql",
        "spreadsheets", "chart_design", "forecasting", "reporting",
        "data_verification", "insight_synthesis", "product_strategy",
        "product_research", "user_research", "ux_research", "market_analysis",
        "competitor_analysis", "pricing", "growth", "ai_research", "ml",
        "deep_learning", "llm", "rag", "prompt_engineering", "model_evaluation",
        "model_selection", "ai_safety", "ai_optimization", "workflow_design",
        "automation", "browser_automation", "api_automation", "scraping",
        "file_management", "email_automation", "scheduling", "integrations",
        "automation_testing", "business_analysis", "market_research",
        "financial_analysis", "strategy", "risk_analysis", "policy_research",
        "quality_control", "verification", "red_team", "executive_review",
        "planning", "requirements", "synthesis",
    }))
)


class BossConfig:
    def __init__(self):
        self.max_agents = getattr(settings, "agentic_max_agents", 14)
        self.max_waves = getattr(settings, "agentic_max_waves", 8)
        self.max_retries = getattr(settings, "agentic_max_retries", 2)
        self.max_alternates = getattr(settings, "agentic_max_alternates", 1)
        self.max_replan_rounds = getattr(settings, "agentic_max_replan_rounds", 2)
        self.agent_timeout_seconds = getattr(settings, "agentic_agent_timeout_seconds", 45)
        self.think_timeout_seconds = getattr(settings, "agentic_think_timeout_seconds", 40)
        self.include_reviewers = getattr(settings, "agentic_include_reviewers", True)
        self.auto_evaluate = getattr(settings, "agentic_auto_evaluate", True)
        self.strong_synthesis = getattr(settings, "agentic_strong_synthesis", True)
        self.enabled = getattr(settings, "agentic_enabled", True)


# ---------------------------------------------------------------------------
# JSON parsing helper (tolerates markdown fences like the rest of the codebase)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start != -1 and obj_end > obj_start:
        text = text[obj_start : obj_end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        # Attempt to salvage with a JSON-ish scalar parse
        try:
            from json import loads as _loads
            data = _loads(text)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}


async def _llm(prompt: str, system: str, tokens: int = 1600, temperature: float = 0.3) -> str:
    from src.services.llm import llm_service
    return await llm_service.generate(
        prompt=prompt,
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=tokens,
    )


# ---------------------------------------------------------------------------
# Boss "thinking" phases — module-level so tests can patch them
# ---------------------------------------------------------------------------

async def analyze_request(request: str, user_context: dict) -> dict:
    """Intent analysis: objective, complexity, domains, constraints."""
    try:
        raw = await _llm(
            prompt=f"User request:\n{request}",
            system=(
                "You are the Boss Agent's intent analyzer. Analyze the user's request and return STRICT JSON only "
                "(no markdown, no commentary): {\n"
                '  "objective": "one-sentence goal",\n'
                '  "complexity": "low"|"medium"|"high"|"critical",\n'
                '  "intent_type": "informational"|"building"|"research"|"data"|"creative"|"automation"|"analysis"|"other",\n'
                '  "domains": ["coding"|"research"|"content"|"visual"|"data"|"product"|"ai_ml"|"automation"|"business"],\n'
                '  "needs_external_research": bool,\n'
                '  "needs_code": bool,\n'
                '  "needs_data_analysis": bool,\n'
                '  "needs_visual": bool,\n'
                '  "implicit_requirements": ["..."] \n'
                '  "constraints": ["cost", "tech stack", "deadlines", "privacy", ...]\n}\n'
                "Detect implicit requirements and constraints carefully."
            ),
            tokens=900,
            temperature=0.2,
        )
        data = _extract_json(raw)
        if data:
            return data
    except Exception as exc:
        logger.warning("Boss intent analysis fell back to heuristics: %s", exc)
    return _heuristic_intent(request)


_DOMAIN_HINTS = [
    ("ai_ml", ["rag", "llm", "machine learning", "neural", "model", "embedding", "ai assistant", "genai"]),
    ("coding", ["code", "app", "website", "api", "backend", "frontend", "full-stack", "script", "python", "react", "database", "debug", "build"]),
    ("research", ["research", "compare", "sources", "market trend", "latest", "current", "find", "investigate"]),
    ("data", ["data", "spreadsheet", "csv", "excel", "analy", "statistic", "chart", "forecast"]),
    ("visual", ["design", "thumbnail", "logo", "image", "ui", "brand", "poster", "visual"]),
    ("content", ["write", "script", "content", "article", "blog", "copy", "seo", "draft"]),
    ("automation", ["automate", "workflow", "scheduler", "pipeline", "integration", "cron"]),
    ("product", ["product", "feature", "roadmap", "pricing", "user", "market fit"]),
    ("business", ["business", "financial", "risk", "strategy", "market", "policy", "compliance"]),
]


def _heuristic_intent(request: str) -> dict:
    text = request.lower()
    domains = [tag for tag, keys in _DOMAIN_HINTS if any(k in text for k in keys)]
    needs_code = any(k in text for k in ["code", "app", "website", "api", "script", "python", "backend", "frontend", "debug", "build"])
    needs_research = any(k in text for k in ["research", "compare", "latest", "current", "find", "investigate", "market"])
    needs_data = any(k in text for k in ["data", "analy", "statistic", "csv", "excel", "chart", "forecast"])
    needs_visual = any(k in text for k in ["design", "thumbnail", "logo", "image", "ui", "brand", "poster"])
    keyword_count = len(domains) + int(needs_code) + int(needs_research) + int(needs_data) + int(needs_visual)
    complexity = "low" if keyword_count <= 1 else ("medium" if keyword_count <= 3 else "high")
    return {
        "objective": request,
        "complexity": complexity,
        "intent_type": "analysis" if needs_research else ("building" if needs_code else "informational"),
        "domains": domains or ["general"],
        "needs_external_research": needs_research,
        "needs_code": needs_code,
        "needs_data_analysis": needs_data,
        "needs_visual": needs_visual,
        "implicit_requirements": [],
        "constraints": [],
    }


async def decompose_request(intent: dict, request: str) -> list[dict]:
    """Convert the intent into subtasks with capabilities + dependencies."""
    try:
        raw = await _llm(
            prompt=(
                f"User request:\n{request}\n\nIntent:\n{json.dumps(intent, ensure_ascii=False)}\n\n"
                "Decompose into the smallest set of subtasks that fully fulfils the objective. "
                "Prefer a focused team: typical tasks need 2-6 subtasks, complex ones up to 8."
            ),
            system=(
                "You are the Boss Agent's task decomposer. Return STRICT JSON only: "
                '{"subtasks": [{"id": "slug", "title": "short", "description": "what to do", '
                '"required_capabilities": ["tag", ...], "dependencies": ["other ids"], "parallel": true/false}]}\n'
                "Rules: each subtask id is a unique kebab-case slug; dependencies refer to earlier "
                "subtask ids whose output this step needs; independent subtasks get parallel=true. "
                f"Use ONLY these capability tags: {_CAPABILITY_HINT}\n"
                "Never invent tags outside the list. Keep total subtasks modest."
            ),
            tokens=2000,
            temperature=0.3,
        )
        data = _extract_json(raw)
        subtasks = [s for s in data.get("subtasks", []) if isinstance(s, dict) and s.get("id")]
        if subtasks:
            return subtasks
        logger.warning("Boss decomposition returned no valid subtasks; using intent-derived fallback")
    except Exception as exc:
        logger.warning("Boss decomposition fell back to intent-derived plan: %s", exc)
    return _heuristic_subtasks(intent)


def _heuristic_subtasks(intent: dict) -> list[dict]:
    request = intent.get("objective", "")
    subtasks: list[dict] = []
    research_caps = ["web_search", "research", "research_synthesis"]

    def add(sid: str, title: str, caps: list[str], deps: list[str] | None = None) -> None:
        if sid not in {s["id"] for s in subtasks}:
            subtasks.append({
                "id": sid, "title": title, "description": _cap_topic(caps),
                "required_capabilities": caps, "dependencies": deps or [], "parallel": True,
            })

    intent_type = intent.get("intent_type", "informational")
    if intent.get("needs_external_research") or "research" in (intent.get("domains") or []):
        add("research", "Research the topic", ["web_search", "research", "source_evaluation"])
    if intent.get("needs_code") or "coding" in (intent.get("domains") or []):
        add("architecture", "Define architecture", ["planning", "api_design", "database_design"])
        add("implementation", "Implement solution", ["backend", "frontend", "code_python"])
        add("testing", "Test and harden", ["testing", "debugging", "security"])
        for dep in [["architecture"]]:
            add("implementation", "Implement solution", ["backend", "frontend", "code_python"], deps)
        subtasks[-1]["dependencies"] = ["architecture"]
        subtasks[-1]["parallel"] = False
        # testing after implementation
        for s in subtasks:
            if s["id"] == "testing":
                s["dependencies"] = ["implementation"]
        add("deployment", "Package and deploy", ["deployment", "devops"], deps=["testing"])
    if intent.get("needs_data_analysis") or "data" in (intent.get("domains") or []):
        add("data_analysis", "Analyze data", ["data_analysis", "statistics", "chart_design"])
        add("report", "Produce report", ["reporting", "insight_synthesis"], deps=["data_analysis"])
    if (intent.get("domains") or []) and "content" in intent.get("domains"):
        add("content", "Create content", ["content_writing", "scriptwriting"])
    if not subtasks:
        add("answer", "Prepare answer", ["requirements", "synthesis"])

    # assignment stage: research is parallel; dependent stages listed last & sequential
    if len(subtasks) > 1:
        for s in subtasks:
            s["parallel"] = not s.get("dependencies")
    return subtasks


def _cap_topic(caps: list[str]) -> str:
    return "Accomplish this sub-goal using the declared capabilities: " + ", ".join(caps[:6])


async def evaluate_results(request: str, objective: str, task_memory: TaskMemory) -> dict:
    """Validate the work so far; returns a verdict dict."""
    deliverables = task_memory.export()["results"]
    rendered = "\n".join(f"[{k}] {v.get('agent')}: {v.get('snippet')}" for k, v in deliverables.items()) or "(none)"
    try:
        raw = await _llm(
            prompt=f"Objective:\n{objective}\n\nSub-deliverables:\n{rendered[:12000]}",
            system=(
                "You are the Boss Agent's evaluator. Check whether the sub-deliverables fully, correctly, "
                "and coherently fulfil the objective. Return STRICT JSON only: "
                '{"verdict": "complete"|"incomplete", "confidence": 0.0-1.0, '
                '"missing": ["specific gaps"], "contradictions": ["..."], "issues": ["..."]}'
            ),
            tokens=900,
            temperature=0.2,
        )
        data = _extract_json(raw)
        return {
            "verdict": "complete" if data.get("verdict") == "complete" else "incomplete",
            "confidence": float(data.get("confidence", 0.5) or 0.5),
            "missing": data.get("missing", []) or [],
            "contradictions": data.get("contradictions", []) or [],
            "issues": data.get("issues", []) or [],
        }
    except Exception as exc:
        logger.warning("Boss evaluation unavailable: %s", exc)
        return {"verdict": "incomplete", "confidence": 0.4, "missing": [], "contradictions": [], "issues": []}


async def decide_replan(request: str, objective: str, evaluation: dict, round_no: int) -> dict:
    """Decide whether to finish, add subtasks, or assign reviewers."""
    try:
        raw = await _llm(
            prompt=(
                f"Objective: {objective}\n\nEvaluation:\n{json.dumps(evaluation, ensure_ascii=False)}\n\n"
                f"This is replan round {round_no}. Decide the next action."
            ),
            system=(
                "You are the Boss Agent's replanner. Return STRICT JSON only: "
                '{"action": "finish"|"replan"|"review", '
                '"new_subtasks": [{"id","title","description","required_capabilities":[...],"dependencies":[...]}], '
                '"note": "short justification"}\n'
                'Use "replan" only when concrete new work would materially improve the answer; '
                'use "review" to activate quality-control/verification/executive-reviewer agents for critical outputs. '
                "Return finish when the current work is sufficient or replanning would not help."
            ),
            tokens=1400,
            temperature=0.2,
        )
        data = _extract_json(raw)
        data["note"] = str(data.get("note", ""))[:500]
        data["new_subtasks"] = [s for s in data.get("new_subtasks", []) if isinstance(s, dict) and s.get("id")][:4]
        return data
    except Exception as exc:
        logger.warning("Boss replan decision unavailable: %s", exc)
        return {"action": "finish", "new_subtasks": [], "note": "Replan engine unavailable; finishing with current results."}


async def synthesize_final(request: str, objective: str, deliverables: list[dict]) -> str:
    """Final synthesis — merge worker outputs into one user-facing answer."""
    rendered = "\n\n".join(
        f"[{d.get('source')}] {d.get('agent')}:\n{d.get('result')}" for d in deliverables
    )
    try:
        return await _llm(
            prompt=f"User request:\n{request}\n\nObjective: {objective}\n\nSpecialist outputs:\n{rendered[:20000]}",
            system=(
                "You are the Boss Agent. Synthesize the specialist results into a single, coherent, "
                "well-structured answer for the user (Markdown). Remove duplication, resolve contradictions "
                "conservatively, distinguish established facts from assumptions, and preserve useful sources "
                "and implementation details. Do NOT mention agents, orchestration, or internal routing."
            ),
            tokens=4096,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("Boss final synthesis failed: %s", exc)
        return "\n\n---\n\n".join(d.get("result", "") for d in deliverables)


# ---------------------------------------------------------------------------
# Worker execution (retries + alternate fallback + timeout)
# ---------------------------------------------------------------------------

async def run_single_agent(
    agent,
    subtask: Subtask,
    task_memory: TaskMemory,
    task_id: str,
    user_id: str,
    granted_tools: list[str],
    config: BossConfig,
    on_event: object | None = None,
) -> ExecutionResult:
    """Execute one worker with timeout + retry, returning a normalized result."""
    manifest = agent.manifest
    attempts_left = config.max_retries + 1

    async def attempt() -> ExecutionResult:
        from src.agents.base import AgentTaskSpec
        previous = task_memory.previous_results(subtask.id, subtask.dependencies)
        spec = AgentTaskSpec(
            task_id=task_id,
            objective=task_memory.objective or subtask.title,
            instructions=subtask.description,
            context=task_memory.relevant_context(subtask.id, subtask.dependencies),
            dependencies=subtask.dependencies,
            previous_results=previous,
            available_tools=granted_tools,
            constraints=task_memory.constraints,
        )
        agent_context = {
            "user_id": user_id,
            "task_id": task_id,
            "subtask": subtask.id,
            "spec": spec,
            "available_tools": granted_tools,
        }
        start = time.perf_counter()
        result = await asyncio.wait_for(
            agent.execute(subtask.title, agent_context),
            timeout=config.agent_timeout_seconds,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return _from_agent_result(result, elapsed_ms)

    subtask.attempts += 1
    last_result = ExecutionResult(status=TaskState.FAILED, error="Not executed")
    first_attempt = True
    while attempts_left > 0:
        if not first_attempt:
            await _emit(on_event, "agent_retry", {"agent_id": manifest.id, "subtask_id": subtask.id, "attempt": subtask.attempts})
        first_attempt = False
        try:
            last_result = await attempt()
        except asyncio.TimeoutError:
            last_result = ExecutionResult(status=TaskState.FAILED, error=f"Timed out after {config.agent_timeout_seconds}s")
        except Exception as exc:
            last_result = ExecutionResult(status=TaskState.FAILED, error=str(exc)[:500])
        if last_result.success:
            break
        attempts_left -= 1
        subtask.status = TaskState.RETRYING
        await _emit(on_event, "agent_failed", {
            "agent_id": manifest.id, "subtask_id": subtask.id,
            "error": last_result.error, "attempts_left": attempts_left,
        })
    return last_result


def _from_agent_result(result, elapsed_ms: int) -> ExecutionResult:
    success = bool(getattr(result, "success", False))
    output = (getattr(result, "output", "") or "").strip()
    tool_calls = getattr(result, "tool_calls", []) or []
    return ExecutionResult(
        status=TaskState.COMPLETED if (success and output) else TaskState.FAILED,
        result=output,
        reasoning_summary=getattr(result, "error", "") or "",
        confidence=0.6 if (success and output) else 0.0,
        tool_calls=tool_calls,
        error="" if (success and output) else (getattr(result, "error", "") or "Agent returned empty output"),
    )


async def _emit(on_event, etype: str, data: dict) -> None:
    if on_event is None:
        return
    try:
        out = on_event(etype, data)
        if hasattr(out, "__await__"):
            await out
    except Exception as exc:
        logger.warning("Boss event emission failed for %s: %s", etype, exc)


# ---------------------------------------------------------------------------
# The Boss
# ---------------------------------------------------------------------------

class BossAgent:
    def __init__(self, config: BossConfig | None = None):
        self.config = config or BossConfig()
        self.registry = ExecutiveRegistry.get()

    async def plan(self, request, user_id="default", context=None, on_event=None) -> TaskRecord:
        """Create + plan a run without executing. REST routes call this first."""
        if not self.config.enabled:
            record = TaskRecord(id=new_task_id(), user_id=user_id, request=request)
            record.emit("task_start", {"task_id": record.id, "request": request[:200]})
            record.emit("task_error", {"error": "Agentic engine is disabled"})
            record.state = TaskState.BLOCKED
            return record

        record = TaskRecord(id=new_task_id(), user_id=user_id, request=request)
        record.emit("task_start", {"task_id": record.id, "request": request[:300]})
        await _emit(on_event, "task_start", {"task_id": record.id, "request": request[:300]})
        memory = TaskMemory(record.id, user_context=context or {})
        try:
            record.state = TaskState.QUEUED
            # 1. UNDERSTAND + CLASSIFY
            intent = await self._understand(request, record, memory, on_event)
            # 2. DECOMPOSE
            plan_subtasks_raw = await self._decompose(intent, request, record, on_event)
            # 3. SELECT AGENTS (capability-based)
            subtasks = await self._select_agents(plan_subtasks_raw, record, memory, on_event)
            # 4a. Precompute the execution graph so the UI can render waves pre-run.
            waves = build_waves([s.to_dict() for s in subtasks])
            record.waves = waves
            record.emit("graph", {"waves": waves, "node_count": len(subtasks)})
            await _emit(on_event, "graph", {"waves": waves, "node_count": len(subtasks)})
        except Exception as exc:
            record.state = TaskState.FAILED
            record.error = str(exc)[:800]
            record.emit("task_error", {"task_id": record.id, "error": record.error})
        return record

    async def run(
        self,
        request: str,
        user_id: str = "default",
        context: dict | None = None,
        on_event=None,
        record: TaskRecord | None = None,
        should_cancel=None,
    ) -> TaskRecord:
        if not self.config.enabled and record is None:
            record = TaskRecord(id=new_task_id(), user_id=user_id, request=request)
            record.emit("task_start", {"task_id": record.id, "request": request[:200]})
            record.emit("task_error", {"error": "Agentic engine is disabled"})
            record.state = TaskState.BLOCKED
            return record

        planned_here = record is None
        if record is None:
            record = await self.plan(request, user_id=user_id, context=context, on_event=on_event)
            if record.state == TaskState.BLOCKED:
                return record
        else:
            record.emit("task_start", {"task_id": record.id, "request": request[:300]})

        memory = TaskMemory(record.id, user_context=context or {})
        for brief in record.selected_agents:
            memory.store_result(brief.get("subtask_id", ""), {"agent": brief.get("name", ""), "result": "", "status": TaskState.QUEUED})

        try:
            record.state = TaskState.RUNNING
            record.started_at = time.time()
            record.emit("task_run", {"task_id": record.id})

            if planned_here or not record.subtasks:
                # No-op guard: whole complex tasks are always planned before execution.
                pass

            # 4b. BUILD GRAPH + EXECUTE (waves)
            await self._execute_graph(record.subtasks, record, memory, user_id, on_event, should_cancel=should_cancel)

            # 5. EVALUATE + REPLAN
            await self._evaluate_and_replan(request, {}, record, memory, user_id, on_event, should_cancel=should_cancel)

            # 6. FINAL SYNTHESIS
            await self._synthesize(request, record, memory, on_event)

            record.state = TaskState.COMPLETED
            await _emit(on_event, "task_complete", {"task_id": record.id, "state": record.state, "output_char_count": len(record.final_output)})
        except asyncio.CancelledError:
            record.state = TaskState.CANCELLED
            record.emit("task_cancelled", {"task_id": record.id})
            await _emit(on_event, "task_cancelled", {"task_id": record.id})
        except Exception as exc:
            record.state = TaskState.FAILED
            record.error = str(exc)[:800]
            record.emit("task_error", {"task_id": record.id, "error": record.error, "trace": traceback.format_exc(limit=5)})
            await _emit(on_event, "task_error", {"task_id": record.id, "error": record.error})
        finally:
            record.completed_at = time.time()
        return record

    # --- phase helpers -----------------------------------------------------

    async def _understand(self, request: str, record: TaskRecord, memory: TaskMemory, on_event) -> dict:
        intent = await analyze_request(request, memory.user_context)
        record.objective = str(intent.get("objective") or request)[:2000]
        record.complexity = str(intent.get("complexity") or "medium")
        record.intent_type = str(intent.get("intent_type") or "other")
        record.domains = list(intent.get("domains") or [])
        memory.objective = record.objective
        memory.constraints = list(intent.get("constraints") or [])
        memory.domains = record.domains
        record.emit("understand", {
            "objective": record.objective,
            "complexity": record.complexity,
            "intent_type": record.intent_type,
            "domains": record.domains,
            "needs_external_research": intent.get("needs_external_research"),
            "needs_code": intent.get("needs_code"),
            "needs_data_analysis": intent.get("needs_data_analysis"),
            "needs_visual": intent.get("needs_visual"),
            "constraints": memory.constraints,
        })
        await _emit(on_event, "understand", {
            "objective": record.objective, "complexity": record.complexity,
            "intent_type": record.intent_type, "domains": record.domains,
            "constraints": memory.constraints,
        })
        return intent

    async def _decompose(self, intent: dict, request: str, record: TaskRecord, on_event) -> list[dict]:
        raw = await decompose_request(intent, request)
        raw = _dedupe_subtasks(raw)
        record.emit("decompose", {"subtasks": raw})
        await _emit(on_event, "decompose", {"subtasks": raw})
        return raw

    async def _select_agents(self, raw_subtasks, record: TaskRecord, memory: TaskMemory, on_event) -> list[Subtask]:
        normalized = normalize_dependencies(raw_subtasks)
        assignments, gaps = build_team_plan(normalized)

        subtasks: list[Subtask] = []
        selected_briefs: list[dict] = []
        for raw, assignment in zip(normalized, assignments):
            subtask = Subtask(
                id=raw["id"],
                title=raw.get("title", raw["id"]),
                description=raw.get("description", ""),
                required_capabilities=list(raw.get("required_capabilities") or []),
                dependencies=list(raw.get("dependencies") or []),
                parallel=bool(raw.get("parallel", True)),
                agent_slug=assignment.get("slug", ""),
            )
            subtasks.append(subtask)
            memory.store_result(subtask.id, {"agent": assignment.get("name", ""), "result": "", "status": TaskState.QUEUED})
            brief = {
                "slug": assignment.get("slug", ""),
                "name": assignment.get("name", ""),
                "department": assignment.get("department", ""),
                "score": assignment.get("score", 0),
                "coverage": assignment.get("coverage", 0),
                "model_tier": assignment.get("model_tier", "balanced"),
                "subtask_id": subtask.id,
                "subtask_title": subtask.title,
                "available_tools": assignment.get("available_tools", []),
                "capability_gaps": assignment.get("capability_gaps", []),
            }
            selected_briefs.append(brief)

        record.selected_agents = selected_briefs
        record.emit("selected", {"agents": selected_briefs, "capability_gaps": gaps})
        await _emit(on_event, "selected", {"agents": selected_briefs, "capability_gaps": gaps})
        return subtasks

    async def _execute_graph(self, subtasks, record: TaskRecord, memory: TaskMemory, user_id, on_event, should_cancel=None) -> None:
        max_agents = int(self.config.max_agents)
        if len(subtasks) > max_agents:
            logger.warning("Boss truncated plan from %d to %d subtasks (max_agents limit)", len(subtasks), max_agents)
            subtasks = subtasks[:max_agents]

        waves = build_waves([s.to_dict() for s in subtasks])
        record.waves = waves
        record.emit("graph", {"waves": waves, "node_count": len(subtasks)})
        await _emit(on_event, "graph", {"waves": waves, "node_count": len(subtasks)})

        by_id = {s.id: s for s in subtasks}
        for index, wave in enumerate(waves[: self.config.max_waves]):
            if should_cancel and should_cancel():
                raise asyncio.CancelledError()
            record.emit("wave_start", {"wave": index, "subtasks": wave})
            await _emit(on_event, "wave_start", {"wave": index, "subtasks": wave})
            batch = [by_id[sid] for sid in wave if sid in by_id]
            results = await asyncio.gather(
                *(self._execute_subtask(s, record, memory, user_id, on_event) for s in batch),
                return_exceptions=True,
            )
            for s, r in zip(batch, results):
                if isinstance(r, Exception):
                    s.status = TaskState.FAILED
                    s.result = ExecutionResult(status=TaskState.FAILED, error=str(r)[:500])
                    record.emit("agent_failed", {"agent_id": s.agent_slug, "subtask_id": s.id, "error": str(r)[:500]})
                    await _emit(on_event, "agent_failed", {"agent_id": s.agent_slug, "subtask_id": s.id, "error": str(r)[:500]})
            record.emit("wave_complete", {"wave": index})
            await _emit(on_event, "wave_complete", {"wave": index})

    async def _execute_subtask(self, subtask, record, memory, user_id, on_event) -> None:
        if not subtask.agent_slug:
            subtask.status = TaskState.BLOCKED
            return
        manifest_brief = next(
            (a for a in record.selected_agents if a.get("slug") == subtask.agent_slug and a.get("subtask_id") == subtask.id),
            None,
        )
        granted_tools = (manifest_brief or {}).get("available_tools", [])
        agent = self.registry.get_agent(subtask.agent_slug)
        if agent is None:
            subtask.status = TaskState.BLOCKED
            record.agent_calls += 1
            return

        subtask.status = TaskState.RUNNING
        record.emit("agent_start", {"agent_id": agent.manifest.id, "name": agent.manifest.name, "subtask_id": subtask.id, "title": subtask.title, "tools": granted_tools})
        await _emit(on_event, "agent_start", {"agent_id": agent.manifest.id, "name": agent.manifest.name, "subtask_id": subtask.id, "title": subtask.title, "tools": granted_tools})

        result = await run_single_agent(
            agent, subtask, memory, record.id, user_id, granted_tools,
            self.config, on_event,
        )
        final_agent_name = agent.manifest.name

        # Alternate fallback: pick the next-best configured worker for this subtask.
        if not result.success and self.config.max_alternates > 0:
            alt = self._alternate_for(subtask, exclude={subtask.agent_slug})
            if alt:
                previous = subtask.agent_slug
                subtask.agent_slug = alt.manifest.id
                final_agent_name = alt.manifest.name
                subtask.status = TaskState.RETRYING
                record.emit("agent_fallback", {"agent_id": previous, "replacement": alt.manifest.id, "subtask_id": subtask.id})
                await _emit(on_event, "agent_fallback", {"agent_id": previous, "replacement": alt.manifest.id, "subtask_id": subtask.id})
                result = await run_single_agent(
                    alt, subtask, memory, record.id, user_id, granted_tools,
                    self.config, on_event,
                )

        subtask.result = result
        subtask.status = result.status
        record.agent_calls += subtask.attempts

        if result.success:
            memory.store_result(subtask.id, {
                "agent": final_agent_name,
                "result": result.result,
                "confidence": result.confidence,
                "status": TaskState.COMPLETED,
            })
            await _emit(on_event, "agent_complete", {
                "agent_id": subtask.agent_slug, "name": final_agent_name, "subtask_id": subtask.id,
                "status": TaskState.COMPLETED, "confidence": result.confidence,
                "snippet": (result.result or "")[:160],
            })
        else:
            record.emit("agent_failed", {"agent_id": subtask.agent_slug, "subtask_id": subtask.id, "error": result.error})
            await _emit(on_event, "agent_failed", {
                "agent_id": subtask.agent_slug, "subtask_id": subtask.id,
                "error": result.error, "final": True,
            })
            memory.store_result(subtask.id, {
                "agent": final_agent_name, "result": "", "status": TaskState.FAILED, "error": result.error,
            })

    def _alternate_for(self, subtask, exclude: set[str]):
        from src.agentic.selector import select_agent_for_subtask
        from src.agentic.agents import ExecutiveRegistry as _Registry
        chosen = select_agent_for_subtask(subtask, registry=_Registry.get(), exclude=exclude)
        if chosen.get("found"):
            return _Registry.get().get_agent(chosen["slug"])
        return None

    async def _evaluate_and_replan(self, request, intent: dict, record: TaskRecord, memory: TaskMemory, user_id, on_event, should_cancel=None) -> None:
        if not self.config.auto_evaluate or not self.config.include_reviewers:
            return
        if not any(s.result.success for s in record.subtasks):
            return

        if should_cancel and should_cancel():
            raise asyncio.CancelledError()

        evaluation = await evaluate_results(request, record.objective, memory)
        record.emit("evaluate", evaluation)
        await _emit(on_event, "evaluate", evaluation)

        if evaluation.get("verdict") == "complete" and float(evaluation.get("confidence") or 0) >= 0.55:
            return
        if record.replan_count >= self.config.max_replan_rounds:
            return

        if should_cancel and should_cancel():
            raise asyncio.CancelledError()

        decision = await decide_replan(request, record.objective, evaluation, record.replan_count + 1)
        action = decision.get("action", "finish")
        record.emit("replan", {"round": record.replan_count + 1, "action": action, "note": decision.get("note", ""), "new_subtasks": decision.get("new_subtasks", [])})
        await _emit(on_event, "replan", {
            "round": record.replan_count + 1, "action": action, "note": decision.get("note", ""),
            "new_subtasks": decision.get("new_subtasks", []),
        })

        if action == "replan" and decision.get("new_subtasks"):
            record.replan_count += 1
            new_plan = decision.get("new_subtasks", [])
            added_subtasks = await self._add_subtasks(record, memory, new_plan, on_event)
            await self._execute_graph(added_subtasks, record, memory, user_id, on_event, should_cancel=should_cancel)
        elif action == "review":
            record.replan_count += 1
            await self._add_reviewers(record, memory, on_event)
            await self._execute_graph(record.subtasks[-3:], record, memory, user_id, on_event, should_cancel=should_cancel)

    async def _add_subtasks(self, record, memory, new_plan, on_event) -> list[Subtask]:
        existing_ids = {s.id for s in record.subtasks}
        additions: list[Subtask] = []
        for raw in new_plan:
            sid = raw.get("id")
            if not sid or sid in existing_ids:
                continue
            raw["dependencies"] = [d for d in (raw.get("dependencies") or []) if d in existing_ids]
            subtask = Subtask(
                id=sid, title=raw.get("title", sid), description=raw.get("description", ""),
                required_capabilities=list(raw.get("required_capabilities") or []),
                dependencies=list(raw.get("dependencies") or []),
                parallel=bool(raw.get("parallel", True)),
            )
            assignment = _single_assignment(subtask.required_capabilities, exclude={x.agent_slug for x in record.subtasks})
            subtask.agent_slug = assignment.get("slug", "")
            record.subtasks.append(subtask)
            additions.append(subtask)
            record.selected_agents.append({
                "slug": assignment.get("slug", ""), "name": assignment.get("name", ""),
                "department": assignment.get("department", ""), "score": assignment.get("score", 0),
                "model_tier": assignment.get("model_tier", "balanced"),
                "subtask_id": subtask.id, "subtask_title": subtask.title,
                "available_tools": assignment.get("available_tools", []),
                "capability_gaps": assignment.get("capability_gaps", []),
            })
            memory.store_result(subtask.id, {"agent": assignment.get("name", ""), "result": "", "status": TaskState.QUEUED})
        return additions

    async def _add_reviewers(self, record, memory, on_event) -> None:
        review_slugs = ["quality-controller", "verification-agent", "executive-reviewer"]
        cutoff = _critical(record)  # only critical tasks get all three reviewers
        picked = review_slugs if cutoff else review_slugs[:2]
        existing_used = {s.agent_slug for s in record.subtasks}
        for slug in picked:
            if slug in existing_used:
                continue
            agent = self.registry.get_agent(slug)
            if not agent:
                continue
            sid = f"review-{slug}"
            subtask = Subtask(
                id=sid, title=f"{agent.manifest.name} review",
                description=("Verify the assembled deliverable for correctness, completeness, and coherence; return structured issues."),
                required_capabilities=agent.manifest.capabilities[:3],
                dependencies=[s.id for s in record.subtasks if s.result.success],
                parallel=True,
                agent_slug=slug,
            )
            record.subtasks.append(subtask)
            record.selected_agents.append({
                "slug": slug, "name": agent.manifest.name, "department": agent.manifest.department,
                "score": 98, "model_tier": agent.manifest.model_tier,
                "subtask_id": sid, "subtask_title": subtask.title,
                "available_tools": [t for t in agent.manifest.optional_tools],
                "capability_gaps": [],
            })
            memory.store_result(sid, {"agent": agent.manifest.name, "result": "", "status": TaskState.QUEUED})

    async def _synthesize(self, request, record: TaskRecord, memory: TaskMemory, on_event) -> None:
        deliverables = [
            {
                "source": s.id,
                "agent": next((a.get("name", "") for a in record.selected_agents if a.get("slug") == s.agent_slug), s.agent_slug),
                "result": s.result.result or "",
            }
            for s in record.subtasks
            if s.result.success and (s.result.result or "").strip()
        ]
        record.emit("synthesize", {"selected_count": len(deliverables)})
        await _emit(on_event, "synthesize", {"selected_count": len(deliverables)})
        objective = record.objective or request
        if not deliverables:
            record.final_output = "The Boss Agent could not produce a verified answer from the selected specialists."
            return
        if len(deliverables) == 1 and not self.config.strong_synthesis:
            record.final_output = deliverables[0]["result"]
            return
        record.final_output = (await synthesize_final(request, objective, deliverables)).strip()


def intents_for_replan(intent: dict) -> dict:
    """Small accessor used by replan stages; keeps signature explicit."""
    return intent


def _single_assignment(required_caps: list[str], exclude: set[str]) -> dict:
    from src.agentic.selector import select_agent_for_subtask

    class _Mini:
        required_capabilities = required_caps
        dependencies = []

    return select_agent_for_subtask(_Mini(), exclude=exclude)


def _critical(record: TaskRecord) -> bool:
    return record.complexity in {"high", "critical"}


def _dedupe_subtasks(subtasks: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for s in subtasks:
        sid = s.get("id", "")
        if not sid:
            continue
        if sid not in seen:
            seen[sid] = s
        else:
            # Merge small capabilities from duplicate into first occurrence
            existing = seen[sid]
            merged = list(existing.get("required_capabilities") or [])
            for cap in s.get("required_capabilities") or []:
                if cap not in merged:
                    merged.append(cap)
            seen[sid]["required_capabilities"] = merged
    return list(seen.values())


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_boss_instance: BossAgent | None = None


def get_boss(config: BossConfig | None = None) -> BossAgent:
    global _boss_instance
    if _boss_instance is None or config is not None:
        _boss_instance = BossAgent(config or BossConfig())
    return _boss_instance