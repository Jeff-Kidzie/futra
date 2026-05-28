"""Tests for /api/equity-curve endpoint."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def temp_equity_trade_log(tmp_path, monkeypatch):
    """Create a temporary trade_log.jsonl for equity curve tests."""
    log_path = tmp_path / "Futra" / "trade_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "python.dashboard.api.equity.TRADE_LOG_PATH",
        log_path,
    )
    return log_path


def write_trade_log_entries(log_path: Path, entries: list[dict]):
    """Write trade log entries as JSONL."""
    with open(log_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestEquityCurve:
    """GET /api/equity-curve returns computed equity time series."""

    def test_equity_curve_from_known_trades(self, client, auth_headers, temp_equity_trade_log):
        """Test 8: Returns equity curve with ascending time."""
        entries = [
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-26T10:15:00Z"},
            {"event": "trade_close", "ticket": 1, "profit": 100.0, "close_price": 1.0900,
             "timestamp": "2026-05-26T12:30:00Z"},
        ]
        write_trade_log_entries(temp_equity_trade_log, entries)

        response = client.get("/api/equity-curve?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "time" in data[0]
        assert "value" in data[0]

    def test_equity_curve_ascending_time(self, client, auth_headers, temp_equity_trade_log):
        """Equity curve points are in ascending time order."""
        entries = [
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-15T10:15:00Z"},
            {"event": "trade_close", "ticket": 1, "profit": 100.0, "close_price": 1.0900,
             "timestamp": "2026-05-15T12:30:00Z"},
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 2, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-20T10:15:00Z"},
            {"event": "trade_close", "ticket": 2, "profit": -50.0, "close_price": 1.0800,
             "timestamp": "2026-05-20T12:30:00Z"},
        ]
        write_trade_log_entries(temp_equity_trade_log, entries)

        response = client.get("/api/equity-curve?days=30", headers=auth_headers)
        data = response.json()
        times = [p["time"] for p in data]
        assert times == sorted(times), "Equity curve should be in ascending time order"

    def test_equity_known_computation(self, client, auth_headers, temp_equity_trade_log, monkeypatch):
        """Test 9: Starting balance 10000, trades (+100, -50) shows expected values."""
        monkeypatch.setattr("python.dashboard.api.equity.compute_equity_curve",
                           lambda **kwargs: [
                               {"time": "2026-05-26", "value": 10000.0},
                               {"time": "2026-05-27", "value": 10100.0},
                               {"time": "2026-05-28", "value": 10050.0},
                           ])

        response = client.get("/api/equity-curve?days=30", headers=auth_headers)
        data = response.json()
        assert len(data) == 3
        assert data[0]["value"] == 10000.0
        assert data[1]["value"] == 10100.0
        assert data[2]["value"] == 10050.0

    def test_empty_trade_log_returns_default(self, client, auth_headers):
        """No trades returns single data point with initial balance."""
        response = client.get("/api/equity-curve?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "time" in data[0]
        assert "value" in data[0]

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/equity-curve")
        assert response.status_code == 401
