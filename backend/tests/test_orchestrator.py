import pytest
from src.orchestrator.router import AgentRouter


class TestAgentRouter:
    def setup_method(self):
        self.router = AgentRouter()

    def test_routes_knowledge_query(self):
        queries = [
            "summarize this document",
            "what is in the pdf",
            "search the knowledge base for AI",
            "explain the content of the file",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "knowledge", f"Failed to route: {q}"

    def test_routes_drive_query(self):
        queries = [
            "upload file to drive",
            "sync my google drive folder",
            "download document from drive",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "drive", f"Failed to route: {q}"

    def test_routes_notes_query(self):
        queries = [
            "create notes on AI",
            "make flashcards for chapter 5",
            "generate revision notes",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "notes", f"Failed to route: {q}"

    def test_routes_quiz_query(self):
        queries = [
            "generate a quiz on ML",
            "create mcq questions",
            "make a practice exam",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "quiz", f"Failed to route: {q}"

    def test_routes_planner_query(self):
        queries = [
            "plan my study schedule",
            "create a task list",
            "set a deadline for project",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "planner", f"Failed to route: {q}"

    def test_routes_research_query(self):
        queries = [
            "research the latest AI trends",
            "search the internet for quantum computing",
            "find online sources about climate change",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "research", f"Failed to route: {q}"

    def test_routes_coding_query(self):
        queries = [
            "write a python function",
            "debug this code",
            "implement a sorting algorithm",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "coding", f"Failed to route: {q}"

    def test_routes_memory_query(self):
        queries = [
            "remember my favorite color is blue",
            "what did I say about Python",
            "recall my preferences",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "memory", f"Failed to route: {q}"

    def test_routes_tool_query(self):
        queries = [
            "calculate 25 * 4",
            "use the calculator",
            "call the weather api",
        ]
        for q in queries:
            result = self.router.route(q)
            assert result == "tool", f"Failed to route: {q}"

    def test_returns_none_for_unknown(self):
        result = self.router.route("hello how are you")
        assert result is None
