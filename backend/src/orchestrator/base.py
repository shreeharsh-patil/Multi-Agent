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
        """Execute an automatically selected team and merge it into one answer."""
        import asyncio
        from src.orchestrator.dynamic import record_routing

        valid_steps = [
            step for step in plan.get("steps", [])
            if self.registry.get_agent(step.get("agent_id", ""))
        ]
        if not valid_steps:
            raise AgentException("Automatic orchestration found no available specialist")

        async def emit(event: str, data: dict) -> None:
            if on_event:
                result = on_event(event, data)
                if hasattr(result, "__await__"):
                    await result

        await emit("plan", {
            "complexity": plan.get("complexity", "simple"),
            "domain": plan.get("domain", "general"),
            "agents": [{"agent_id": step["agent_id"], "label": step["label"], "reason": step["reason"]} for step in valid_steps],
        })

        async def run_step(step: dict) -> dict:
            agent_id = step["agent_id"]
            await emit("agent_started", {"agent_id": agent_id, "label": step["label"], "reason": step["reason"]})
            try:
                agent = self.registry.get_agent(agent_id)
                result = await agent.execute(
                    user_input,
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "orchestration_role": step.get("role", "specialist analysis"),
                        **(context or {}),
                    },
                )
                output = result.output or ""
                await emit("agent_complete", {"agent_id": agent_id, "label": step["label"], "success": bool(result.success)})
                return {"step": step, "output": output, "citations": getattr(result, "citations", []), "success": result.success}
            except Exception as exc:
                logger.warning("Dynamic specialist %s failed: %s", agent_id, exc)
                await emit("agent_complete", {"agent_id": agent_id, "label": step["label"], "success": False})
                return {"step": step, "output": "", "citations": [], "success": False, "error": str(exc)}

        # All specialists receive the same original request, so they can run
        # concurrently. The final synthesis is the only dependent stage.
        results = await asyncio.gather(*(run_step(step) for step in valid_steps))
        usable = [result for result in results if result["output"].strip()]
        citations = [citation for result in usable for citation in result.get("citations", [])]
        record_routing(plan.get("domain", "general"), [result["step"]["agent_id"] for result in usable])

        if len(usable) == 1:
            output = usable[0]["output"]
        else:
            from src.services.llm import llm_service
            evidence = "\n\n".join(
                f"[{result['step']['label']} — {result['step'].get('role', 'specialist')}]:\n{result['output']}"
                for result in usable
            )
            output = await llm_service.generate(
                prompt=f"User request:\n{user_input}\n\nSpecialist findings:\n{evidence}",
                system_instruction=(
                    "You are the Master Orchestrator's answer editor. Merge the specialist findings into one "
                    "coherent answer for the user. Do not mention agents, orchestration, handoffs, or internal "
                    "findings. Resolve contradictions conservatively, preserve useful citations, and use clear "
                    "Markdown. If a diagram is useful, include valid Mermaid in a fenced mermaid block."
                ),
                temperature=0.35,
                max_output_tokens=6000,
            )

        return {
            "output": output,
            "citations": citations,
            "agent_traces": [
                {"agent_id": result["step"]["agent_id"], "event_type": "DynamicSpecialist", "has_content": bool(result["output"])}
                for result in results
            ],
            "events_count": len(results),
            "success": bool(output),
            "plan": plan,
        }


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
