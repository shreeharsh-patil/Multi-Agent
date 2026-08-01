import pytest
from fastapi.testclient import TestClient
from src.services.swarm_service import SWARM_AGENTS


def test_swarm_agents_endpoint(client: TestClient):
    """Test getting list of participating Swarm agents."""
    response = client.get("/api/swarm/agents")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json.get("success") is True
    
    data = res_json["data"]
    assert "agents" in data
    assert len(data["agents"]) == len(SWARM_AGENTS)
    assert data["agents"][0]["id"] == "researcher"
