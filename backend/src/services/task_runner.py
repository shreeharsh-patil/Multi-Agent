"""Multi-step autonomous task runner.

Breaks a complex goal into a plan, executes each step (optionally using
web search, knowledge base, or calculator tools), then verifies and
synthesizes the final deliverable. Streams progress as Server-Sent Events.
"""
import json
import re
from typing import AsyncGenerator

from src.services.llm import llm_service
from src.utils.logger import logger

MAX_STEPS = 5
MAX_STEP_OUTPUT_CHARS = 6000
VALID_TOOLS = {"search", "knowledge", "calculate", "none"}


def _safe_json_list(text: str) -> list[dict]:
    """Parse an LLM plan response into a JSON list, tolerating fences/trimming."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _plan_steps(user_prompt: str) -> list[dict]:
    """Use the LLM to break a goal into an ordered list of executable steps."""
    system = (
        "You are a task planning engine. Break the user's goal into a concise, "
        f"ordered plan of at most {MAX_STEPS} concrete execution steps. "
        'Return ONLY a JSON array. Each step is an object with: '
        '"title" (short verb phrase), "description" (what to do or query), '
        'and "tool" which must be exactly one of "search" | "knowledge" | "calculate" | "none". '
        'Use "search" to gather current online information, "knowledge" for stored documents, '
        '"calculate" for math, and "none" for pure reasoning steps. No markdown, no code fences.'
    )
    try:
        raw = await llm_service.generate(
            prompt=user_prompt,
            system_instruction=system,
            temperature=0.3,
            max_output_tokens=1024,
        )
    except Exception as e:
        logger.error(f"Task planning failed: {e}")
        return []

    steps = _safe_json_list(raw)
    clean = []
    for s in steps[:MAX_STEPS]:
        title = str(s.get("title", "")).strip() or str(s.get("description", "")).strip()[:60]
        tool = str(s.get("tool", "none")).strip().lower()
        if tool not in VALID_TOOLS:
            tool = "none"
        clean.append({
            "title": title[:120],
            "description": str(s.get("description", "")).strip()[:2000],
            "tool": tool,
        })
    return clean


async def _run_search(step: dict) -> str:
    from src.adk.tools import web_search

    query = step.get("description") or step.get("title")
    return await web_search(query, for_research=True)


async def _run_knowledge(step: dict, user_id: str) -> str:
    from src.adk.tools import knowledge_search

    query = step.get("description") or step.get("title")
    return await knowledge_search(query, user_id=user_id)


async def _run_calculate(step: dict) -> str:
    from src.adk.tools import calculator

    expr = step.get("description") or step.get("title")
    match = re.search(r"[\d\s\.\+\-\*/\^\(\)%]+", expr)
    if match:
        expr = match.group().strip()
    if not expr:
        return "No valid math expression found."
    try:
        return await calculator(expr)
    except Exception as e:
        return f"Calculation failed: {e}"


async def _run_step(step: dict, accumulated: str, user_id: str) -> str:
    """Execute a single step, optionally running a tool, and summarize the result."""
    tool = step.get("tool", "none")
    tool_result = ""
    if tool == "search":
        tool_result = await _run_search(step)
    elif tool == "knowledge":
        tool_result = await _run_knowledge(step, user_id)
    elif tool == "calculate":
        tool_result = await _run_calculate(step)

    if tool in {"search", "knowledge"}:
        prompt = (
            f"Step goal: {step.get('description', '')}\n\n"
            f"Tool output:\n{tool_result[:8000]}\n\n"
            "Summarize the key findings for this step in 2-4 bullet points, "
            "including concrete facts, numbers, and sources where available."
        )
        system = "You are a careful research executor. Report only what the tool output supports."
    else:
        prompt = (
            "Accomplish the following step using the accumulated context so far.\n"
            f"Step goal: {step.get('description', '')}\n\n"
            f"Accumulated context from previous steps:\n{accumulated[:6000]}\n"
        )
        system = "You are a step executor in a multi-step task run. Be concise but complete."

    try:
        result = await llm_service.generate(
            prompt=prompt,
            system_instruction=system,
            max_output_tokens=900,
        )
    except Exception as e:
        result = tool_result or f"Step failed: {e}"
    return result.strip()[:MAX_STEP_OUTPUT_CHARS]


async def _verify(goal: str, steps: list[dict], outputs: list[str]) -> str:
    """Synthesize the final deliverable from all step outputs."""
    step_text = "\n\n".join(
        f"STEP {i + 1}: {s.get('title', '')}\n{out}"
        for i, (s, out) in enumerate(zip(steps, outputs))
    )
    prompt = (
        f"Original goal: {goal}\n\n"
        f"Completed steps:\n{step_text[:15000]}\n\n"
        "Now produce the FINAL deliverable for the user. Synthesize the step results into a "
        "clear, well-structured answer (headings, bullet points, and bold where appropriate). "
        "Explicitly note any gaps or unverified claims."
    )
    system = "You are a verifier and final synthesizer. Produce the best complete answer to the user's goal."
    return await llm_service.generate(
        prompt=prompt,
        system_instruction=system,
        max_output_tokens=1600,
    )


async def stream_task_run(user_prompt: str, user_id: str = "default") -> AsyncGenerator[str, None]:
    """Run a multi-step task and yield SSE strings (event: task_* + data JSON)."""
    goal = user_prompt.strip()

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield sse("task_start", {"task_id": "live", "total_steps": 0, "title": goal[:100]})

    steps = await _plan_steps(goal)
    if not steps:
        steps = [{"title": "Answer directly", "description": goal, "tool": "none"}]

    yield sse("task_start", {"task_id": "live", "total_steps": len(steps), "title": goal[:100]})

    outputs: list[str] = []
    accumulated = ""
    try:
        for idx, step in enumerate(steps, start=1):
            yield sse("task_step", {"step_index": idx, "title": step["title"], "status": "running"})
            try:
                out = await _run_step(step, accumulated, user_id)
            except Exception as e:
                out = f"Step failed: {e}"
            outputs.append(out)
            accumulated += f"\n\n--- Step {idx}: {step['title']} ---\n{out}"
            yield sse("task_step", {"step_index": idx, "title": step["title"], "status": "complete", "output": out})
            yield sse("task_progress", {"percent": int(idx / max(len(steps), 1) * 100)})

        final = await _verify(goal, steps, outputs)
        yield sse("task_complete", {"output": final, "steps": steps, "total_steps": len(steps)})
    except Exception as e:
        logger.error(f"Task run failed: {e}")
        yield sse("task_complete", {
            "output": f"The task run encountered an error: {e}",
            "steps": steps,
            "total_steps": len(steps),
        })
