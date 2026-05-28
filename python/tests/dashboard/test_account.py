"""Tests for /api/account endpoint."""
import pytest
from python.dashboard.api import _mt5_cache


@pytest.fixture
def mock_account_cache(monkeypatch):
    """Populate the MT5 cache with sample account data."""
    test_account = {
        "balance": 10000.0,
        "equity": 10050.0,
        "margin": 500.0,
        "free_margin": 9550.0,
        "daily_pnl": 50.0,
    }
    monkeypatch.setitem(_mt5_cache, "account", test_account)
    yield test_account
    monkeypatch.setitem(_mt5_cache, "account", None)


class TestAccount:
    """GET /api/account returns account summary."""

    def test_returns_account_info(self, client, auth_headers, mock_account_cache):
        """Test 3: Returns AccountInfo with balance, equity, margin, free_margin, daily_pnl."""
        response = client.get("/api/account", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 10000.0
        assert data["equity"] == 10050.0
        assert data["margin"] == 500.0
        assert data["free_margin"] == 9550.0
        assert data["daily_pnl"] == 50.0

    def test_returns_defaults_when_no_account(self, client, auth_headers):
        """Returns zeros when MT5 not connected."""
        response = client.get("/api/account", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == {"balance": 0, "equity": 0, "margin": 0, "free_margin": 0, "daily_pnl": 0}

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/account")
        assert response.status_code == 401
