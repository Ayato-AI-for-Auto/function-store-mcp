"""
Test API authentication using FastAPI TestClient to ensure isolation.
"""
import pytest
from fastapi.testclient import TestClient
from mcp_core.api import app
from mcp_core.auth import generate_api_key

client = TestClient(app)

@pytest.fixture
def valid_api_key():
    """Generate a real valid API key for testing."""
    key = generate_api_key("test_user_auth")
    return key

def test_health_endpoint():
    """Health endpoint should work without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_without_key():
    """Test request without API key (should fail)."""
    response = client.get("/functions/test_func")
    assert response.status_code == 401
    assert "detail" in response.json()

def test_with_invalid_key():
    """Test request with invalid API key (should fail)."""
    headers = {"X-API-Key": "fsk_invalid_key_12345"}
    response = client.get("/functions/test_func", headers=headers)
    assert response.status_code == 403

def test_with_valid_key(valid_api_key):
    """Test request with valid API key (should succeed)."""
    headers = {"X-API-Key": valid_api_key}
    # Using /functions/search as a representative endpoint
    response = client.post(
        "/functions/search",
        headers=headers,
        json={"query": "test", "limit": 3}
    )
    # 200 is success for search
    assert response.status_code == 200
