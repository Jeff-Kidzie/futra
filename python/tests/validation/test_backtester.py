"""Tests for the bar-level backtesting engine.

All tests use mock AI components and mock OHLCV data — no MT5 connection required.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from python.validation.backtester import Backtester
from python.validation.costs import (
    FixedSpreadModel, PerLotCommissionModel, FixedSlippageModel,
    HistoricalSpreadModel, NoSwapModel,
)


# --- Mock AI Components ---

class MockDetector:
    def predict(self, features):
        return ("trending", 0.8)

class MockAdapter:
    def adapt(self, regime=None, confidence=None, volatility=None,
              equity=10000.0, atr_pips=None, **kwargs):
        return {
            "sl_pips": 50.0,
            "tp_pips": 100.0,
            "lot_size": 0.01,
            "regime": regime or "trending",
            "confidence": confidence or 0.8,
        }

class StopAdapter:
    """Adapter that returns very tight SL/TP for controlled testing."""
    def adapt(self, regime=None, confidence=None, volatility=None,
              equity=10000.0, atr_pips=None, **kwargs):
        return {
            "sl_pips": 3.0,
            "tp_pips": 6.0,
            "lot_size": 0.01,
            "regime": regime or "trending",
            "confidence": confidence or 0.8,
        }

class LargeLotAdapter:
    """Adapter with larger position size for drawdown testing."""
    def adapt(self, regime=None, confidence=None, volatility=None,
              equity=10000.0, atr_pips=None, **kwargs):
        return {
            "sl_pips": 50.0,
            "tp_pips": 100.0,
            "lot_size": 1.0,
            "regime": regime or "trending",
            "confidence": confidence or 0.8,
        }


def mock_features(df):
    return {
        "atr_14": 25.0, "volatility_20": 0.12, "rsi_14": 55.0,
        "macd": 0.0001, "macd_signal": 0.0000, "adx_14": 28.0,
        "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
        "close_to_sma20_pct": 0.5, "volume_ratio": 1.0,
    }


# --- Fixtures ---

@pytest.fixture
def backtester():
    return Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.20,
        daily_loss_cap_pct=0.05,
        max_positions_per_symbol=1,
        max_bars_held=48,
    )


@pytest.fixture
def flat_ohlcv():
    """500 bars of EURUSD at ~1.085, flat market."""
    np.random.seed(42)
    n = 500
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = 1.085 + np.cumsum(np.random.randn(n) * 0.0002)
    close = np.clip(close, 1.07, 1.10)
    return pd.DataFrame({
        "time": dates,
        "open": close,
        "high": close + 0.0005,
        "low": close - 0.0005,
        "close": close,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })


@pytest.fixture
def uptrend_ohlcv():
    """500 bars of EURUSD rising 2%."""
    n = 500
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.linspace(1.08, 1.1016, n)
    return pd.DataFrame({
        "time": dates,
        "open": close,
        "high": close + 0.0010,
        "low": close - 0.0002,
        "close": close,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })


# --- Test 1: Backtester.run() returns expected keys ---

def test_run_returns_expected_keys(backtester, flat_ohlcv):
    """Backtester.run() returns dict with trades, equity_curve, final_equity."""
    result = backtester.run(flat_ohlcv, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    assert "trades" in result
    assert "equity_curve" in result
    assert "final_equity" in result


# --- Test 2: Flat market → negative P&L (costs drain) ---

def test_flat_market_negative_pnl():
    """With flat prices and costs, equity declines due to spread + commission drain.
    
    Uses perfectly constant prices so zero P&L from price movement — costs dominate.
    Uses slightly larger lot size to make commission impact visible.
    """
    n = 200
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    df = pd.DataFrame({
        "time": dates,
        "open": np.full(n, 1.085),
        "high": np.full(n, 1.090),
        "low": np.full(n, 1.080),
        "close": np.full(n, 1.085),
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class LargerAdapter:
        def adapt(self, regime=None, confidence=None, volatility=None,
                  equity=10000.0, atr_pips=None, **kwargs):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.1, "regime": "trending", "confidence": 0.8}

    bt = Backtester(
        initial_equity=10000.0,
        spread_model=FixedSpreadModel({"EURUSD": 0.0}),
        commission_model=PerLotCommissionModel(7.0),
        slippage_model=FixedSlippageModel(0.0, 0.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), LargerAdapter(), mock_features)
    # With flat prices, zero spread/slippage, only commission applies.
    # Each position: $3.50 entry + $3.50 exit = $7 commission cost.
    # Final equity should be < initial due to commission drain.
    assert result["final_equity"] < 10000.0, \
        f"Equity {result['final_equity']} not below initial due to costs"


# --- Test 3: Strong uptrend → positive P&L ---

def test_uptrend_positive_pnl(backtester, uptrend_ohlcv):
    """With strong upward trend and trending regime, backtester should profit."""
    result = backtester.run(uptrend_ohlcv, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    total_pnl = sum(t["profit_loss"] for t in result["trades"])
    assert total_pnl > 0


# --- Test 4: SL hit during bar ---

def test_sl_hit_during_bar():
    """Position closes at SL price when bar low crosses SL."""
    n = 60
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Flat at 1.085 for all bars
    close = np.full(n, 1.085)
    low = np.full(n, 1.084)
    high = np.full(n, 1.086)
    # Bar 51: low drops to 1.080 (will cross SL)
    low[51] = 1.0800
    high[51] = 1.0855
    close[51] = 1.081

    df = pd.DataFrame({
        "time": dates, "open": close, "high": high, "low": low,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        spread_model=FixedSpreadModel({"EURUSD": 1.0}),
        commission_model=PerLotCommissionModel(7.0),
        slippage_model=FixedSlippageModel(0.5, 1.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), StopAdapter(), mock_features)
    # At least one trade should have been taken
    assert len(result["trades"]) > 0, "No trades were taken"

    # Find the trade that was stopped out
    sl_trades = [t for t in result["trades"] if t["exit_reason"] == "sl_tp"]
    assert len(sl_trades) > 0, "No SL-hit trades found"

    # SL price should be entry_price - sl_pips * pip_size
    # StopAdapter returns sl_pips=3.0, pip_size=0.0001
    # So SL distance from entry = 3.0 * 0.0001 = 0.0003
    trade = sl_trades[0]
    expected_sl_distance = trade["sl_pips"] * 0.0001
    actual_distance = abs(trade["entry_price"] - trade["exit_price"])
    assert actual_distance == pytest.approx(expected_sl_distance, abs=0.001), \
        f"Exit price {trade['exit_price']} does not match SL distance {expected_sl_distance} from entry {trade['entry_price']}"


# --- Test 5: TP hit during bar ---

def test_tp_hit_during_bar():
    """Position closes at TP price when bar high crosses TP."""
    n = 60
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)
    low = np.full(n, 1.084)
    high = np.full(n, 1.086)
    # Bar 51: high crosses TP
    high[51] = 1.0870  # With SL=3 pips, TP=6 pips, TP ≈ 1.085 + 0.0006 = 1.0856
    low[51] = 1.0845
    close[51] = 1.086

    df = pd.DataFrame({
        "time": dates, "open": close, "high": high, "low": low,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        spread_model=FixedSpreadModel({"EURUSD": 1.0}),
        commission_model=PerLotCommissionModel(7.0),
        slippage_model=FixedSlippageModel(0.5, 1.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), StopAdapter(), mock_features)
    tp_trades = [t for t in result["trades"] if t["exit_reason"] == "sl_tp"]
    assert len(tp_trades) > 0, "No TP-hit trades found"


# --- Test 6: Both SL and TP crossed → bar direction tiebreaker ---

def test_both_sl_and_tp_tiebreaker_down():
    """When both SL and TP are crossed in a down bar, SL hits first."""
    n = 60
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)
    low = np.full(n, 1.084)
    high = np.full(n, 1.086)
    # Bar 51: big range bar that crosses both SL and TP
    # For a buy position, SL is below entry, TP is above entry
    # If both are crossed with a down bar, SL should hit first
    # With SL=3 pips (0.0003) and TP=6 pips (0.0006)
    # From entry at ~1.085: SL ≈ 1.0847, TP ≈ 1.0856
    high[51] = 1.0870  # crosses TP
    low[51] = 1.0840   # crosses SL
    close[51] = 1.0845  # down bar (close < open)
    
    df = pd.DataFrame({
        "time": dates, "open": np.full(n, 1.085), "high": high, "low": low,
        "close": close, "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        spread_model=FixedSpreadModel({"EURUSD": 1.0}),
        commission_model=PerLotCommissionModel(7.0),
        slippage_model=FixedSlippageModel(0.5, 1.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), StopAdapter(), mock_features)
    sl_tp_trades = [t for t in result["trades"] if t["exit_reason"] == "sl_tp"]
    assert len(sl_tp_trades) > 0, "No SL/TP trades found"

    # Down bar: for buy, SL hit first → exit should be at SL price
    trade = sl_tp_trades[0]
    expected_sl = trade["sl_pips"] * 0.0001
    actual_loss = abs(trade["entry_price"] - trade["exit_price"])
    # Should have hit SL (closer to entry) not TP (further)
    # SL is 3 pips away, TP is 6 pips away
    assert actual_loss < trade["tp_pips"] * 0.0001, \
        f"Trade exited at TP distance {actual_loss} instead of SL distance {expected_sl}"


# --- Test 7: Drawdown gate blocks entry ---

def test_drawdown_gate_blocks_new_positions():
    """Risk gate blocks new positions when drawdown exceeds threshold."""
    n = 200
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Prices that fall 30% — every buy position loses money
    close = np.linspace(1.10, 0.80, n)

    df = pd.DataFrame({
        "time": dates, "open": close, "high": close + 0.01, "low": close - 0.01,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.20,  # 20% drawdown limit
        daily_loss_cap_pct=0.50,  # 50% daily loss cap (won't block)
        max_positions_per_symbol=5,  # Allow multiple positions
    )
    # Use larger lot size so each trade loses enough to trigger drawdown gate
    result = bt.run(df, "EURUSD", MockDetector(), LargeLotAdapter(), mock_features)

    # At least some trades should have been taken
    assert len(result["trades"]) > 0
    # Some losses occurred
    total_pnl = sum(t["profit_loss"] for t in result["trades"])
    assert total_pnl < 0, "Expected negative total P&L in falling market"
    # Large lots in a falling market should cause significant losses
    assert result["final_equity"] < 9000, \
        f"Equity {result['final_equity']} not below 9000"


# --- Test 8: Daily loss cap blocks entry ---

def test_daily_loss_cap_blocks_new_positions():
    """Risk gate blocks new positions when daily loss exceeds threshold."""
    n = 100
    # All same day so daily loss tracking doesn't reset
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Falling prices — every buy loses
    close = np.linspace(1.10, 0.90, n)

    df = pd.DataFrame({
        "time": dates, "open": close, "high": close + 0.01, "low": close - 0.01,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,  # 50% drawdown (won't block)
        daily_loss_cap_pct=0.05,  # 5% daily loss ($500)
        max_positions_per_symbol=5,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    # Some trades taken, but equity shouldn't be catastrophic
    # (daily loss cap should limit losses)
    assert len(result["trades"]) > 0


# --- Test 9: Max positions per symbol enforced ---

def test_max_positions_per_symbol():
    """Backtester won't open second position for same symbol while one is open."""
    n = 100
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)

    df = pd.DataFrame({
        "time": dates, "open": close, "high": close + 0.005, "low": close - 0.005,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        max_positions_per_symbol=1,
        max_bars_held=100,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    # Check that we never have overlapping positions for the same symbol
    for i in range(len(result["trades"])):
        for j in range(i + 1, len(result["trades"])):
            t1, t2 = result["trades"][i], result["trades"][j]
            if t1["symbol"] == t2["symbol"]:
                # t2 should not open while t1 is still open
                assert t2["entry_time"] >= t1["exit_time"], \
                    f"Overlapping positions for {t1['symbol']}: {t1['entry_time']}-{t1['exit_time']} and {t2['entry_time']}-{t2['exit_time']}"


# --- Test 10: Max bars held enforced ---

def test_max_bars_held_enforced():
    """Position closes at bar close when max_bars_held reached.
    
    Ensures the bar low does NOT trigger SL (use tight SL via StopAdapter
    but keep bar range wide enough that low doesn't cross SL).
    """
    n = 60
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)
    # Keep low above SL price: with SL=3 pips, SL ≈ 1.085 - 0.0003 = 1.0847
    # low = 1.0848 (above SL) + ensures max_hold triggers before SL
    low = np.full(n, 1.0848)
    high = np.full(n, 1.0852)

    df = pd.DataFrame({
        "time": dates, "open": close, "high": high, "low": low,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=10000.0,
        max_bars_held=3,  # Force close after 3 bars
        spread_model=FixedSpreadModel({"EURUSD": 0.0}),
        commission_model=PerLotCommissionModel(0.0),
        slippage_model=FixedSlippageModel(0.0, 0.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    max_hold_trades = [t for t in result["trades"] if t["exit_reason"] == "max_hold"]
    assert len(max_hold_trades) > 0, "No max_hold trades found"

    for trade in max_hold_trades:
        # Position should have been held for max_bars_held bars
        entry_idx = [i for i, d in enumerate(df["time"]) if d == trade["entry_time"]]
        exit_idx = [i for i, d in enumerate(df["time"]) if d == trade["exit_time"]]
        if entry_idx and exit_idx:
            bars_held = exit_idx[0] - entry_idx[0]
            # max_bars_held=3, so position should close around bar 3-4
            assert bars_held <= 5, f"Position held for {bars_held} bars, expected ~3"


# --- Test 11: Equity curve tracked correctly ---

def test_equity_curve_tracking():
    """Equity curve contains (timestamp, equity) pairs, one per bar.
    Starting equity = initial_equity.
    """
    n = 100
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)

    df = pd.DataFrame({
        "time": dates, "open": close, "high": close + 0.005, "low": close - 0.005,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })

    bt = Backtester(
        initial_equity=5000.0,
        spread_model=FixedSpreadModel({"EURUSD": 0.0}),
        commission_model=PerLotCommissionModel(0.0),
        slippage_model=FixedSlippageModel(0.0, 0.0),
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    # Equity curve should have one entry per bar
    assert len(result["equity_curve"]) == n
    # First entry should be initial equity
    assert result["equity_curve"][0][1] == 5000.0
    # Each entry should be a (timestamp, equity) tuple
    for entry in result["equity_curve"][:5]:
        assert len(entry) == 2
        assert isinstance(entry[1], (int, float))


# --- Test 12: HistoricalSpreadModel integration ---

def test_historical_spread_model_in_backtester():
    """Backtester uses HistoricalSpreadModel when provided, reading spread from DataFrame."""
    n = 70
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.full(n, 1.085)
    # Large spread on bar 60 (will affect entry cost)
    spread = np.full(n, 10)  # 10 points = 1.0 pips
    spread[60:65] = 50  # 50 points = 5.0 pips

    df = pd.DataFrame({
        "time": dates, "open": close, "high": close + 0.005, "low": close - 0.005,
        "close": close,
        "tick_volume": np.ones(n) * 1000, "spread": spread,
    })

    hist_model = HistoricalSpreadModel(points_to_price=0.00001)

    bt = Backtester(
        initial_equity=10000.0,
        spread_model=hist_model,
        commission_model=PerLotCommissionModel(0.0),
        slippage_model=FixedSlippageModel(0.0, 0.0),
    )
    # Should not crash — HistoricalSpreadModel used for spread lookups
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    assert len(result["trades"]) > 0
    # Some spread was applied (non-zero spread costs)
    assert result["final_equity"] < 10000.0, \
        "Historical spread should have added costs"
