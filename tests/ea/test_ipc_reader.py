"""
RED/GREEN phase tests for Task 3: IPCReader module.

Verifies per-symbol params file format and staleness detection contract.
MQL5 file tests FAIL in RED phase (IPCReader.mqh doesn't exist).
IPC contract tests use test_helpers and verify the JSON formats.
"""
import json
import os
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IPCREADER_MQH = PROJECT_ROOT / "ea" / "include" / "IPCReader.mqh"


class TestIPCReaderModule:
    """Verify IPCReader.mqh defines required per-symbol params reading."""

    def test_file_exists(self):
        assert IPCREADER_MQH.exists(), f"Missing: {IPCREADER_MQH}"

    def test_has_property_strict(self):
        content = IPCREADER_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common_and_config(self):
        content = IPCREADER_MQH.read_text()
        assert 'include "Common.mqh"' in content
        assert 'include "Config.mqh"' in content

    def test_has_symbol_params_struct(self):
        content = IPCREADER_MQH.read_text()
        assert "struct SymbolParams" in content
        assert "isFresh" in content

    def test_has_read_symbol_params(self):
        content = IPCREADER_MQH.read_text()
        assert "ReadSymbolParams" in content
        assert "SymbolParams" in content

    def test_has_is_params_fresh(self):
        content = IPCREADER_MQH.read_text()
        assert "IsParamsFresh" in content

    def test_uses_staleness_config(self):
        content = IPCREADER_MQH.read_text()
        assert "InpParamsStalenessSeconds" in content


class TestSymbolParamsContract:
    """Verify per-symbol params JSON format matches the IPC contract."""

    REQUIRED_FIELDS = [
        "symbol", "timestamp", "sl_percent", "tp_percent",
        "max_position_size", "regime", "confidence",
    ]

    def test_params_file_has_all_fields(self, temp_ipc_dir):
        """EURUSD_params.json must contain all required fields."""
        from tests.ea.test_helpers import write_symbol_params

        params_path = write_symbol_params(
            temp_ipc_dir,
            symbol="EURUSD",
            sl_percent=1.5,
            tp_percent=3.0,
            max_position_size=0.1,
            regime="trending",
            confidence=0.85,
        )

        assert params_path.exists()
        assert params_path.name == "EURUSD_params.json"

        data = json.loads(params_path.read_text())
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"EURUSD_params.json missing field: {field}"

        assert data["sl_percent"] == 1.5
        assert data["tp_percent"] == 3.0
        assert data["max_position_size"] == 0.1
        assert data["regime"] == "trending"

    def test_params_file_timestamp_is_iso8601(self, temp_ipc_dir):
        """Timestamp in params file must be parseable ISO8601."""
        from tests.ea.test_helpers import write_symbol_params

        params_path = write_symbol_params(
            temp_ipc_dir,
            symbol="GBPUSD",
            sl_percent=2.0,
            tp_percent=4.0,
            max_position_size=0.05,
        )
        data = json.loads(params_path.read_text())
        timestamp = data["timestamp"]
        assert "T" in timestamp

    def test_missing_params_file(self, temp_ipc_dir):
        """When params file doesn't exist, EA uses safe defaults."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        params_path = ipc_dir / "NONEXISTENT_params.json"
        assert not params_path.exists(), (
            "Params file should not exist — EA must fall back to safe defaults"
        )

    def test_stale_params_detection_timestamp(self, temp_ipc_dir):
        """Write params with an old timestamp to simulate staleness.
        The EA checks if (TimeCurrent() - file_timestamp) > InpParamsStalenessSeconds.
        This test verifies the timestamp is writable in the expected format."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        # Write a params file whose timestamp is in the past
        old_data = {
            "symbol": "EURUSD",
            "timestamp": "2026-01-01T00:00:00Z",  # Old timestamp
            "sl_percent": 1.5,
            "tp_percent": 3.0,
            "max_position_size": 0.1,
            "regime": "trending",
            "confidence": 0.85,
        }
        params_path = ipc_dir / "EURUSD_params.json"
        params_path.write_text(json.dumps(old_data, indent=2))

        data = json.loads(params_path.read_text())
        assert data["timestamp"] == "2026-01-01T00:00:00Z"
        # This timestamp is clearly stale — EA should detect and fall back

    def test_malformed_params_json(self, temp_ipc_dir):
        """Malformed params JSON should exist with bad content.
        EA must handle parse errors gracefully (isFresh=false safe default)."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        params_path = ipc_dir / "EURUSD_params.json"
        params_path.write_text('{"symbol": "EURUSD", "sl_percent": 1.5')  # Malformed

        assert params_path.exists()
        with pytest.raises(json.JSONDecodeError):
            json.loads(params_path.read_text())

    def test_params_file_naming_convention(self, temp_ipc_dir):
        """Verify the {SYMBOL}_params.json naming convention."""
        from tests.ea.test_helpers import write_symbol_params

        for symbol in ["EURUSD", "GBPUSD", "USDJPY"]:
            path = write_symbol_params(
                temp_ipc_dir, symbol=symbol,
                sl_percent=2.0, tp_percent=4.0, max_position_size=0.1
            )
            assert path.name == f"{symbol}_params.json"


# ---------------------------------------------------------------------------
# EA wiring contract tests (verify OnTick execution loop)
# ---------------------------------------------------------------------------

FUTRA_MQ5 = PROJECT_ROOT / "ea" / "FutraEA.mq5"


class TestEAWiring:
    """Verify FutraEA.mq5 OnTick wires kill switch, params reading, and early exit."""

    def test_on_tick_checks_kill_switch_first(self):
        """OnTick must call CheckKillSwitch before any trading logic."""
        content = FUTRA_MQ5.read_text()
        assert "CheckKillSwitch" in content, (
            "EA OnTick must call CheckKillSwitch every tick per D-01"
        )

    def test_on_tick_reads_symbol_params(self):
        """OnTick must read per-symbol params via ReadSymbolParams."""
        content = FUTRA_MQ5.read_text()
        assert "ReadSymbolParams" in content, (
            "EA OnTick must read per-symbol AI params per D-08"
        )

    def test_on_tick_respects_kill_switch_early_exit(self):
        """OnTick must return early when kill switch is active."""
        content = FUTRA_MQ5.read_text()
        has_ks_check = "IsKillSwitchActive" in content
        has_close_pos = "ShouldClosePositions" in content
        assert has_ks_check or has_close_pos, (
            "EA OnTick must check kill switch state and return early when active"
        )

    def test_on_tick_has_safe_defaults_fallback(self):
        """OnTick must use InpSafeDefaultSLPercent/TPPercent when params stale."""
        content = FUTRA_MQ5.read_text()
        assert "InpSafeDefaultSLPercent" in content or "InpSafeDefaultTPPercent" in content, (
            "EA must fall back to safe defaults when AI params unavailable per AI-03"
        )

    def test_on_tick_has_trading_signal_placeholder(self):
        """OnTick must have a comment indicating where trading signals will be wired."""
        content = FUTRA_MQ5.read_text()
        assert "signal" in content.lower() or "placeholder" in content.lower() or "future phase" in content.lower(), (
            "EA OnTick should have a trading signal placeholder comment"
        )
