"""Test fixtures for dashboard tests."""
import pytest
import sqlite3
import os
import secrets
from pathlib import Path
import bcrypt
from fastapi.testclient import TestClient


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary dashboard.db path."""
    db_path = str(tmp_path / "dashboard.db")
    return db_path


@pytest.fixture
def test_db(test_db_path, monkeypatch):
    """Create a fresh dashboard.db with users, sessions, alerts tables."""
    # Patch the config value BEFORE importing dashboard modules
    monkeypatch.setattr("python.config.DASHBOARD_DB_PATH", Path(test_db_path))

    from python.dashboard.db import init_db, get_db
    init_db()

    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def test_user(test_db):
    """Insert a test user and return (username, password)."""
    password = "testpassword123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    test_db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("testuser", password_hash),
    )
    test_db.commit()
    return "testuser", password


@pytest.fixture
def client(test_db_path, monkeypatch):
    """Create a FastAPI TestClient with test database override."""
    monkeypatch.setattr("python.config.DASHBOARD_DB_PATH", Path(test_db_path))
    monkeypatch.setenv("FUTRA_DASHBOARD_DB", test_db_path)
    monkeypatch.setenv("FUTRA_DASHBOARD_DEV", "true")

    from python.dashboard.main import app
    from python.dashboard.db import init_db
    init_db()
    return TestClient(app)


@pytest.fixture
def auth_headers(client, test_user):
    """Log in with test user and return auth headers dict."""
    username, password = test_user
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['token']}"}
