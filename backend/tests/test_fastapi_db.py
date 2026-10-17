"""FastAPI database integration tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db

client = TestClient(app)


class TestHealthEndpointWithoutDB:
    """Verify the health endpoint works even without a database configured."""

    def test_health_returns_ok_without_db(self):
        """When DATABASE_URL is unset the API still reports ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert "components" in data
        assert "database" in data["components"]

    def test_api_v1_health_returns_ok_without_db(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")


class TestGetDbDependency:
    """Verify the get_db dependency is importable and well-formed."""

    def test_get_db_is_generator(self):
        from app.db.session import get_db
        import inspect

        assert inspect.isgeneratorfunction(get_db)
