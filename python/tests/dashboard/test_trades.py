"""Tests for /api/trades endpoint."""
import json
import pytest
from pathlib import Path
from python.dashboard.api.trades import TRADE_LOG_PATH, read_trades


@pytest.fixture
def temp_trade_log(tmp_path, monkeypatch):
    """Create a temporary trade_log.jsonl with known test data."""
    log_path = tmp_path / "Futra" / "trade_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "python.dashboard.api.trades.TRADE_LOG_PATH",
        log_path,
    )
    return log_path


def write_trade_log(log_path: Path, entries: list[dict]):
    """Write trade log entries as JSONL."""
    with open(log_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestTrades:
    """GET /api/trades returns paginated trade history."""

    def test_returns_trades(self, client, auth_headers, temp_trade_log):
        """Test 4: Returns trades from trade_log.jsonl."""
        entries = [
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-26T10:15:00Z"},
            {"event": "trade_close", "ticket": 1, "profit": 50.0, "close_price": 1.0900,
             "timestamp": "2026-05-26T12:30:00Z"},
            {"event": "trade_open", "symbol": "GBPUSD", "ticket": 2, "direction": "sell",
             "volume": 0.05, "price": 1.2650, "sl": 1.2680, "tp": 1.2600,
             "timestamp": "2026-05-26T14:00:00Z"},
            {"event": "trade_close", "ticket": 2, "profit": -30.0, "close_price": 1.2680,
             "timestamp": "2026-05-26T15:00:00Z"},
        ]
        write_trade_log(temp_trade_log, entries)

        response = client.get("/api/trades?limit=10&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ticket"] == 2  # Most recent first
        assert data[0]["profit"] == -30.0
        assert data[1]["ticket"] == 1
        assert data[1]["profit"] == 50.0

    def test_pagination_limit(self, client, auth_headers, temp_trade_log):
        """Limit parameter works correctly."""
        entries = []
        for i in range(5):
            entries.append({"event": "trade_open", "symbol": "EURUSD", "ticket": i,
                           "direction": "buy", "volume": 0.1, "price": 1.08,
                           "sl": 1.07, "tp": 1.09, "timestamp": f"2026-05-26T1{i}:00:00Z"})
            entries.append({"event": "trade_close", "ticket": i, "profit": 10.0,
                           "close_price": 1.09, "timestamp": f"2026-05-26T1{i}:30:00Z"})
        write_trade_log(temp_trade_log, entries)

        response = client.get("/api/trades?limit=2&offset=0", headers=auth_headers)
        data = response.json()
        assert len(data) == 2

    def test_offset_beyond_log(self, client, auth_headers, temp_trade_log):
        """Test 5: Offset beyond log returns empty list."""
        entries = [
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-26T10:15:00Z"},
            {"event": "trade_close", "ticket": 1, "profit": 50.0, "close_price": 1.0900,
             "timestamp": "2026-05-26T12:30:00Z"},
        ]
        write_trade_log(temp_trade_log, entries)

        response = client.get("/api/trades?limit=10&offset=100", headers=auth_headers)
        data = response.json()
        assert data == []

    def test_empty_log_file(self, client, auth_headers, temp_trade_log):
        """Empty or missing log returns empty list."""
        # File exists but is empty
        response = client.get("/api/trades", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_malformed_lines_skipped(self, client, auth_headers, temp_trade_log):
        """Malformed JSON lines are skipped with a warning."""
        content = (
            '{"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",'
            ' "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,'
            ' "timestamp": "2026-05-26T10:15:00Z"}\n'
            'this is not json\n'
            '{"event": "trade_close", "ticket": 1, "profit": 50.0, "close_price": 1.0900,'
            ' "timestamp": "2026-05-26T12:30:00Z"}\n'
        )
        temp_trade_log.write_text(content)

        response = client.get("/api/trades", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only the valid trade pair

    def test_requires_auth(self, client):
        """Returns 401 without token."""
        response = client.get("/api/trades")
        assert response.status_code == 401

    def test_trade_has_required_fields(self, client, auth_headers, temp_trade_log):
        """Trade objects contain all expected fields."""
        entries = [
            {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
             "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
             "timestamp": "2026-05-26T10:15:00Z"},
            {"event": "trade_close", "ticket": 1, "profit": 50.0, "close_price": 1.0900,
             "timestamp": "2026-05-26T12:30:00Z"},
        ]
        write_trade_log(temp_trade_log, entries)

        response = client.get("/api/trades", headers=auth_headers)
        data = response.json()
        trade = data[0]
        expected = ["ticket", "symbol", "direction", "entry_price", "exit_price",
                     "profit", "open_time", "close_time", "duration", "regime"]
        for field in expected:
            assert field in trade, f"Missing field: {field}"
