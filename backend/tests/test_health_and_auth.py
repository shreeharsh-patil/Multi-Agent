import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test API root metadata endpoint wrapped in response envelope."""
    response = client.get("/api")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json.get("success") is True
    
    data = res_json["data"]
    assert "name" in data
    assert "version" in data
    assert "endpoints" in data
    assert data["endpoints"]["health"] == "/api/health"


def test_health_check(client: TestClient):
    """Test API health check endpoint wrapped in response envelope."""
    response = client.get("/api/health")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json.get("success") is True
    
    data = res_json["data"]
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
