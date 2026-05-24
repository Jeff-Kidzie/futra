"""
RED phase tests for Task 1: Project scaffolding and foundation modules.

These tests verify the contracts defined in 01-01-PLAN.md. They MUST FAIL
before any implementation exists — this is the TDD RED gate.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import pytest

# Ensure project root is on the path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Test Helpers API contract (Test 1 from plan)
# ---------------------------------------------------------------------------

class TestHelpersContract:
    """Verify the test_helpers module exposes the required API."""

    def test_module_imports(self):
        """test_helpers module should be importable."""
        from tests.ea import test_helpers  # noqa: F401

    def test_create_ipc_dir_signature(self):
        """create_ipc_dir(base_path: Path) -> Path must exist."""
        from tests.ea.test_helpers import create_ipc_dir

        assert callable(create_ipc_dir)

    def test_cleanup_ipc_dir_signature(self):
        """cleanup_ipc_dir(base_path: Path) must exist."""
        from tests.ea.test_helpers import cleanup_ipc_dir

        assert callable(cleanup_ipc_dir)

    def test_write_kill_switch_signature(self):
        """write_kill_switch(base_path, active, close_positions, reason) -> Path."""
        from tests.ea.test_helpers import write_kill_switch

        assert callable(write_kill_switch)

    def test_write_symbol_params_signature(self):
        """write_symbol_params(base_path, symbol, sl_percent, tp_percent, max_position_size, ...) -> Path."""
        from tests.ea.test_helpers import write_symbol_params

        assert callable(write_symbol_params)

    def test_read_trade_log_signature(self):
        """read_trade_log(base_path: Path) -> list[dict]."""
        from tests.ea.test_helpers import read_trade_log

        assert callable(read_trade_log)

    def test_read_ea_state_signature(self):
        """read_ea_state(base_path: Path) -> dict | None."""
        from tests.ea.test_helpers import read_ea_state

        assert callable(read_ea_state)

    def test_temp_ipc_dir_fixture(self):
        """temp_ipc_dir should be a pytest fixture (conftest or test_helpers)."""
        from tests.ea.test_helpers import temp_ipc_dir


class TestHelpersBehavior:
    """Verify the test_helpers functions behave correctly at the contract level."""

    def test_create_and_cleanup_ipc_dir(self, tmp_path):
        """create_ipc_dir creates Futra/ subdirectory, cleanup removes it."""
        from tests.ea.test_helpers import cleanup_ipc_dir, create_ipc_dir

        ipc_dir = create_ipc_dir(tmp_path)
        assert ipc_dir.exists()
        assert ipc_dir.is_dir()
        assert ipc_dir.name == "Futra"

        cleanup_ipc_dir(tmp_path)
        assert not ipc_dir.exists()

    def test_write_kill_switch_creates_valid_json(self, tmp_path):
        """write_kill_switch writes valid JSON matching the IPC contract."""
        from tests.ea.test_helpers import create_ipc_dir, write_kill_switch

        ipc_dir = create_ipc_dir(tmp_path)
        ks_path = write_kill_switch(
            tmp_path, active=True, close_positions=True, reason="test_emergency"
        )

        assert ks_path.exists()
        content = json.loads(ks_path.read_text())
        assert content["active"] is True
        assert content["close_positions"] is True
        assert content["reason"] == "test_emergency"
        assert "timestamp" in content

    def test_write_kill_switch_no_close(self, tmp_path):
        """write_kill_switch with close_positions=False."""
        from tests.ea.test_helpers import create_ipc_dir, write_kill_switch

        create_ipc_dir(tmp_path)
        ks_path = write_kill_switch(
            tmp_path, active=True, close_positions=False, reason="pause"
        )

        content = json.loads(ks_path.read_text())
        assert content["active"] is True
        assert content["close_positions"] is False

    def test_write_kill_switch_inactive(self, tmp_path):
        """write_kill_switch with active=False."""
        from tests.ea.test_helpers import create_ipc_dir, write_kill_switch

        create_ipc_dir(tmp_path)
        ks_path = write_kill_switch(
            tmp_path, active=False, close_positions=False, reason="resume"
        )

        content = json.loads(ks_path.read_text())
        assert content["active"] is False

    def test_write_symbol_params_creates_valid_json(self, tmp_path):
        """write_symbol_params writes valid JSON matching IPC contract."""
        from tests.ea.test_helpers import create_ipc_dir, write_symbol_params

        create_ipc_dir(tmp_path)
        params_path = write_symbol_params(
            tmp_path,
            symbol="EURUSD",
            sl_percent=1.5,
            tp_percent=3.0,
            max_position_size=0.1,
            regime="trending",
            confidence=0.85,
        )

        assert params_path.exists()
        assert params_path.name == "EURUSD_params.json"
        content = json.loads(params_path.read_text())
        assert content["symbol"] == "EURUSD"
        assert content["sl_percent"] == 1.5
        assert content["tp_percent"] == 3.0
        assert content["max_position_size"] == 0.1
        assert content["regime"] == "trending"
        assert content["confidence"] == 0.85
        assert "timestamp" in content

    def test_read_trade_log_parses_jsonl(self, tmp_path):
        """read_trade_log reads JSONL trade log entries."""
        from tests.ea.test_helpers import create_ipc_dir, read_trade_log

        ipc_dir = create_ipc_dir(tmp_path)
        entries = [
            {"ticket": 12345, "symbol": "EURUSD", "type": "buy", "volume": 0.1},
            {"ticket": 12346, "symbol": "GBPUSD", "type": "sell", "volume": 0.05},
        ]
        log_path = ipc_dir / "trade_log.jsonl"
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = read_trade_log(tmp_path)
        assert len(result) == 2
        assert result[0]["ticket"] == 12345
        assert result[1]["symbol"] == "GBPUSD"

    def test_read_trade_log_empty_file(self, tmp_path):
        """read_trade_log returns empty list for missing or empty file."""
        from tests.ea.test_helpers import create_ipc_dir, read_trade_log

        ipc_dir = create_ipc_dir(tmp_path)
        result = read_trade_log(tmp_path)
        assert result == []

    def test_read_ea_state_returns_none_when_missing(self, tmp_path):
        """read_ea_state returns None when file doesn't exist."""
        from tests.ea.test_helpers import create_ipc_dir, read_ea_state

        create_ipc_dir(tmp_path)
        result = read_ea_state(tmp_path)
        assert result is None

    def test_read_ea_state_reads_existing_file(self, tmp_path):
        """read_ea_state reads ea_state.json when it exists."""
        from tests.ea.test_helpers import create_ipc_dir, read_ea_state

        ipc_dir = create_ipc_dir(tmp_path)
        state = {"status": "running", "last_tick": "2026-05-24T12:00:00Z"}
        (ipc_dir / "ea_state.json").write_text(json.dumps(state))

        result = read_ea_state(tmp_path)
        assert result is not None
        assert result["status"] == "running"


# ---------------------------------------------------------------------------
# MQL5 file contract tests (Tests 2-4 from plan)
# ---------------------------------------------------------------------------

EA_DIR = PROJECT_ROOT / "ea"
COMMON_MQH = EA_DIR / "include" / "Common.mqh"
CONFIG_MQH = EA_DIR / "include" / "Config.mqh"
FUTRA_MQ5 = EA_DIR / "FutraEA.mq5"


class TestCommonMqh:
    """Verify Common.mqh defines the required shared types and constants."""

    def test_file_exists(self):
        assert COMMON_MQH.exists(), f"Missing: {COMMON_MQH}"

    def test_has_property_strict(self):
        content = COMMON_MQH.read_text()
        assert "#property strict" in content

    def test_has_kill_switch_state_enum(self):
        content = COMMON_MQH.read_text()
        assert "ENUM_KILL_SWITCH_STATE" in content
        assert "KS_INACTIVE" in content
        assert "KS_ACTIVE_NO_CLOSE" in content
        assert "KS_ACTIVE_CLOSE_ALL" in content

    def test_has_trade_direction_enum(self):
        content = COMMON_MQH.read_text()
        assert "ENUM_TRADE_DIRECTION" in content
        assert "TRADE_BUY" in content
        assert "TRADE_SELL" in content

    def test_has_trade_result_struct(self):
        content = COMMON_MQH.read_text()
        assert "struct TradeResult" in content
        for field in ["ticket", "symbol", "type", "volume", "price",
                       "sl", "tp", "retcode", "comment", "timestamp"]:
            assert field in content, f"TradeResult missing field: {field}"

    def test_has_position_info_struct(self):
        content = COMMON_MQH.read_text()
        assert "struct PositionInfo" in content
        for field in ["ticket", "symbol", "type", "volume", "openPrice",
                       "sl", "tp", "profit"]:
            assert field in content, f"PositionInfo missing field: {field}"

    def test_has_ipc_path_constants(self):
        content = COMMON_MQH.read_text()
        assert "IPC_DIRECTORY" in content
        assert "KILL_SWITCH_FILE" in content
        assert "TRADE_LOG_FILE" in content
        assert "EA_STATE_FILE" in content


class TestConfigMqh:
    """Verify Config.mqh defines hardcoded safe default parameters."""

    def test_file_exists(self):
        assert CONFIG_MQH.exists(), f"Missing: {CONFIG_MQH}"

    def test_has_property_strict(self):
        content = CONFIG_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common(self):
        content = CONFIG_MQH.read_text()
        assert 'include "Common.mqh"' in content

    def test_has_safe_default_sl(self):
        content = CONFIG_MQH.read_text()
        assert "InpSafeDefaultSLPercent" in content
        assert "input double" in content

    def test_has_safe_default_tp(self):
        content = CONFIG_MQH.read_text()
        assert "InpSafeDefaultTPPercent" in content

    def test_has_max_position_size(self):
        content = CONFIG_MQH.read_text()
        assert "InpMaxPositionSize" in content

    def test_has_kill_switch_timeout(self):
        content = CONFIG_MQH.read_text()
        assert "InpKillSwitchTimeoutMinutes" in content

    def test_has_params_staleness(self):
        content = CONFIG_MQH.read_text()
        assert "InpParamsStalenessSeconds" in content

    def test_has_symbols_list(self):
        content = CONFIG_MQH.read_text()
        assert "InpSymbols" in content

    def test_has_magic_number(self):
        content = CONFIG_MQH.read_text()
        assert "InpMagicNumber" in content


class TestFutraEA:
    """Verify FutraEA.mq5 skeleton with all includes and stub functions."""

    def test_file_exists(self):
        assert FUTRA_MQ5.exists(), f"Missing: {FUTRA_MQ5}"

    def test_has_property_blocks(self):
        content = FUTRA_MQ5.read_text()
        assert "#property copyright" in content
        assert "#property version" in content

    def test_includes_all_modules(self):
        """Must include all 6 module headers."""
        content = FUTRA_MQ5.read_text()
        expected_includes = [
            "Common.mqh",
            "Config.mqh",
            "Logger.mqh",
            "KillSwitch.mqh",
            "OrderManager.mqh",
            "IPCReader.mqh",
        ]
        for inc in expected_includes:
            assert f'include "include/{inc}"' in content, \
                f"Missing include: {inc}"

    def test_has_on_init_stub(self):
        content = FUTRA_MQ5.read_text()
        assert "OnInit" in content
        assert "INIT_SUCCEEDED" in content

    def test_has_on_deinit_stub(self):
        content = FUTRA_MQ5.read_text()
        assert "OnDeinit" in content

    def test_has_on_tick_stub(self):
        content = FUTRA_MQ5.read_text()
        assert "OnTick" in content


# ---------------------------------------------------------------------------
# IPC Contract verification (from plan <interfaces>)
# ---------------------------------------------------------------------------

class TestIPCDirectoryContract:
    """Verify IPC directory and file path conventions match the plan."""

    def test_kill_switch_path_constant(self):
        content = COMMON_MQH.read_text() if COMMON_MQH.exists() else ""
        assert "Futra/" in content or "IPC_DIRECTORY" in content

    def test_kill_switch_json_contract(self, tmp_path):
        """Kill switch JSON format matches the contract."""
        from tests.ea.test_helpers import create_ipc_dir, write_kill_switch

        create_ipc_dir(tmp_path)
        ks_path = write_kill_switch(
            tmp_path, active=True, close_positions=True, reason="manual_emergency"
        )
        data = json.loads(ks_path.read_text())

        required_keys = {"active", "close_positions", "reason", "timestamp"}
        assert required_keys.issubset(data.keys()), \
            f"Missing keys: {required_keys - set(data.keys())}"

    def test_symbol_params_json_contract(self, tmp_path):
        """Per-symbol params JSON format matches the contract."""
        from tests.ea.test_helpers import create_ipc_dir, write_symbol_params

        create_ipc_dir(tmp_path)
        params_path = write_symbol_params(
            tmp_path, symbol="EURUSD", sl_percent=0.02, tp_percent=0.04,
            max_position_size=0.1, regime="trending", confidence=0.85
        )
        data = json.loads(params_path.read_text())

        required_keys = {"symbol", "timestamp", "sl_percent", "tp_percent",
                          "max_position_size", "regime", "confidence"}
        assert required_keys.issubset(data.keys()), \
            f"Missing keys: {required_keys - set(data.keys())}"

    def test_trade_log_jsonl_contract(self, tmp_path):
        """Trade log JSONL format matches the contract."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(tmp_path)
        entry = {
            "ticket": 12345, "symbol": "EURUSD", "type": "buy",
            "volume": 0.1, "price": 1.0850, "sl": 1.0830, "tp": 1.0890,
            "retcode": 10009, "comment": "", "timestamp": "2026-05-24T12:00:01Z"
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            line = f.readline().strip()
            parsed = json.loads(line)

        required_keys = {"ticket", "symbol", "type", "volume", "price",
                          "sl", "tp", "retcode", "comment", "timestamp"}
        assert required_keys.issubset(parsed.keys()), \
            f"Missing keys: {required_keys - set(parsed.keys())}"
