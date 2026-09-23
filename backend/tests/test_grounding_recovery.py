import json
import os
import subprocess
import sys
from types import SimpleNamespace

from src.adk import runner


def test_function_tool_web_search_urls_become_citations():
    payload = (
        "### Source 1: Official Example (DuckDuckGo Web)\n"
        "URL: https://example.com/current\n"
        "Current verified information.\n"
    )
    event = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_response=SimpleNamespace(
                        name="web_search",
                        response={"result": payload},
                    )
                )
            ]
        )
    )

    citations = runner._extract_function_tool_citations(event)

    assert citations == [
        {
            "file_name": "Official Example",
            "text": "https://example.com/current",
            "url": "https://example.com/current",
        }
    ]


def test_non_search_function_response_is_not_treated_as_grounding():
    event = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_response=SimpleNamespace(
                        name="calculator",
                        response={"result": "See https://example.com/not-evidence"},
                    )
                )
            ]
        )
    )
    assert runner._extract_function_tool_citations(event) == []


def _run_isolated(script: str) -> dict:
    env = os.environ.copy()
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


def test_missing_adk_evidence_recovers_with_web_search_instead_of_retry_message():
    result = _run_isolated(
        r'''
import asyncio
import json

import src.adk.runner as runner
import src.adk.tools as tools
import src.services.llm as llm_module

runner.use_adk = lambda: True

async def fake_adk_stream(message, user_id="default", conversation_id="default", workspace_id=None, fast_path=False, _failover_attempt=0):
    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "boss_agent"}}
    yield {"event": "chunk", "data": {"text": "Unverified current answer"}}
    yield {"event": "completed", "data": {"output": "Unverified current answer", "conversation_id": conversation_id, "citations": []}}

async def fake_web_search(query, for_research=False, max_items=None):
    return (
        "### Source 1: Official Status (Web)\n"
        "URL: https://example.com/status\n"
        "The current status is operational.\n"
    )

async def fake_generate(*args, **kwargs):
    return "The current status is operational."

runner.process_message_stream = fake_adk_stream
tools.web_search = fake_web_search
llm_module.llm_service.generate = fake_generate

import src.api.routes

async def main():
    events = []
    async for event in runner.process_message_stream(
        "What is the current status?",
        user_id="u1",
        conversation_id="live-current",
    ):
        events.append(event)
    chunks = "".join(e["data"].get("text", "") for e in events if e["event"] == "chunk")
    completed = [e for e in events if e["event"] == "completed"][-1]["data"]
    agents = [e["data"].get("agent_id") for e in events if e["event"] == "agent"]
    print(json.dumps({"chunks": chunks, "completed": completed, "agents": agents}))

asyncio.run(main())
'''
    )

    assert "Unverified current answer" not in result["chunks"]
    assert "current status is operational" in result["chunks"]
    assert "https://example.com/status" in result["chunks"]
    assert result["completed"]["citations"][0]["url"] == "https://example.com/status"
    assert "grounding_rescue" in result["agents"]
    assert "Please retry" not in result["completed"]["output"]


def test_grounding_still_fails_closed_when_search_has_no_sources():
    result = _run_isolated(
        r'''
import asyncio
import json

import src.adk.runner as runner
import src.adk.tools as tools

runner.use_adk = lambda: True

async def fake_adk_stream(message, user_id="default", conversation_id="default", workspace_id=None, fast_path=False, _failover_attempt=0):
    yield {"event": "start", "data": {"conversation_id": conversation_id}}
    yield {"event": "agent", "data": {"agent_id": "boss_agent"}}
    yield {"event": "chunk", "data": {"text": "Unsupported current claim"}}
    yield {"event": "completed", "data": {"output": "Unsupported current claim", "conversation_id": conversation_id, "citations": []}}

async def fake_web_search(query, for_research=False, max_items=None):
    return "No live search results found for the request."

runner.process_message_stream = fake_adk_stream
tools.web_search = fake_web_search

import src.api.routes

async def main():
    events = []
    async for event in runner.process_message_stream(
        "What is the latest status today?",
        user_id="u1",
        conversation_id="live-no-sources",
    ):
        events.append(event)
    completed = [e for e in events if e["event"] == "completed"][-1]["data"]
    print(json.dumps({"completed": completed}))

asyncio.run(main())
'''
    )

    assert "couldn't reliably verify" in result["completed"]["output"]
    assert result["completed"]["citations"] == []
