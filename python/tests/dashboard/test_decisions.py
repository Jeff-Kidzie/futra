"""Tests for /api/decisions endpoint."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def temp_decision_log(tmp_path, monkeypatch):
    """Create a temporary decision_log.jsonl."""
    log_path = tmp_path / "decision_log.jsonl"
    monkeypatch.setattr(
        "python.dashboard.api.decisions.DECISION_LOG_PATH",
        log_path,
    )
    return log_path


def write_decision_log(log_path: Path, entries: list[dict]):
    """Write decision log entries as JSONL."""
    with open(log_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestDecisions:
    """GET /api/decisions returns paginated AI decision log."""

    def test_returns_decisions(self, client, auth_headers, temp_decision_log):
        """Returns decision entries from the log."""
        entries = [
            {"timestamp": "2026-05-26T10:14:00Z", "symbol": "EURUSD", "timeframe": "H1",
             "regime": "trending", "confidence": 0.87, "sl_pips": 25.0, "tp_pips": 50.0,
             "lot_size": 0.05, "reasoning": "Strong uptrend"},
            {"timestamp": "2026-05-26T11:00:00Z", "symbol": "GBPUSD", "timeframe": "H1",
             "regime": "ranging", "confidence": 0.65, "sl_pips": 20.0, "tp_pips": 35.0,
             "lot_size": 0.03, "reasoning": "Sideways market"},
        ]
        write_decision_log(temp_decision_log, entries)

        response = client.get("/api/decisions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "GBPUSD"  # Most recent first

    def test_symbol_filter(self, client, auth_headers, temp_decision_log):
        """Test 6: Filters by symbol correctly."""
        entries = [
            {"timestamp": "2026-05-26T10:14:00Z", "symbol": "EURUSD", "timeframe": "H1",
             "regime": "trending", "confidence": 0.87, "sl_pips": 25.0, "tp_pips": 50.0,
             "lot_size": 0.05, "reasoning": "Strong uptrend"},
            {"timestamp": "2026-05-26T11:00:00Z", "symbol": "GBPUSD", "timeframe": "H1",
             "regime": "ranging", "confidence": 0.65, "sl_pips": 20.0, "tp_pips": 35.0,
             "lot_size": 0.03, "reasoning": "Sideways market"},
        ]
        write_decision_log(temp_decision_log, entries)

        response = client.get("/api/decisions?symbol=EURUSD", headers=auth_headers)
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "EURUSD"

    def test_missing_file_returns_empty(self, client, auth_headers):
        """Test 7: When decision_log.jsonl doesn't exist, returns empty list."""
        response = client.get("/api/decisions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/decisions")
        assert response.status_code == 401

    def test_decision_has_required_fields(self, client, auth_headers, temp_decision_log):
        """Decision objects contain all expected fields."""
        entries = [
            {"timestamp": "2026-05-26T10:14:00Z", "symbol": "EURUSD", "timeframe": "H1",
             "regime": "trending", "confidence": 0.87, "sl_pips": 25.0, "tp_pips": 50.0,
             "lot_size": 0.05, "reasoning": "Strong uptrend"},
        ]
        write_decision_log(temp_decision_log, entries)

        response = client.get("/api/decisions", headers=auth_headers)
        data = response.json()
        decision = data[0]
        expected = ["timestamp", "symbol", "timeframe", "regime", "confidence",
                     "sl_pips", "tp_pips", "lot_size", "reasoning"]
        for field in expected:
            assert field in decision, f"Missing field: {field}"
