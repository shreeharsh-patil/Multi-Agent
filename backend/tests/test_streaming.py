"""Unit tests for SSE streaming functionality.

Tests:
1. process_message_stream() in src/adk/runner.py — the async generator
2. /api/chat/stream POST endpoint — SSE formatting, persistence, error handling
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# =============================================================================
# Mock ADK Event
# =============================================================================


class MockEvent:
    """Minimal mock for google.adk.Event.

    Implements only the attributes/methods used by runner.py:
    node_name, content, message, is_final_response(), etc.
    """

    def __init__(
        self,
        node_name: str = "orchestrator",
        content: str | None = None,
        is_final: bool = False,
    ):
        self.node_name = node_name
        self.content = content
        self.message = content
        self._is_final = is_final

    def is_final_response(self) -> bool:
        return self._is_final

    def get_function_calls(self):
        return []

    def get_function_responses(self):
        return []

    def has_trailing_code_execution_result(self):
        return False

    def model_dump(self):
        return {
            "node_name": self.node_name,
            "content": self.content,
            "is_final": self._is_final,
        }


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_runner():
    """A MagicMock runner whose run_async yields nothing.

    Note: We use MagicMock (not AsyncMock) because AsyncMock.__call__
    wraps the return_value in a coroutine, which breaks 'async for'.
    """
    runner = MagicMock()
    runner.run_async.return_value.__aiter__.return_value = iter([])
    return runner


# =============================================================================
# process_message_stream tests
# =============================================================================


class TestProcessMessageStream:

    @pytest.mark.asyncio
    async def test_first_event_is_start(self, empty_runner):
        """The first yielded event must be 'start' with conversation_id."""
        with patch("src.adk.runner.create_runner", return_value=empty_runner):
            from src.adk.runner import process_message_stream  # late import to avoid lifespan side-effects

            events: list[dict] = []
            async for ev in process_message_stream("hi", "u1", "conv-1"):
                events.append(ev)

        assert len(events) >= 1
        assert events[0]["event"] == "start"
        assert events[0]["data"]["conversation_id"] == "conv-1"

    @pytest.mark.asyncio
    async    def test_yields_chunk_and_complete_with_accumulated_content(self):
        """Content from multiple events is accumulated into the complete event."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", "Hello ", is_final=False),
            MockEvent("knowledge", "World!", is_final=True),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        types = [r["event"] for r in results]
        assert "chunk" in types
        assert "complete" in types

        complete = next(r for r in results if r["event"] == "complete")
        assert complete["data"]["output"] == "Hello World!"
        assert complete["data"]["conversation_id"] == "c1"

    @pytest.mark.asyncio
    async    def test_agent_switch_on_node_name_change(self):
        """An 'agent' event is emitted when node_name differs from previous."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", "Routing to knowledge...", is_final=False),
            MockEvent("knowledge", "Here is the answer.", is_final=True),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        agent_events = [r for r in results if r["event"] == "agent"]
        assert len(agent_events) >= 1
        assert agent_events[-1]["data"]["agent_id"] == "knowledge"

    @pytest.mark.asyncio
    async    def test_fallback_complete_when_no_final_response(self):
        """When no event has is_final_response(), a fallback complete is emitted."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", "Part 1 ", is_final=False),
            MockEvent("orchestrator", "Part 2", is_final=False),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        types = [r["event"] for r in results]
        assert "complete" in types
        complete = next(r for r in results if r["event"] == "complete")
        assert complete["data"]["output"] == "Part 1 Part 2"

    @pytest.mark.asyncio
    async    def test_empty_content_skips_chunk(self):
        """Events with empty or None content still yield trace but not chunk."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", None, is_final=False),
            MockEvent("orchestrator", "", is_final=True),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        types = [r["event"] for r in results]
        assert "chunk" not in types
        assert "trace" in types
        assert "complete" in types

    @pytest.mark.asyncio
    async    def test_trace_events_carry_metadata(self):
        """Trace events include agent_id, event_type and has_content."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", "some-content", is_final=True),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        traces = [r for r in results if r["event"] == "trace"]
        assert len(traces) >= 1
        trace = traces[0]["data"]
        assert trace["agent_id"] == "orchestrator"
        assert trace["event_type"] == "MockEvent"
        assert trace["has_content"] is True

    @pytest.mark.asyncio
    async    def test_complete_ends_generator(self):
        """Once a complete event is yielded, the generator stops."""
        runner = MagicMock()
        runner.run_async.return_value.__aiter__.return_value = iter([
            MockEvent("orchestrator", "First", is_final=False),
            MockEvent("orchestrator", "Final", is_final=True),
            # This event should never be reached
            MockEvent("orchestrator", "Extra", is_final=False),
        ])

        with patch("src.adk.runner.create_runner", return_value=runner):
            from src.adk.runner import process_message_stream

            results: list[dict] = []
            async for ev in process_message_stream("q", "u1", "c1"):
                results.append(ev)

        contents = []
        for r in results:
            if r["event"] == "chunk":
                contents.append(r["data"]["text"])
        assert "Extra" not in contents, "Generator continued after final event"


# =============================================================================
# SSE Endpoint tests (via TestClient)
# =============================================================================


@pytest.fixture
def sse_client():
    """FastAPI TestClient with the chat router patched to avoid DB/ADK calls."""
    # Patch the chat module's dependencies BEFORE importing the app
    with (
        patch("src.api.routes.chat.process_message_stream") as mock_stream,
        patch("src.api.routes.chat._save_messages") as mock_save,
    ):
        # Defer import so it sees the patches at module load for the endpoint
        from fastapi.testclient import TestClient
        from src.main import app

        mock_save.return_value = None
        client = TestClient(app, raise_server_exceptions=False)
        client._mock_stream = mock_stream
        client._mock_save = mock_save
        yield client


class TestStreamEndpoint:

    def test_returns_sse_content_type(self, sse_client):
        """The endpoint must return text/event-stream."""
        async def fake_stream(*_a, **_kw):
            yield {"event": "start", "data": {"conversation_id": "c1"}}
            yield {"event": "complete", "data": {"output": "OK", "conversation_id": "c1"}}

        sse_client._mock_stream.side_effect = fake_stream

        resp = sse_client.post("/api/chat/stream", json={"message": "Hello", "user_id": "test"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_events_formatted_as_sse(self, sse_client):
        """Each yielded event is formatted as 'event: X\\ndata: {...}\\n\\n'."""
        async def fake_stream(*_a, **_kw):
            yield {"event": "start", "data": {"conversation_id": "c1"}}
            yield {"event": "chunk", "data": {"text": "Hello"}}
            yield {"event": "complete", "data": {"output": "Hello", "conversation_id": "c1"}}

        sse_client._mock_stream.side_effect = fake_stream

        resp = sse_client.post("/api/chat/stream", json={"message": "Hi", "user_id": "test"})
        body = resp.text

        assert "event: start" in body
        assert "event: chunk" in body
        assert '"text": "Hello"' in body
        assert "event: complete" in body
        assert body.endswith("\n\n") or "\n\n" in body

    def test_persists_on_complete_event(self, sse_client):
        """_save_messages must be called when a complete event is yielded."""
        async def fake_stream(*_a, **_kw):
            yield {"event": "start", "data": {"conversation_id": "c1"}}
            yield {"event": "chunk", "data": {"text": "Hello world"}}
            yield {"event": "complete", "data": {"output": "Hello world", "conversation_id": "c1"}}

        sse_client._mock_stream.side_effect = fake_stream

        resp = sse_client.post("/api/chat/stream", json={"message": "Hi", "user_id": "test"})
        assert resp.status_code == 200
        sse_client._mock_save.assert_called_once()

    def test_error_event_on_exception(self, sse_client):
        """When the stream raises, an error event is yielded instead of crashing."""
        sse_client._mock_stream.side_effect = RuntimeError("Something broke")

        resp = sse_client.post("/api/chat/stream", json={"message": "Hi", "user_id": "test"})
        assert resp.status_code == 200
        body = resp.text
        assert "event: error" in body
        assert "Something broke" in body
        assert "event: complete" in body

    def test_partial_persistence_on_stream_error(self, sse_client):
        """If an error occurs mid-stream, partial content is saved."""
        call_count = [0]

        async def failing_stream(*_a, **_kw):
            call_count[0] += 1
            yield {"event": "start", "data": {"conversation_id": "c1"}}
            yield {"event": "chunk", "data": {"text": "Partial "}}
            yield {"event": "chunk", "data": {"text": "content"}}
            raise RuntimeError("Mid-stream failure")

        sse_client._mock_stream.side_effect = failing_stream

        resp = sse_client.post("/api/chat/stream", json={"message": "Hi", "user_id": "test"})
        assert resp.status_code == 200
        # _save_messages should be called with the partial content
        sse_client._mock_save.assert_called()
        call = sse_client._mock_save.call_args
        kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
        # agent_message is passed as a keyword argument
        agent_msg = kwargs.get('agent_message', '')
        assert "Partial" in agent_msg or "Partial content" in agent_msg

    def test_conversation_id_passed_through(self, sse_client):
        """A custom conversation_id is reflected in SSE events."""
        async def fake_stream(*_a, **_kw):
            yield {"event": "start", "data": {"conversation_id": "custom-id"}}
            yield {"event": "complete", "data": {"output": "Done", "conversation_id": "custom-id"}}

        sse_client._mock_stream.side_effect = fake_stream

        resp = sse_client.post(
            "/api/chat/stream",
            json={"message": "Hi", "conversation_id": "custom-id", "user_id": "test"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert '"conversation_id": "custom-id"' in body
