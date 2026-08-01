import pytest
from fastapi.testclient import TestClient


def test_voice_endpoints_available(client: TestClient):
    """Test voice route endpoints registered in FastAPI."""
    response = client.post("/api/voice/synthesize", json={"text": "Hello world"})
    # Expecting 400 because DEEPGRAM_API_KEY is mock in test environment
    assert response.status_code in [400, 401, 502, 200]
