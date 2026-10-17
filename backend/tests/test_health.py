"""Automated tests for health check endpoints and error handling."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_health_endpoint():
    """Verify GET /health returns 200 OK and expected HealthResponse schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "MRI Analysis API"
    assert "version" in data
    assert "environment" in data


def test_api_v1_health_endpoint():
    """Verify GET /api/v1/health returns 200 OK and matching schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "MRI Analysis API"
    assert "version" in data
    assert "environment" in data


def test_root_info_endpoint():
    """Verify GET / returns 200 OK with service metadata and doc links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MRI Analysis API"
    assert data["docs"] == "/docs"
    assert data["redoc"] == "/redoc"
    assert data["health"] == "/health"
    assert data["api_v1_health"] == "/api/v1/health"


def test_not_found_structured_error():
    """Verify that a 404 response follows the standardized error format."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["status_code"] == 404
    assert "message" in data["error"]
