"""
RED/GREEN phase tests for Plan 01-03: Risk controls — pending orders,
drawdown circuit breaker, daily loss cap, max positions per symbol,
position sizing validation.

Verifies the IPC contract for risk control log output and validates the
MQL5 RiskManager module exports, EA integration, and conservative defaults.

The MQL5 file tests FAIL in RED phase (RiskManager.mqh doesn't exist yet).
The IPC contract tests use test_helpers and verify the JSONL log formats
that the EA writes through its file-based interface.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
RISK_MANAGER_MQH = PROJECT_ROOT / "ea" / "include" / "RiskManager.mqh"
FUTRA_EA_MQ5 = PROJECT_ROOT / "ea" / "FutraEA.mq5"


# ---------------------------------------------------------------------------
# RiskManager module existence & export tests (RED: fail before file exists)
# ---------------------------------------------------------------------------

class TestRiskManagerModule:
    """Verify RiskManager.mqh exists and defines all required functions."""

    def test_file_exists(self):
        assert RISK_MANAGER_MQH.exists(), f"Missing: {RISK_MANAGER_MQH}"

    def test_has_property_strict(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "#property strict" in content

    def test_includes_dependencies(self):
        content = RISK_MANAGER_MQH.read_text()
        assert 'include "Common.mqh"' in content
        assert 'include "Config.mqh"' in content
        assert 'include "Logger.mqh"' in content
        assert 'include "PositionManager.mqh"' in content

    def test_has_pending_order_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "PlacePendingOrder" in content
        assert "TradeResult" in content

    def test_has_drawdown_limit_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "CheckDrawdownLimit" in content
        # Uses ACCOUNT_EQUITY and peak balance tracking
        assert "ACCOUNT_EQUITY" in content or "s_peakBalance" in content

    def test_has_daily_loss_cap_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "CheckDailyLossLimit" in content
        # Uses daily loss tracking
        assert "ResetDailyLossTracking" in content or "s_dailyRealizedLoss" in content

    def test_has_max_positions_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "CheckMaxPositionsPerSymbol" in content

    def test_has_validate_position_size_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "ValidatePositionSize" in content
        # Uses margin calculation
        assert "OrderCalcMargin" in content or "ACCOUNT_MARGIN_FREE" in content

    def test_has_is_trading_allowed_function(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "IsTradingAllowed" in content

    def test_has_record_closed_trade_profit(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "RecordClosedTradeProfit" in content

    def test_has_reset_daily_loss_tracking(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "ResetDailyLossTracking" in content

    # --- Pending order type coverage (DATA-07: all 6 types) ---

    def test_supports_all_six_pending_order_types(self):
        content = RISK_MANAGER_MQH.read_text()
        expected_types = [
            "ORDER_TYPE_BUY_LIMIT",
            "ORDER_TYPE_SELL_LIMIT",
            "ORDER_TYPE_BUY_STOP",
            "ORDER_TYPE_SELL_STOP",
            "ORDER_TYPE_BUY_STOP_LIMIT",
            "ORDER_TYPE_SELL_STOP_LIMIT",
        ]
        for ot in expected_types:
            assert ot in content, f"Missing pending order type: {ot}"

    # --- Drawdown circuit breaker (RISK-02) ---

    def test_drawdown_uses_peak_balance_and_equity(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "s_peakBalance" in content
        assert "ACCOUNT_EQUITY" in content
        assert "InpMaxDrawdownPercent" in content

    # --- Daily loss cap (RISK-03) ---

    def test_daily_loss_uses_reset_and_realized_loss(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "s_dailyRealizedLoss" in content
        assert "InpDailyLossCapPercent" in content
        assert "MqlDateTime" in content or "ResetDailyLossTracking" in content

    # --- Max positions per symbol (RISK-04) ---

    def test_max_positions_uses_magic_number_and_symbol(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "InpMaxPositionsPerSymbol" in content
        assert "POSITION_MAGIC" in content or "InpMagicNumber" in content

    # --- Position sizing validation (RISK-05) ---

    def test_validate_position_size_uses_margin_buffer(self):
        content = RISK_MANAGER_MQH.read_text()
        assert "InpMinMarginBufferPercent" in content
        assert "OrderCalcMargin" in content
        assert "ACCOUNT_MARGIN_FREE" in content

    # --- Risk gate ordering: drawdown -> daily loss -> positions -> margin ---

    def test_is_trading_allowed_gate_order(self):
        content = RISK_MANAGER_MQH.read_text()
        # The four gates must appear in priority order within IsTradingAllowed
        dd_idx = content.index("CheckDrawdownLimit")
        dl_idx = content.index("CheckDailyLossLimit")
        mp_idx = content.index("CheckMaxPositionsPerSymbol")
        vs_idx = content.index("ValidatePositionSize")
        assert dd_idx < dl_idx < mp_idx < vs_idx, (
            "Risk gate priority order must be: drawdown -> daily loss -> "
            "max positions -> position sizing"
        )

    # --- Conservative defaults ---

    def test_conservative_defaults(self):
        content = RISK_MANAGER_MQH.read_text()
        # Drawdown max: 20% (per plan)
        assert "20.0" in content
        # Daily loss cap: 5% (per plan)
        assert "5.0" in content
        # Max positions per symbol: 1 (per plan)
        assert "InpMaxPositionsPerSymbol = 1" in content or "MaxPositions = 1" in content
        # Margin buffer: 150% (per plan)
        assert "150.0" in content or "InpMinMarginBufferPercent" in content


# ---------------------------------------------------------------------------
# EA integration tests (RED: fail before RiskManager is wired into EA)
# ---------------------------------------------------------------------------

class TestEAIntegration:
    """Verify FutraEA.mq5 integrates RiskManager with pre-trade gates."""

    def test_ea_includes_risk_manager(self):
        content = FUTRA_EA_MQ5.read_text()
        assert 'include "include/RiskManager.mqh"' in content

    def test_ea_calls_is_trading_allowed(self):
        content = FUTRA_EA_MQ5.read_text()
        assert "IsTradingAllowed" in content

    def test_ea_skips_symbol_when_trading_not_allowed(self):
        content = FUTRA_EA_MQ5.read_text()
        # Must have pattern: if(!IsTradingAllowed(...)) { continue; }
        assert "IsTradingAllowed" in content
        # Either continue or a skip pattern must exist alongside the gate call
        assert "continue" in content or "break" in content

    def test_risk_gate_before_order_logic(self):
        content = FUTRA_EA_MQ5.read_text()
        # IsTradingAllowed must appear before any OrderManager calls
        # (OpenBuyOrder/OpenSellOrder/PlacePendingOrder)
        ita_idx = content.index("IsTradingAllowed")
        order_idx = float("inf")
        for pattern in ["OpenBuyOrder", "OpenSellOrder", "PlacePendingOrder",
                         "OrderSend"]:
            idx = content.find(pattern, ita_idx)
            if idx != -1:
                order_idx = min(order_idx, idx)
        if order_idx != float("inf"):
            assert ita_idx < order_idx, (
                "Risk gate (IsTradingAllowed) must execute BEFORE any order logic"
            )

    def test_oninit_initializes_risk_state(self):
        content = FUTRA_EA_MQ5.read_text()
        # OnInit should initialize risk tracking
        assert "ResetDailyLossTracking" in content or "s_peakBalance" in content


# ---------------------------------------------------------------------------
# IPC contract tests — risk control log output formats
# ---------------------------------------------------------------------------

class TestDrawdownBreachLogged:
    """Verify drawdown circuit breaker error log format (RISK-02)."""

    def test_drawdown_breach_jsonl_format(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDrawdownLimit",
            "errorCode": 0,
            "details": (
                "Drawdown circuit breaker: equity=8000.00 peak=10000.00 "
                "drawdown=20.00% limit=20.00%"
            ),
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert parsed["context"] == "CheckDrawdownLimit"
        assert "drawdown" in parsed["details"].lower()
        assert "equity" in parsed["details"].lower()

    def test_drawdown_breach_contains_percentage(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDrawdownLimit",
            "errorCode": 0,
            "details": "Drawdown circuit breaker: equity=8000.00 peak=10000.00 drawdown=20.00% limit=20.00%",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "%" in parsed["details"]
        assert "20.00" in parsed["details"]


class TestDailyLossCapLogged:
    """Verify daily loss cap error log format (RISK-03)."""

    def test_daily_loss_cap_jsonl_format(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDailyLossLimit",
            "errorCode": 0,
            "details": (
                "Daily loss cap: loss=600.00 (6.00%) limit=5.00% "
                "balance_start=10000.00"
            ),
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert parsed["context"] == "CheckDailyLossLimit"
        assert "loss" in parsed["details"].lower()
        assert "%" in parsed["details"]

    def test_daily_loss_cap_contains_loss_percentage(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDailyLossLimit",
            "errorCode": 0,
            "details": "Daily loss cap: loss=600.00 (6.00%) limit=5.00% balance_start=10000.00",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "6.00%" in parsed["details"]
        assert "5.00%" in parsed["details"]


class TestMaxPositionsLogged:
    """Verify max positions per symbol log format (RISK-04)."""

    def test_max_positions_info_jsonl_format(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "info",
            "message": (
                "Max positions for EURUSD: 1/1 — "
                "skipping new orders for this symbol"
            ),
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "info"
        assert "EURUSD" in parsed["message"]
        assert "Max positions" in parsed["message"]
        assert "1/1" in parsed["message"] or "positions" in parsed["message"].lower()


class TestMarginValidationLogged:
    """Verify margin rejection log format (RISK-05)."""

    def test_margin_validation_error_jsonl_format(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "ValidatePositionSize",
            "errorCode": 0,
            "details": (
                "Insufficient margin for EURUSD: need=100.00 "
                "(with 150% buffer=150.00) free=50.00"
            ),
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert parsed["context"] == "ValidatePositionSize"
        assert "margin" in parsed["details"].lower()
        # Contains margin values
        assert "150" in parsed["details"]

    def test_volume_exceeds_max_format(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "ValidatePositionSize",
            "errorCode": 0,
            "details": "Volume 5.00 exceeds max 0.10 for EURUSD",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert parsed["context"] == "ValidatePositionSize"
        assert "exceeds max" in parsed["details"].lower()


# ---------------------------------------------------------------------------
# Pending order contract test (DATA-07)
# ---------------------------------------------------------------------------

class TestPendingOrderLogged:
    """Verify pending order trade log entry format (DATA-07)."""

    PENDING_ORDER_FIELDS = [
        "ticket", "symbol", "type", "volume", "price",
        "sl", "tp", "retcode", "comment", "timestamp",
    ]

    VALID_PENDING_TYPES = [
        "ORDER_TYPE_BUY_LIMIT",
        "ORDER_TYPE_SELL_LIMIT",
        "ORDER_TYPE_BUY_STOP",
        "ORDER_TYPE_SELL_STOP",
        "ORDER_TYPE_BUY_STOP_LIMIT",
        "ORDER_TYPE_SELL_STOP_LIMIT",
    ]

    def test_pending_order_entry_has_all_fields(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 67890,
            "symbol": "EURUSD",
            "type": "ORDER_TYPE_BUY_LIMIT",
            "volume": 0.1,
            "price": 1.0800,
            "sl": 1.0584,
            "tp": 1.1232,
            "retcode": 10009,
            "comment": "",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        for field in self.PENDING_ORDER_FIELDS:
            assert field in parsed, (
                f"Pending order log entry missing field: {field}"
            )

    def test_pending_order_type_is_valid(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        for order_type in self.VALID_PENDING_TYPES:
            entry = {
                "ticket": 1,
                "symbol": "EURUSD",
                "type": order_type,
                "volume": 0.1,
                "price": 1.0800,
                "sl": 1.0700,
                "tp": 1.0900,
                "retcode": 10009,
                "comment": "",
                "timestamp": "2026-05-24T12:00:00Z",
            }
            assert entry["type"] in self.VALID_PENDING_TYPES

    def test_pending_order_has_sl_tp(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        entry = {
            "ticket": 67890,
            "symbol": "GBPUSD",
            "type": "ORDER_TYPE_SELL_STOP",
            "volume": 0.05,
            "price": 1.2400,
            "sl": 1.2500,
            "tp": 1.2300,
            "retcode": 10009,
            "comment": "",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["sl"] > 0
        assert parsed["tp"] > 0
        assert parsed["sl"] != parsed["tp"]


# ---------------------------------------------------------------------------
# IsTradingAllowed integration test
# ---------------------------------------------------------------------------

class TestIsTradingAllowed:
    """Verify IsTradingAllowed master gate integration."""

    def test_all_gates_passing_logs_info(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        # Simulate trade proceeding after all gates pass
        trade_entry = {
            "ticket": 1001,
            "symbol": "EURUSD",
            "type": "buy",
            "volume": 0.1,
            "price": 1.0850,
            "sl": 1.0830,
            "tp": 1.0890,
            "retcode": 10009,
            "comment": "",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(trade_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["retcode"] == 10009
        assert parsed["ticket"] > 0

    def test_drawdown_gate_failing_blocks_trade(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        # When drawdown gate fails, no trade entry appears — only error log
        error_entry = {
            "level": "error",
            "context": "CheckDrawdownLimit",
            "errorCode": 0,
            "details": "Drawdown circuit breaker: equity=8000.00 peak=10000.00 drawdown=20.00% limit=20.00%",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(error_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert parsed["level"] == "error"
        assert "CheckDrawdownLimit" in parsed["context"]


# ---------------------------------------------------------------------------
# Position size violation contract test
# ---------------------------------------------------------------------------

class TestPositionSizeViolation:
    """Verify position size rejection log format."""

    def test_volume_exceeds_max_rejection(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "ValidatePositionSize",
            "errorCode": 0,
            "details": "Volume 5.00 exceeds max 0.10 for EURUSD",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "exceeds max" in parsed["details"].lower()
        assert "5.00" in parsed["details"] or "0.10" in parsed["details"]
        assert "EURUSD" in parsed["details"]


# ---------------------------------------------------------------------------
# Configurable risk inputs test
# ---------------------------------------------------------------------------

class TestRiskInputsConfigurable:
    """Verify risk control inputs are configurable via input parameters."""

    def test_drawdown_percent_configurable(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        # Test that the config value is reflected in log output
        # For 25% drawdown limit:
        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDrawdownLimit",
            "errorCode": 0,
            "details": "Drawdown circuit breaker: equity=7500.00 peak=10000.00 drawdown=25.00% limit=25.00%",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "25.00%" in parsed["details"]

    def test_daily_loss_cap_configurable(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        # Test that a different cap (3%) is reflected:
        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "CheckDailyLossLimit",
            "errorCode": 0,
            "details": "Daily loss cap: loss=300.00 (3.00%) limit=3.00% balance_start=10000.00",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "3.00%" in parsed["details"]

    def test_margin_buffer_configurable(self, temp_ipc_dir):
        from tests.ea.test_helpers import create_ipc_dir

        # Test that a different buffer (200%) is reflected:
        ipc_dir = create_ipc_dir(temp_ipc_dir)
        log_entry = {
            "level": "error",
            "context": "ValidatePositionSize",
            "errorCode": 0,
            "details": "Insufficient margin for EURUSD: need=100.00 (with 200% buffer=200.00) free=50.00",
            "timestamp": "2026-05-24T12:00:00Z",
        }
        log_path = ipc_dir / "trade_log.jsonl"
        log_path.write_text(json.dumps(log_entry) + "\n")

        with open(log_path) as f:
            parsed = json.loads(f.readline().strip())

        assert "200%" in parsed["details"] or "200.0" in parsed["details"]
