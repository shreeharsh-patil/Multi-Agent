import json
import os
import subprocess
import sys


# Import the module directly during pytest. routes.__init__ deliberately skips
# the production global install while pytest is present in sys.modules.
from src.api.routes import _chat_quality as quality


def test_quality_helpers_fail_closed_for_live_queries():
    assert quality._is_user_facing("boss_agent") is True
    assert quality._is_user_facing("coding_manager") is False
    assert quality._is_adk_failure("Google ADK could not complete this request after trying routes.") is True
    assert quality._requires_live_verification("What is the latest AI news today?") is True
    assert quality._requires_live_verification("Explain binary search with an example") is False


def test_compact_prompt_keeps_prefix_and_latest_turn():
    text = "SYSTEM PREFIX\n" + ("old context " * 5000) + "\nLATEST USER REQUEST"
    compacted = quality._compact_prompt(text, limit=1200)

    assert len(compacted) <= 1250
    assert compacted.startswith("SYSTEM PREFIX")
    assert compacted.endswith("LATEST USER REQUEST")
    assert "Earlier repeated context omitted" in compacted


def _run_isolated(script: str) -> dict:
    env = os.environ.copy()
    # The subprocess is intentionally not a pytest process, so importing the
    # routes package exercises the same bootstrap path used in production.
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_production_stream_suppresses_specialist_draft_and_keeps_boss_answer():
    result = _run_isolated(
        r'''
import asyncio
import json

import src.adk.runner as runner

captured = {}
runner.use_adk = lambda: True

async def fake_stream(message, user_id="default", conversation_id="default", workspace_id=None, fast_path=False, _failover_attempt=0):
    captured["internal_session"] = conversation_id
    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "coding_manager"}}
    yield {"event": "chunk", "data": {"text": "INTERNAL DRAFT SHOULD NOT LEAK"}}
    yield {"event": "trace", "data": {"agent_id": "coding_manager", "has_content": True}}
    yield {"event": "agent", "data": {"agent_id": "boss_agent"}}
    yield {"event": "answer_started", "data": {"message": "Preparing answer..."}}
    yield {"event": "chunk", "data": {"text": "Clean final answer"}}
    yield {"event": "completed", "data": {"output": "wrong later aggregate", "conversation_id": conversation_id, "citations": []}}

runner.process_message_stream = fake_stream

import src.api.routes  # installs the production quality wrapper

async def main():
    events = []
    async for event in runner.process_message_stream(
        "Explain the bug",
        user_id="u1",
        conversation_id="conversation-123",
    ):
        events.append(event)
    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    completed = [e for e in events if e["event"] == "completed"][-1]
    print(json.dumps({
        "chunks": chunks,
        "completed": completed["data"],
        "internal_session": captured["internal_session"],
    }))

asyncio.run(main())
'''
    )

    assert result["chunks"] == ["Clean final answer"]
    assert result["completed"]["output"] == "Clean final answer"
    assert result["completed"]["conversation_id"] == "conversation-123"
    assert result["internal_session"] != "conversation-123"
    assert result["internal_session"].startswith("conversation-123-request-")


def test_production_stream_synthesizes_specialist_only_final():
    result = _run_isolated(
        r'''
import asyncio
import json

import src.adk.runner as runner
import src.services.llm as llm_module

runner.use_adk = lambda: True

async def fake_generate(*args, **kwargs):
    return "Polished user-facing answer"

llm_module.llm_service.generate = fake_generate

async def fake_stream(message, user_id="default", conversation_id="default", workspace_id=None, fast_path=False, _failover_attempt=0):
    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "backend_engineer"}}
    yield {"event": "chunk", "data": {"text": "raw specialist chatter"}}
    yield {"event": "completed", "data": {"output": "raw specialist report", "conversation_id": conversation_id, "citations": []}}

runner.process_message_stream = fake_stream

import src.api.routes

async def main():
    events = []
    async for event in runner.process_message_stream(
        "Fix my API",
        user_id="u1",
        conversation_id="conversation-456",
    ):
        events.append(event)
    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    agents = [e["data"].get("agent_id") for e in events if e["event"] == "agent"]
    completed = [e for e in events if e["event"] == "completed"][-1]
    print(json.dumps({"chunks": chunks, "agents": agents, "completed": completed["data"]}))

asyncio.run(main())
'''
    )

    assert result["chunks"] == ["Polished user-facing answer"]
    assert "final_synthesizer" in result["agents"]
    assert result["completed"]["output"] == "Polished user-facing answer"
    assert result["completed"]["conversation_id"] == "conversation-456"
