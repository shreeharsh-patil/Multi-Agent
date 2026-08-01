import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set environment variables for testing before importing settings
os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-authentication-testing-only"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["LLM_PROVIDER"] = "groq"

from fastapi.testclient import TestClient


@pytest.fixture
def mock_mongo():
    """Mock Motor/Beanie MongoDB client for unit testing."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.admin.command = AsyncMock(return_value={"ok": 1.0})
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_app(mock_mongo):
    """FastAPI TestClient with bypassed lifespan MongoDB initialization."""
    with patch("src.main.init_beanie", new=AsyncMock()):
        with patch("src.agents.init_agents.initialize_agents"):
            with patch("src.adk.runner.get_orchestrator"):
                from src.main import app
                yield app


@pytest.fixture
def client(test_app):
    """FastAPI HTTP TestClient."""
    return TestClient(test_app)
