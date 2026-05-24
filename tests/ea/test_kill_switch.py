"""
RED/GREEN phase tests for Task 2: Kill switch module and Logger module.

Verifies the IPC contract for kill switch behavior and trade logging.
Also checks MQL5 file existence and required function signatures.

The MQL5 file tests FAIL in RED phase (files don't exist).
The IPC contract tests use test_helpers and verify the JSON formats
that the EA reads/writes through its file-based interface.
"""
import json
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# MQL5 file contract tests (RED: these fail until Logger/KillSwitch exist)
# ---------------------------------------------------------------------------

LOGGER_MQH = PROJECT_ROOT / "ea" / "include" / "Logger.mqh"
KILLSWITCH_MQH = PROJECT_ROOT / "ea" / "include" / "KillSwitch.mqh"


class TestLoggerModule:
    """Verify Logger.mqh defines required logging functions."""

    def test_file_exists(self):
        assert LOGGER_MQH.exists(), f"Missing: {LOGGER_MQH}"

    def test_has_property_strict(self):
        content = LOGGER_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common(self):
        content = LOGGER_MQH.read_text()
        assert 'include "Common.mqh"' in content

    def test_has_log_trade(self):
        content = LOGGER_MQH.read_text()
        assert "void LogTrade" in content
        assert "TradeResult" in content

    def test_has_log_error(self):
        content = LOGGER_MQH.read_text()
        assert "void LogError" in content

    def test_has_log_info(self):
        content = LOGGER_MQH.read_text()
        assert "void LogInfo" in content

    def test_has_get_timestamp(self):
        content = LOGGER_MQH.read_text()
        assert "GetCurrentTimestamp" in content or "string Get" in content


class TestKillSwitchModule:
    """Verify KillSwitch.mqh defines required kill switch functions."""

    def test_file_exists(self):
        assert KILLSWITCH_MQH.exists(), f"Missing: {KILLSWITCH_MQH}"

    def test_has_property_strict(self):
        content = KILLSWITCH_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common_and_config(self):
        content = KILLSWITCH_MQH.read_text()
        assert 'include "Common.mqh"' in content
        assert 'include "Config.mqh"' in content
        assert 'include "Logger.mqh"' in content

    def test_has_check_kill_switch(self):
        content = KILLSWITCH_MQH.read_text()
        assert "CheckKillSwitch" in content
        assert "ENUM_KILL_SWITCH_STATE" in content

    def test_has_is_kill_switch_active(self):
        content = KILLSWITCH_MQH.read_text()
        assert "IsKillSwitchActive" in content

    def test_has_should_close_positions(self):
        content = KILLSWITCH_MQH.read_text()
        assert "ShouldClosePositions" in content

    def test_uses_kill_switch_file_constant(self):
        content = KILLSWITCH_MQH.read_text()
        assert "KILL_SWITCH_FILE" in content

    def test_uses_timeout_config(self):
        content = KILLSWITCH_MQH.read_text()
        assert "InpKillSwitchTimeoutMinutes" in content


# ---------------------------------------------------------------------------
# Kill switch IPC contract tests (verify file format, not EA runtime)
# ---------------------------------------------------------------------------

class TestKillSwitchContract:
    """Verify kill_switch.json format matches the IPC contract."""

    def test_active_with_close_writes_correct_json(self, temp_ipc_dir):
        """Kill switch active=true, close_positions=true -> valid JSON."""
        from tests.ea.test_helpers import write_kill_switch

        ks_path = write_kill_switch(
            temp_ipc_dir, active=True, close_positions=True, reason="test_emergency"
        )
        data = json.loads(ks_path.read_text())
        assert data["active"] is True
        assert data["close_positions"] is True
        assert "timestamp" in data
        assert "reason" in data

    def test_active_no_close_writes_correct_json(self, temp_ipc_dir):
        """Kill switch active=true, close_positions=false -> valid JSON."""
        from tests.ea.test_helpers import write_kill_switch

        ks_path = write_kill_switch(
            temp_ipc_dir, active=True, close_positions=False, reason="pause"
        )
        data = json.loads(ks_path.read_text())
        assert data["active"] is True
        assert data["close_positions"] is False

    def test_inactive_writes_correct_json(self, temp_ipc_dir):
        """Kill switch active=false -> valid JSON."""
        from tests.ea.test_helpers import write_kill_switch

        ks_path = write_kill_switch(
            temp_ipc_dir, active=False, close_positions=False, reason="resume"
        )
        data = json.loads(ks_path.read_text())
        assert data["active"] is False

    def test_missing_file_means_inactive(self, temp_ipc_dir):
        """When kill_switch.json doesn't exist, EA treats as inactive."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        ks_path = ipc_dir / "kill_switch.json"
        # File should NOT exist — EA treats this as KS_INACTIVE
        assert not ks_path.exists(), (
            "kill_switch.json should not exist — EA must treat missing file as inactive"
        )

    def test_malformed_json_file_exists(self, temp_ipc_dir):
        """Malformed kill_switch.json should exist with bad content.
        EA must handle parse errors gracefully (KS_INACTIVE safe default)."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        ks_path = ipc_dir / "kill_switch.json"
        # Write malformed JSON (missing closing brace)
        ks_path.write_text('{"active": true, "close_positions": true')
        assert ks_path.exists()
        content = ks_path.read_text()
        # Prove it's malformed
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)

    def test_timeout_timestamp_format(self, temp_ipc_dir):
        """Verify kill switch timestamp is in ISO8601 format for auto-reset."""
        from tests.ea.test_helpers import write_kill_switch

        ks_path = write_kill_switch(
            temp_ipc_dir, active=True, close_positions=True, reason="timeout_test"
        )
        data = json.loads(ks_path.read_text())
        timestamp = data["timestamp"]
        # Must be ISO8601 format: YYYY-MM-DDTHH:MM:SSZ
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[10:]
        # Should be parseable as a date
        from datetime import datetime
        # Strip timezone for parsing
        ts_clean = timestamp.replace("Z", "+00:00")
        datetime.fromisoformat(ts_clean)


# ---------------------------------------------------------------------------
# Trade log contract tests (verify JSONL format)
# ---------------------------------------------------------------------------

class TestTradeLogContract:
    """Verify trade_log.jsonl format matches TradeResult struct."""

    TRADE_RESULT_FIELDS = [
        "ticket", "symbol", "type", "volume", "price",
        "sl", "tp", "retcode", "comment", "timestamp",
    ]

    def test_log_entry_has_all_fields(self, temp_ipc_dir):
        """A trade log JSON line must contain all TradeResult fields."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "buy",
            "volume": 0.1,
            "price": 1.0850,
            "sl": 1.0830,
            "tp": 1.0890,
            "retcode": 10009,
            "comment": "",
            "timestamp": "2026-05-24T12:00:01Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        for field in self.TRADE_RESULT_FIELDS:
            assert field in parsed, f"Trade log entry missing field: {field}"

    def test_multiple_log_entries(self, temp_ipc_dir):
        """Multiple JSONL entries should each be valid."""
        from tests.ea.test_helpers import create_ipc_dir, read_trade_log

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entries = [
            {"ticket": 100, "symbol": "EURUSD", "type": "buy", "volume": 0.1,
             "price": 1.08, "sl": 1.07, "tp": 1.09, "retcode": 10009,
             "comment": "", "timestamp": "2026-05-24T12:00:00Z"},
            {"ticket": 101, "symbol": "GBPUSD", "type": "sell", "volume": 0.05,
             "price": 1.25, "sl": 1.26, "tp": 1.24, "retcode": 10009,
             "comment": "", "timestamp": "2026-05-24T12:00:05Z"},
        ]
        log_path = ipc_dir / "trade_log.jsonl"
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = read_trade_log(temp_ipc_dir)
        assert len(result) == 2
        assert result[0]["ticket"] == 100
        assert result[1]["ticket"] == 101

    def test_error_log_entry_format(self, temp_ipc_dir):
        """Error log entries must have level=error, context, errorCode, details."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        error_entry = {
            "level": "error",
            "context": "OpenBuyOrder",
            "errorCode": 10016,
            "details": "Invalid stops",
            "timestamp": "2026-05-24T12:00:01Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(error_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert parsed["context"] == "OpenBuyOrder"
        assert "errorCode" in parsed
        assert "timestamp" in parsed
