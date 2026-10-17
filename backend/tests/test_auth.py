"""Tests for authentication endpoints and security — Phase 9."""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_db_optional
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)


# ==============================================================================
# Test client helpers
# ==============================================================================

def _client_with_no_db() -> TestClient:
    """Return a TestClient with the DB dependency overridden to return None.

    This simulates the behaviour of the app when PostgreSQL is unavailable
    without suffering a 2-second TCP connect timeout per test.
    """
    app.dependency_overrides[get_db_optional] = lambda: (yield None)
    client = TestClient(app, raise_server_exceptions=False)
    return client


# Default client (DB dependency NOT overridden — uses real DB probe which yields None)
client_no_db_override = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# 1. Security utility unit tests
# ==============================================================================

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        """Password hash must differ from plain text."""
        plain = "SecurePass123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        """Correct password verifies successfully."""
        plain = "TestPassword99"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password does not verify."""
        hashed = hash_password("CorrectPass1")
        assert verify_password("WrongPass1", hashed) is False

    def test_verify_malformed_hash(self):
        """Malformed hash returns False without raising."""
        assert verify_password("anything", "not-a-real-hash") is False

    def test_different_hashes_for_same_password(self):
        """bcrypt generates unique salts — two hashes of same password differ."""
        plain = "SamePassword1"
        h1 = hash_password(plain)
        h2 = hash_password(plain)
        assert h1 != h2
        # Both still verify
        assert verify_password(plain, h1) is True
        assert verify_password(plain, h2) is True


class TestJWTTokens:
    def test_create_and_verify_access_token(self):
        """Access token round-trip: create → verify → extract claims."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="viewer")
        assert isinstance(token, str)
        assert len(token) > 30

        payload = verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["role"] == "viewer"
        assert payload["type"] == "access"

    def test_access_token_with_admin_role(self):
        """Admin role is correctly embedded in token."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="admin")
        payload = verify_access_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_returns_none(self):
        """Tampered/invalid token returns None from verify."""
        result = verify_access_token("not.a.valid.jwt.token")
        assert result is None

    def test_refresh_token_type_field(self):
        """Refresh tokens have type='refresh' to prevent misuse as access tokens."""
        from app.core.security import decode_token
        user_id = str(uuid.uuid4())
        refresh = create_refresh_token(subject=user_id, role="viewer")
        payload = decode_token(refresh)
        assert payload["type"] == "refresh"

    def test_refresh_token_rejected_as_access(self):
        """verify_access_token rejects refresh tokens."""
        user_id = str(uuid.uuid4())
        refresh = create_refresh_token(subject=user_id, role="viewer")
        result = verify_access_token(refresh)
        assert result is None


# ==============================================================================
# 2. API endpoint tests (DB overridden to return None → 503)
# ==============================================================================

class TestAuthEndpointsNoDB:
    """Auth routes return 503 when database is unavailable."""

    def setup_method(self):
        """Override DB dependency to immediately return None (no timeout)."""
        app.dependency_overrides[get_db_optional] = lambda: (yield None)
        self.client = TestClient(app, raise_server_exceptions=False)

    def teardown_method(self):
        """Restore real dependency after each test."""
        app.dependency_overrides.pop(get_db_optional, None)

    def test_register_no_db_returns_503(self):
        """Registration requires DB — returns 503 when unavailable."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123",
            },
        )
        assert response.status_code == 503
        assert "database" in response.json()["error"]["message"].lower()

    def test_login_no_db_returns_503(self):
        """Login requires DB — returns 503 when unavailable."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPass123"},
        )
        assert response.status_code == 503

    def test_refresh_no_db_returns_503(self):
        """Refresh requires DB — returns 503 when unavailable."""
        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "dummy_token_value"},
        )
        assert response.status_code == 503

    def test_me_no_auth_returns_401(self):
        """GET /me without Bearer token returns 401."""
        response = self.client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["status_code"] == 401

    def test_me_invalid_token_returns_401(self):
        """GET /me with invalid token returns 401."""
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert response.status_code == 401

    def test_logout_no_auth_returns_401(self):
        """Logout without Bearer token returns 401."""
        response = self.client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_admin_role_endpoint_unauthorized(self):
        """Role change without auth returns 401."""
        response = self.client.put(
            f"/api/v1/auth/users/{uuid.uuid4()}/role",
            params={"role": "admin"},
        )
        assert response.status_code == 401

    def test_admin_role_endpoint_viewer_role_forbidden(self):
        """Role change with viewer role returns 403."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="viewer")
        response = self.client.put(
            f"/api/v1/auth/users/{uuid.uuid4()}/role",
            params={"role": "radiologist"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


# ==============================================================================
# 3. Registration input validation (Pydantic → 422 before DB is touched)
# ==============================================================================

class TestRegistrationValidation:
    """Input validation tests — 422 comes from Pydantic BEFORE DB access."""

    def setup_method(self):
        """Override DB to immediately yield None to avoid timeout on bad-data requests."""
        app.dependency_overrides[get_db_optional] = lambda: (yield None)
        self.client = TestClient(app, raise_server_exceptions=False)

    def teardown_method(self):
        app.dependency_overrides.pop(get_db_optional, None)

    def test_register_missing_email_422(self):
        """Missing email returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={"username": "user1", "password": "Pass123"},
        )
        assert response.status_code == 422

    def test_register_invalid_email_422(self):
        """Invalid email format returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "username": "user1", "password": "Pass123"},
        )
        assert response.status_code == 422

    def test_register_weak_password_no_digit_422(self):
        """Password without digit returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "username": "user1",
                "password": "onlyletters",
            },
        )
        assert response.status_code == 422

    def test_register_short_password_422(self):
        """Password shorter than min_length returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "u@example.com", "username": "user1", "password": "Sh1"},
        )
        assert response.status_code == 422

    def test_register_invalid_username_special_chars_422(self):
        """Username with space/special chars returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "username": "user name!",
                "password": "ValidPass1",
            },
        )
        assert response.status_code == 422

    def test_register_short_username_422(self):
        """Username shorter than 3 chars returns 422."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "u@example.com", "username": "ab", "password": "ValidPass1"},
        )
        assert response.status_code == 422

    def test_register_invalid_profession_422(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "username": "user1",
                "password": "ValidPass1",
                "profession": "admin",
            },
        )
        assert response.status_code == 422


# ==============================================================================
# 4. Role-based access control
# ==============================================================================

class TestRoleBasedAccess:
    def setup_method(self):
        app.dependency_overrides[get_db_optional] = lambda: (yield None)
        self.client = TestClient(app, raise_server_exceptions=False)

    def teardown_method(self):
        app.dependency_overrides.pop(get_db_optional, None)

    def test_admin_only_with_viewer_token(self):
        """Viewer token cannot reach admin-only endpoint."""
        token = create_access_token(subject=str(uuid.uuid4()), role="viewer")
        response = self.client.put(
            f"/api/v1/auth/users/{uuid.uuid4()}/role",
            params={"role": "radiologist"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_only_with_radiologist_token(self):
        """Radiologist token cannot reach admin-only endpoint."""
        token = create_access_token(subject=str(uuid.uuid4()), role="radiologist")
        response = self.client.put(
            f"/api/v1/auth/users/{uuid.uuid4()}/role",
            params={"role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_token_returns_503_when_no_db(self):
        """Admin token passes auth/role check but gets 503 when DB unavailable."""
        token = create_access_token(subject=str(uuid.uuid4()), role="admin")
        response = self.client.put(
            f"/api/v1/auth/users/{uuid.uuid4()}/role",
            params={"role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # 503 = passed auth+role check, DB unavailable
        assert response.status_code == 503


# ==============================================================================
# 5. Analysis endpoint backward compatibility
# ==============================================================================

class TestAnalysisAuthCompat:
    """Analysis endpoint requires authentication."""

    def setup_method(self):
        # Keep DB override so analysis tests don't try to persist to DB
        app.dependency_overrides[get_db_optional] = lambda: (yield None)
        self.client = TestClient(app, raise_server_exceptions=False)

    def teardown_method(self):
        app.dependency_overrides.pop(get_db_optional, None)

    def test_analysis_requires_authentication(self):
        """Analysis endpoint accepts requests without Bearer token."""
        import io
        import numpy as np
        from PIL import Image as PILImage

        arr = (np.zeros((32, 32), dtype=np.uint8) + 50)
        arr[10:20, 10:20] = 230
        img = PILImage.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        response = self.client.post(
            "/api/v1/analysis",
            files={"file": ("test.png", buf.getvalue(), "image/png")},
        )
        assert response.status_code == 401

    def test_analysis_also_works_with_bearer_token(self):
        """Analysis endpoint accepts requests with valid Bearer token."""
        import io
        import numpy as np
        from PIL import Image as PILImage

        arr = (np.zeros((32, 32), dtype=np.uint8) + 50)
        img = PILImage.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        token = create_access_token(subject=str(uuid.uuid4()), role="radiologist")
        response = self.client.post(
            "/api/v1/analysis",
            files={"file": ("test.png", buf.getvalue(), "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
