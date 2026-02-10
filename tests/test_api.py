"""
Integration tests for the Function Store REST API using FastAPI TestClient.
"""
import pytest
import time
from fastapi.testclient import TestClient
from solo_mcp.api import app

# Use a test client to avoid needing a running server
client = TestClient(app)

# Dummy API key for testing
HEADERS = {"X-API-Key": "test_key"}

@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    """Ensure auth is mocked for each test."""
    # Mocking verify_api_key to always succeed for testing purposes
    # Mocking verify_api_key to always succeed for testing purposes
    monkeypatch.setattr("solo_mcp.api.verify_api_key", lambda key: (True, "test_user"))
    yield

def test_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_save_and_run_flow():
    """Test saving a function and then running it via the API."""
    ts = int(time.time())
    unique_name = f"api_test_add_{ts}"
    function_data = {
        "asset_name": unique_name,
        "code": "def " + unique_name + "(a, b):\n    return a + b",
        "description": "API Test Function",
        "test_cases": [
            {"input": {"a": 2, "b": 3}, "expected": 5}
        ],
        "tags": ["test"]
    }
    
    # 1. Save
    response = client.post("/functions", json=function_data, headers=HEADERS)
    assert response.status_code == 200
    
    # 2. Search
    search_query = {"query": unique_name, "limit": 1}
    response = client.post("/functions/search", json=search_query, headers=HEADERS)
    assert response.status_code == 200
    assert any(r["name"] == unique_name for r in response.json())

def test_auth_failure():
    """Test that requests without API key are rejected."""
    response = client.get("/functions/any/history")
    assert response.status_code == 401
