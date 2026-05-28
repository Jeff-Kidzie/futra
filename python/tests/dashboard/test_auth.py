"""Tests for authentication system.

Tests cover: login success/failure, token validation, token expiry,
logout invalidation, missing token, expired token, bcrypt verification.
"""
import pytest
import time
import secrets
import bcrypt
from fastapi.testclient import TestClient


class TestLoginSuccess:
    """POST /api/auth/login with correct credentials returns token."""

    def test_login_returns_token_and_expires_at(self, client, test_user):
        """Test 1: Login returns 200 with token and expires_at."""
        username, password = test_user
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) == 64  # secrets.token_hex(32) = 64 hex chars
        assert "expires_at" in data

    def test_login_token_is_usable(self, client, test_user):
        """Login token is accepted by require_auth dependency."""
        username, password = test_user
        login_resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        token = login_resp.json()["token"]
        # Use token on a protected endpoint
        response = client.get(
            "/api/positions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestLoginFailure:
    """POST /api/auth/login with wrong credentials returns 401."""

    def test_wrong_password_returns_401(self, client, test_user):
        """Test 2: Wrong password returns 401."""
        username, _ = test_user
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_wrong_username_returns_401(self, client):
        """Non-existent username returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "anything"},
        )
        assert response.status_code == 401

    def test_missing_credentials_returns_422(self, client):
        """Missing username/password returns validation error."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422


class TestAuthMiddleware:
    """require_auth dependency enforces token validation."""

    def test_no_token_returns_401(self, client):
        """Test 3: Request without token returns 401."""
        response = client.get("/api/positions")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """Malformed token returns 401."""
        response = client.get(
            "/api/positions",
            headers={"Authorization": "Bearer invalid_token_123"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, test_db, client, test_user, monkeypatch):
        """Test 5: Expired token returns 401."""
        username, password = test_user
        login_resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        token = login_resp.json()["token"]

        # Force the token to expire by modifying the sessions table
        test_db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            ("2000-01-01T00:00:00", token),
        )
        test_db.commit()

        response = client.get(
            "/api/positions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_bearer_scheme_required(self, client):
        """Token without Bearer prefix returns 401."""
        response = client.get(
            "/api/positions",
            headers={"Authorization": "sometoken123"},
        )
        assert response.status_code == 401


class TestLogout:
    """POST /api/auth/logout invalidates token."""

    def test_logout_invalidates_token(self, client, test_user):
        """Test 6: After logout, token is no longer valid."""
        username, password = test_user
        login_resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        token = login_resp.json()["token"]

        # Logout
        logout_resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_resp.status_code == 200

        # Token should be rejected now
        response = client.get(
            "/api/positions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


class TestDBInit:
    """init_db() creates required tables."""

    def test_users_table_schema(self, test_db):
        """Test 7: users table has correct columns."""
        cursor = test_db.execute("PRAGMA table_info(users)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "INTEGER"
        assert "username" in columns
        assert "password_hash" in columns
        assert "created_at" in columns

    def test_sessions_table_schema(self, test_db):
        """Sessions table has correct columns."""
        cursor = test_db.execute("PRAGMA table_info(sessions)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "token" in columns
        assert "user_id" in columns
        assert "expires_at" in columns

    def test_alerts_table_schema(self, test_db):
        """Alerts table has correct columns."""
        cursor = test_db.execute("PRAGMA table_info(alerts)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "id" in columns
        assert "type" in columns
        assert "message" in columns
        assert "severity" in columns
        assert "acknowledged" in columns
        assert "created_at" in columns

    def test_init_idempotent(self, test_db):
        """Running init_db() twice does not raise an error."""
        from python.dashboard.db import init_db
        init_db()  # Should not raise


class TestPasswordSecurity:
    """Password storage uses bcrypt, not plaintext."""

    def test_password_hash_not_plaintext(self, test_db, test_user):
        """Test 8: Password is stored as bcrypt hash, not plaintext."""
        row = test_db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("testuser",),
        ).fetchone()
        assert row is not None
        stored = row["password_hash"]
        # bcrypt hashes start with $2b$ or $2a$
        assert stored.startswith("$2")
        assert stored != "testpassword123"

    def test_password_verified_with_bcrypt(self, test_db, test_user):
        """Stored hash can be verified with bcrypt."""
        username, password = test_user
        row = test_db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        stored = row["password_hash"]
        assert bcrypt.checkpw(password.encode(), stored.encode())

    def test_grep_bcrypt_usage(self):
        """Verify bcrypt is used in auth.py (hash and verify)."""
        import python.dashboard.auth as auth_module
        source = __import__("inspect").getsource(auth_module)
        assert "bcrypt" in source


class TestDefaultAdminUser:
    """First startup creates default admin if no users exist."""

    def test_default_admin_created_on_empty_db(self, client, test_db):
        """When users table is empty, init creates a default admin."""
        # Delete all users
        test_db.execute("DELETE FROM sessions")
        test_db.execute("DELETE FROM users")
        test_db.commit()

        from python.dashboard.db import init_db
        init_db()

        # Check admin user was created
        row = test_db.execute(
            "SELECT * FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        assert row is not None
        assert row["password_hash"].startswith("$2")
