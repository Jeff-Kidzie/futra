"""Tests for /api/positions endpoint."""
import pytest
from python.dashboard.api import _mt5_cache


@pytest.fixture
def mock_positions_cache(monkeypatch):
    """Populate the MT5 cache with sample position data."""
    test_positions = [
        {
            "ticket": 1001,
            "symbol": "EURUSD",
            "direction": "buy",
            "volume": 0.1,
            "open_price": 1.0850,
            "current_price": 1.0875,
            "sl": 1.0825,
            "tp": 1.0900,
            "profit": 25.0,
            "swap": -0.5,
            "open_time": "2026-05-26T10:15:00Z",
        },
        {
            "ticket": 1002,
            "symbol": "GBPUSD",
            "direction": "sell",
            "volume": 0.05,
            "open_price": 1.2650,
            "current_price": 1.2635,
            "sl": 1.2680,
            "tp": 1.2600,
            "profit": 7.5,
            "swap": -0.2,
            "open_time": "2026-05-26T11:30:00Z",
        },
    ]
    monkeypatch.setitem(_mt5_cache, "positions", test_positions)
    yield test_positions
    monkeypatch.setitem(_mt5_cache, "positions", [])


class TestPositions:
    """GET /api/positions returns current open positions."""

    def test_returns_positions_when_mt5_connected(self, client, auth_headers, mock_positions_cache):
        """Test 1: Returns list of Position objects when positions exist."""
        response = client.get("/api/positions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["symbol"] == "EURUSD"
        assert data[0]["ticket"] == 1001
        assert "profit" in data[0]

    def test_returns_empty_when_no_positions(self, client, auth_headers):
        """Test 2: Returns empty list when no positions open."""
        # Cache is empty by default (reset by mock_positions_cache teardown)
        response = client.get("/api/positions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/positions")
        assert response.status_code == 401

    def test_positions_have_all_fields(self, client, auth_headers, mock_positions_cache):
        """Position objects contain all expected fields."""
        response = client.get("/api/positions", headers=auth_headers)
        data = response.json()
        pos = data[0]
        expected_fields = ["ticket", "symbol", "direction", "volume", "open_price",
                          "current_price", "sl", "tp", "profit", "swap", "open_time"]
        for field in expected_fields:
            assert field in pos, f"Missing field: {field}"
