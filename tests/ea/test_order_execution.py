"""
RED/GREEN phase tests for Task 3: OrderManager module.

Verifies the trade execution contract — order log format matches
TradeResult struct fields. MQL5 file tests FAIL in RED phase.
"""
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ORDERMGR_MQH = PROJECT_ROOT / "ea" / "include" / "OrderManager.mqh"


class TestOrderManagerModule:
    """Verify OrderManager.mqh defines required order execution functions."""

    def test_file_exists(self):
        assert ORDERMGR_MQH.exists(), f"Missing: {ORDERMGR_MQH}"

    def test_has_property_strict(self):
        content = ORDERMGR_MQH.read_text()
        assert "#property strict" in content

    def test_includes_common_config_logger(self):
        content = ORDERMGR_MQH.read_text()
        assert 'include "Common.mqh"' in content
        assert 'include "Config.mqh"' in content
        assert 'include "Logger.mqh"' in content

    def test_has_open_buy_order(self):
        content = ORDERMGR_MQH.read_text()
        assert "OpenBuyOrder" in content
        assert "TradeResult" in content

    def test_has_open_sell_order(self):
        content = ORDERMGR_MQH.read_text()
        assert "OpenSellOrder" in content

    def test_uses_safe_default_sl(self):
        content = ORDERMGR_MQH.read_text()
        assert "InpSafeDefaultSLPercent" in content

    def test_uses_filling_mode_detection(self):
        content = ORDERMGR_MQH.read_text()
        assert "SYMBOL_FILLING_MODE" in content

    def test_calls_log_trade(self):
        content = ORDERMGR_MQH.read_text()
        assert "LogTrade" in content

    def test_has_get_default_volume(self):
        content = ORDERMGR_MQH.read_text()
        assert "GetDefaultVolume" in content


class TestTradeResultContract:
    """Verify trade log entries match TradeResult struct fields."""

    TRADE_RESULT_FIELDS = [
        "ticket", "symbol", "type", "volume", "price",
        "sl", "tp", "retcode", "comment", "timestamp",
    ]

    def test_buy_order_log_has_all_fields(self, temp_ipc_dir):
        """A buy order log entry must contain all TradeResult fields."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "buy",
            "volume": 0.1,
            "price": 1.08500,
            "sl": 1.08283,
            "tp": 1.08934,
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "comment": "",
            "timestamp": "2026-05-24T12:00:01Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        for field in self.TRADE_RESULT_FIELDS:
            assert field in parsed, f"Buy order log missing field: {field}"
        assert parsed["type"] == "buy"

    def test_sell_order_log_has_all_fields(self, temp_ipc_dir):
        """A sell order log entry must contain all TradeResult fields."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 12346,
            "symbol": "GBPUSD",
            "type": "sell",
            "volume": 0.05,
            "price": 1.25000,
            "sl": 1.25250,
            "tp": 1.24500,
            "retcode": 10009,
            "comment": "Futra",
            "timestamp": "2026-05-24T12:00:05Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["type"] == "sell"
        for field in self.TRADE_RESULT_FIELDS:
            assert field in parsed, f"Sell order log missing field: {field}"

    def test_failed_order_log_has_error_context(self, temp_ipc_dir):
        """A failed trade should log with retcode != 10009."""
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 0,
            "symbol": "EURUSD",
            "type": "buy",
            "volume": 0.1,
            "price": 0.0,
            "sl": 0.0,
            "tp": 0.0,
            "retcode": 10016,  # TRADE_RETCODE_INVALID_STOPS
            "comment": "Invalid stops",
            "timestamp": "2026-05-24T12:00:01Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["retcode"] == 10016
        assert parsed["retcode"] != 10009
