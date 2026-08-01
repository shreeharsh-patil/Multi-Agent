import pytest
from src.orchestrator.router import AgentRouter


def test_agent_router_intent_matching():
    """Test pattern matching for domain-specialized agent routing."""
    router = AgentRouter()

    assert router.route("Generate an image of a cybernetic cat") == "image"
    assert router.route("Schedule a meeting with John on my calendar") == "calendar"
    assert router.route("Summarize this document PDF") == "knowledge"
    assert router.route("Search Google Drive for quarterly reports") == "drive"
    assert router.route("Create a quiz with 5 multiple choice questions") == "quiz"
    assert router.route("Research the latest advancements in quantum computing") == "research"
    assert router.route("Write code to implement quicksort in Python") == "coding"
    assert router.route("Remember that my favorite color is teal") == "memory"


def test_agent_router_fallback():
    """Test fallback when no pattern matches generic prompt."""
    router = AgentRouter()
    assert router.route("Hello how are you today?") is None
