import time
from typing import Optional
from src.utils.logger import logger
from src.utils.exceptions import AgentException
from src.agents.registry import AgentRegistry
from src.orchestrator.router import AgentRouter


class AgentOrchestrator:
    def __init__(self):
        self.router = AgentRouter()
        self.registry = AgentRegistry()

    async def process(
        self,
        user_input: str,
        user_id: str,
        agent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> dict:
        start_time = time.time()
        logger.info("Processing request", extra={
            "user_id": user_id,
            "agent_id": agent_id,
            "input_length": len(user_input),
        })

        target_agent_id = agent_id or self.router.route(user_input)

        if not target_agent_id:
            target_agent_id = "knowledge"

        # Route via ADK multi-agent system
        from src.adk.runner import process_message

        conv_id = conversation_id or f"orch_{user_id}_{int(time.time())}"

        try:
            result = await process_message(
                message=user_input,
                user_id=user_id,
                conversation_id=conv_id,
            )

            elapsed = time.time() - start_time
            logger.info("Request processed via ADK", extra={
                "agent_id": target_agent_id,
                "latency_ms": round(elapsed * 1000, 2),
                "success": result.get("success", True),
            })

            return {
                "agent_id": target_agent_id,
                "output": result.get("output", ""),
                "citations": result.get("citations", []),
                "tool_calls": [],
                "agent_traces": result.get("agent_traces", []),
                "latency_ms": round(elapsed * 1000, 2),
                "success": result.get("success", True),
                "error": result.get("error"),
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"ADK processing failed", extra={"error": str(e)})

            # Fallback: use custom agent if ADK fails
            agent = self.registry.get_agent(target_agent_id)
            if agent:
                context = {"user_id": user_id, "conversation_id": conversation_id}
                result = await agent.execute(user_input, context)
                return {
                    "agent_id": target_agent_id,
                    "output": result.output,
                    "citations": result.citations,
                    "tool_calls": result.tool_calls,
                    "latency_ms": round(elapsed * 1000, 2),
                    "success": result.success,
                    "error": result.error,
                }

            raise AgentException(f"Agent execution failed: {e}") from e

    async def process_multi_agent(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
        conversation_id: Optional[str] = None,
    ) -> list[dict]:
        import asyncio
        tasks = [
            self.process(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
            )
            for agent_id in agent_ids
        ]
        return list(await asyncio.gather(*tasks))

    async def process_team(
        self,
        user_input: str,
        user_id: str,
        agent_ids: list[str],
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> dict:
        """Run a deterministic specialist handoff.

        Each agent receives the original task plus the previous specialist's
        output. This is intentionally separate from ADK routing: Teamwork
        mode promises the order selected by the user.
        """
        valid_agents = [agent_id for agent_id in agent_ids if self.registry.get_agent(agent_id)]
        if not valid_agents:
            raise AgentException("Teamwork mode requires at least one valid agent")

        handoff = user_input
        stages = []
        for index, agent_id in enumerate(valid_agents):
            agent = self.registry.get_agent(agent_id)
            if not agent:
                continue
            agent_context = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "team_index": index,
                **(context or {}),
            }
            result = await agent.execute(handoff, agent_context)
            stage = {
                "agent_id": agent_id,
                "output": result.output,
                "success": result.success,
                "error": result.error,
            }
            stages.append(stage)
            if not result.success:
                break
            handoff = (
                f"Original user request:\n{user_input}\n\n"
                f"Previous specialist handoff from {agent_id}:\n{result.output}\n\n"
                "Continue the request as the next specialist. Preserve useful details, "
                "correct issues when needed, and return an actionable result for the user."
            )

        output = "\n\n".join(
            f"### {stage['agent_id'].title()} Agent\n{stage['output']}" for stage in stages
        )
        return {
            "output": output,
            "stages": stages,
            "agent_traces": [
                {"agent_id": stage["agent_id"], "event_type": "TeamStage", "has_content": bool(stage["output"])}
                for stage in stages
            ],
            "events_count": len(stages),
            "success": all(stage["success"] for stage in stages),
        }

    async def process_dynamic(
        self,
        user_input: str,
        user_id: str,
        plan: dict,
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None,
        on_event=None,
    ) -> dict:
        """Execute an automatically selected team and merge it into one answer cleanly."""
        import asyncio
        import time
        from src.orchestrator.dynamic import record_routing
        from src.services.llm import llm_service

        start_time = time.time()
        valid_steps = [
            step for step in plan.get("steps", [])
            if self.registry.get_agent(step.get("agent_id", ""))
        ]
        if not valid_steps:
            valid_steps = [{"agent_id": "knowledge", "label": "Knowledge Agent", "reason": "General reasoning fallback", "role": "general reasoning"}]

        async def emit(event: str, data: dict) -> None:
            if on_event:
                try:
                    result = on_event(event, data)
                    if hasattr(result, "__await__"):
                        await result
                except Exception as emit_err:
                    logger.warning("Event emission failed: %s", emit_err)

        await emit("plan", {
            "complexity": plan.get("complexity", "simple"),
            "domain": plan.get("domain", "general"),
            "agents": [{"agent_id": step["agent_id"], "label": step["label"], "reason": step["reason"]} for step in valid_steps],
        })

        async def run_step(step: dict) -> dict:
            agent_id = step["agent_id"]
            step_start = time.time()
            await emit("agent_started", {"agent_id": agent_id, "label": step["label"], "reason": step["reason"]})
            try:
                agent = self.registry.get_agent(agent_id)
                if not agent:
                    raise AgentException(f"Agent {agent_id} is not registered")

                # Wrap agent execution in a hard 25-second timeout to prevent deadlocks
                result = await asyncio.wait_for(
                    agent.execute(
                        user_input,
                        {
                            "user_id": user_id,
                            "conversation_id": conversation_id,
                            "orchestration_role": step.get("role", "specialist analysis"),
                            **(context or {}),
                        },
                    ),
                    timeout=25.0,
                )
                output = (result.output or "").strip()
                elapsed = round((time.time() - step_start) * 1000, 2)
                await emit("agent_complete", {
                    "agent_id": agent_id,
                    "label": step["label"],
                    "success": bool(result.success and output),
                    "execution_time_ms": elapsed,
                })
                return {
                    "step": step,
                    "output": output,
                    "citations": getattr(result, "citations", []) or [],
                    "success": bool(result.success and output),
                    "execution_time_ms": elapsed,
                }
            except asyncio.TimeoutError:
                elapsed = round((time.time() - step_start) * 1000, 2)
                logger.warning("Dynamic specialist %s timed out after 25s", agent_id)
                await emit("agent_complete", {
                    "agent_id": agent_id,
                    "label": step["label"],
                    "success": False,
                    "error": "Execution timed out (25s limit)",
                    "execution_time_ms": elapsed,
                })
                return {"step": step, "output": "", "citations": [], "success": False, "error": "Timeout", "execution_time_ms": elapsed}
            except Exception as exc:
                elapsed = round((time.time() - step_start) * 1000, 2)
                logger.warning("Dynamic specialist %s failed: %s", agent_id, exc)
                await emit("agent_complete", {
                    "agent_id": agent_id,
                    "label": step["label"],
                    "success": False,
                    "error": str(exc),
                    "execution_time_ms": elapsed,
                })
                return {"step": step, "output": "", "citations": [], "success": False, "error": str(exc), "execution_time_ms": elapsed}

        # Run all specialists concurrently with circuit breaker error isolation
        results = await asyncio.gather(*(run_step(step) for step in valid_steps), return_exceptions=True)

        cleaned_results = []
        for r, step in zip(results, valid_steps):
            if isinstance(r, dict):
                cleaned_results.append(r)
            else:
                cleaned_results.append({"step": step, "output": "", "citations": [], "success": False, "error": str(r), "execution_time_ms": 0})

        usable = [r for r in cleaned_results if r.get("output", "").strip()]
        citations = [citation for r in usable for citation in r.get("citations", []) if citation]
        record_routing(plan.get("domain", "general"), [r["step"]["agent_id"] for r in usable])

        await emit("synthesizing", {"usable_agents": len(usable), "total_agents": len(valid_steps)})

        output = ""
        state = "SUCCESS"

        if len(usable) == 1:
            output = usable[0]["output"]
        elif len(usable) > 1:
            evidence = "\n\n".join(
                f"[{r['step']['label']} — {r['step'].get('role', 'specialist')}]:\n{r['output']}"
                for r in usable
            )
            try:
                output = await asyncio.wait_for(
                    llm_service.generate(
                        prompt=f"User request:\n{user_input}\n\nSpecialist findings:\n{evidence}",
                        system_instruction=(
                            "You are the Master Orchestrator's answer editor. Merge the specialist findings into one "
                            "coherent answer for the user. Do not mention agents, orchestration, handoffs, or internal "
                            "findings. Resolve contradictions conservatively, preserve useful citations, and use clear "
                            "Markdown. If a diagram is useful, include valid Mermaid in a fenced mermaid block."
                        ),
                        temperature=0.35,
                        max_output_tokens=6000,
                    ),
                    timeout=30.0,
                )
            except Exception as synth_err:
                logger.error("Master synthesis failed: %s, using concatenated findings", synth_err)
                output = "\n\n---\n\n".join(r["output"] for r in usable)
                state = "PARTIAL_SUCCESS"

        # Fallback if all specialists failed or generated empty outputs
        if not output or not output.strip():
            logger.warning("No usable specialist output, running direct master fallback synthesis")
            state = "PARTIAL_SUCCESS" if usable else "FAILED_WITH_REASON"
            try:
                from datetime import datetime, timezone
                now_utc = datetime.now(timezone.utc).strftime("%A, %d %B %Y %H:%M:%S UTC")
                output = await asyncio.wait_for(
                    llm_service.generate(
                        prompt=user_input,
                        system_instruction=(
                            f"Current Real-Time System Date & Time: {now_utc}.\n"
                            "You are the Master AI Assistant for the Agentic Multi-Agent Workspace platform. "
                            "Provide a comprehensive, accurate, and direct response to the user's request. "
                            "Use clear Markdown formatting with headings, bold text, lists, and code blocks as appropriate."
                        ),
                        temperature=0.7,
                        max_output_tokens=4096,
                    ),
                    timeout=25.0,
                )
            except Exception as fallback_err:
                logger.error("Direct master fallback synthesis failed: %s", fallback_err)
                output = "The orchestrator processed your request, but experienced a temporary delay. Please try resending your message."
                state = "TIMEOUT"

        total_latency = round((time.time() - start_time) * 1000, 2)
        return {
            "output": output.strip(),
            "citations": citations,
            "agent_traces": [
                {
                    "agent_id": r["step"]["agent_id"],
                    "event_type": "DynamicSpecialist",
                    "has_content": bool(r.get("output")),
                    "execution_time_ms": r.get("execution_time_ms", 0),
                    "success": r.get("success", False),
                    "error": r.get("error"),
                }
                for r in cleaned_results
            ],
            "events_count": len(cleaned_results),
            "success": bool(output.strip()),
            "state": state,
            "latency_ms": total_latency,
            "plan": plan,
        }


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
