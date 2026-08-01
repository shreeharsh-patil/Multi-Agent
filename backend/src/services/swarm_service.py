import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from src.services.llm import get_llm_provider
from src.utils.logger import logger

SWARM_AGENTS = [
    {
        "id": "researcher",
        "name": "Research & Knowledge Agent",
        "role": "Domain Researcher",
        "avatar": "🔍",
        "system_prompt": (
            "You are an expert Research & Domain Knowledge AI Agent in a multi-agent swarm. "
            "Your task is to analyze the prompt, extract core requirements, identify key concepts, "
            "and lay out foundational research facts, architectural constraints, and background details."
        ),
    },
    {
        "id": "architect",
        "name": "System Architect & Coder",
        "role": "Lead Architect",
        "avatar": "💻",
        "system_prompt": (
            "You are a Senior System Architect & Technical Lead AI Agent in a multi-agent swarm. "
            "Using the research provided by the Research Agent, design a comprehensive, high-quality, "
            "production-grade technical solution, code implementation, or operational strategy."
        ),
    },
    {
        "id": "critic",
        "name": "Security & Quality Auditor",
        "role": "Critic & Auditor",
        "avatar": "🛡️",
        "system_prompt": (
            "You are a Security, Reliability, and Edge-Case Auditor AI Agent in a multi-agent swarm. "
            "Review the proposal from the Architect Agent. Identify security vulnerabilities, performance "
            "bottlenecks, missing edge cases, and areas of improvement."
        ),
    },
    {
        "id": "synthesizer",
        "name": "Swarm Orchestrator & Synthesizer",
        "role": "Consensus Lead",
        "avatar": "🤖",
        "system_prompt": (
            "You are the Swarm Lead & Synthesis Orchestrator AI Agent. "
            "Synthesize the research, proposed solution, and audit critique into a unified, definitive "
            "consensus report with key takeaways, revised architecture/code, and action items."
        ),
    },
]


async def stream_swarm_collaboration(user_prompt: str) -> AsyncGenerator[str, None]:
    """Execute a multi-agent swarm debate & collaboration loop yielding SSE events."""
    rotator = get_llm_provider()
    conversation_history: Dict[str, str] = {}

    yield f"data: {json.dumps({'type': 'swarm_init', 'topic': user_prompt, 'agents': SWARM_AGENTS})}\n\n"
    await asyncio.sleep(0.1)

    for agent in SWARM_AGENTS:
        agent_id = agent["id"]
        agent_name = agent["name"]
        role = agent["role"]

        yield f"data: {json.dumps({'type': 'agent_start', 'agent_id': agent_id, 'name': agent_name, 'role': role})}\n\n"

        # Build context from previous agents' work
        context_str = f"User Request: {user_prompt}\n\n"
        if conversation_history:
            context_str += "--- PREVIOUS AGENT CONTRIBUTIONS ---\n"
            for prev_id, prev_output in conversation_history.items():
                context_str += f"\n[{prev_id.upper()} OUTPUT]:\n{prev_output}\n"

        full_output_chunks = []
        try:
            async for chunk in rotator.generate_stream(
                prompt=context_str,
                system_instruction=agent["system_prompt"],
            ):
                full_output_chunks.append(chunk)
                yield f"data: {json.dumps({'type': 'agent_token', 'agent_id': agent_id, 'token': chunk})}\n\n"
        except Exception as e:
            err_msg = f"Error during {agent_name} execution: {str(e)}"
            logger.error(err_msg)
            full_output_chunks.append(f"\n[Execution error: {str(e)}]")
            yield f"data: {json.dumps({'type': 'agent_token', 'agent_id': agent_id, 'token': err_msg})}\n\n"

        agent_full_text = "".join(full_output_chunks)
        conversation_history[agent_id] = agent_full_text

        yield f"data: {json.dumps({'type': 'agent_complete', 'agent_id': agent_id, 'output': agent_full_text})}\n\n"
        await asyncio.sleep(0.2)

    final_consensus = conversation_history.get("synthesizer", "")
    yield f"data: {json.dumps({'type': 'swarm_complete', 'consensus': final_consensus})}\n\n"
