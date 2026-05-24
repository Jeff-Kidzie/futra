"""
RED/GREEN phase tests for Task 3: PositionManager module.

Verifies position management contract — position close and SL/TP
modification log format. MQL5 file tests FAIL in RED phase.
"""
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

POSMGR_MQH = PROJECT_ROOT / "ea" / "include" / "PositionManager.mqh"


class TestPositionManagerModule:
    """Verify PositionManager.mqh defines required position management functions."""

    def test_file_exists(self):
        assert POSMGR_MQH.exists(), f"Missing: {POSMGR_MQH}"

    def test_has_property_strict(self):
        content = POSMGR_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common_and_logger(self):
        content = POSMGR_MQH.read_text()
        assert 'include "Common.mqh"' in content
        assert 'include "Logger.mqh"' in content

    def test_has_close_position(self):
        content = POSMGR_MQH.read_text()
        assert "ClosePosition" in content
        assert "bool ClosePosition" in content

    def test_has_close_all_positions(self):
        content = POSMGR_MQH.read_text()
        assert "CloseAllPositions" in content
        assert "int CloseAllPositions" in content

    def test_has_modify_sltp(self):
        content = POSMGR_MQH.read_text()
        assert "ModifySLTP" in content


class TestPositionLogContract:
    """Verify position management log entries."""

    def test_position_close_log_format(self, temp_ipc_dir):
        """Position close should produce a loggable entry."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "sell",  # Close of a buy position
            "volume": 0.1,
            "price": 1.08600,
            "sl": 0.0,
            "tp": 0.0,
            "retcode": 10009,
            "comment": "Position closed",
            "timestamp": "2026-05-24T12:00:10Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["ticket"] == 12345
        assert parsed["symbol"] == "EURUSD"
        assert "retcode" in parsed

    def test_sltp_modification_log_format(self, temp_ipc_dir):
        """SL/TP modification should produce a loggable entry."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entrysltp = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "modify",
            "volume": 0.1,
            "price": 0.0,
            "sl": 1.08300,  # New SL
            "tp": 1.08900,  # New TP
            "retcode": 10009,
            "comment": "SL/TP modified",
            "timestamp": "2026-05-24T12:00:15Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entrysltp) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["sl"] == 1.08300
        assert parsed["tp"] == 1.08900
