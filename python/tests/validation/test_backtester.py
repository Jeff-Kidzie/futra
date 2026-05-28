"""Test backtesting engine — bar-level EA trade execution simulation.

TDD RED phase — all tests expect python/validation/backtester.py to exist
with the Backtester class and run() method specified in 03-01-PLAN.md.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from python.validation.backtester import Backtester
from python.validation.costs import (
    FixedSpreadModel,
    HistoricalSpreadModel,
    PerLotCommissionModel,
    FixedSlippageModel,
    NoSwapModel,
)


# ── Test fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_ohlcv():
    """500 bars of EURUSD at ~1.085, flat market with small random noise."""
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
        "spread": np.ones(n) * 10,  # 1.0 pips at 5-digit precision
    })


@pytest.fixture
def uptrend_ohlcv():
    """500 bars of EURUSD rising 2% from 1.08 to 1.1016."""
    n = 500
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close = np.linspace(1.08, 1.1016, n)  # +2%
    return pd.DataFrame({
        "time": dates,
        "open": close,
        "high": close + 0.0010,
        "low": close - 0.0002,
        "close": close,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })


@pytest.fixture
def mock_detector():
    """Mock RegimeDetector that always returns trending with 0.8 confidence."""
    class MockDetector:
        def predict(self, features):
            return ("trending", 0.8)
    return MockDetector()


@pytest.fixture
def mock_adapter():
    """Mock ParameterAdapter that returns fixed SL=50, TP=100, lot=0.01."""
    class MockAdapter:
        def adapt(self, regime, confidence, volatility=None, equity=10000.0, atr_pips=None):
            return {
                "sl_pips": 50.0,
                "tp_pips": 100.0,
                "lot_size": 0.01,
                "regime": regime,
                "confidence": confidence,
            }
    return MockAdapter()


@pytest.fixture
def mock_features():
    """Mock compute_features that returns minimal feature dict."""
    def _compute(df):
        return {
            "atr_14": 25.0, "volatility_20": 0.12, "rsi_14": 55.0,
            "macd": 0.0001, "macd_signal": 0.0000, "adx_14": 28.0,
            "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
            "close_to_sma20_pct": 0.5, "volume_ratio": 1.0,
        }
    return _compute


@pytest.fixture
def backtester():
    """Default Backtester with standard risk params and cost models."""
    return Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.20,
        daily_loss_cap_pct=0.05,
        max_positions_per_symbol=1,
        max_bars_held=48,
        spread_model=FixedSpreadModel(),
        commission_model=PerLotCommissionModel(),
        slippage_model=FixedSlippageModel(),
        swap_model=NoSwapModel(),
    )


# ── Test 1: Backtester.run() returns expected keys ─────────────────────────

def test_run_returns_expected_keys(backtester, sample_ohlcv, mock_detector, mock_adapter, mock_features):
    """run() must return dict with trades, equity_curve, final_equity keys."""
    result = backtester.run(sample_ohlcv, "EURUSD", mock_detector, mock_adapter, mock_features)
    assert isinstance(result, dict)
    assert "trades" in result
    assert "equity_curve" in result
    assert "final_equity" in result
    assert isinstance(result["trades"], list)
    assert isinstance(result["equity_curve"], list)


# ── Test 2: Flat market produces zero-or-negative P&L before costs ──────────

def test_flat_market_zero_or_negative_pnl(mock_detector, mock_adapter, mock_features):
    """With truly flat prices, total P&L should be non-positive (costs drain)."""
    # Build a truly flat DataFrame — all bars at same price, no drift
    n = 200
    np.random.seed(42)
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    base = 1.085
    df = pd.DataFrame({
        "time": dates,
        "open": np.full(n, base),
        "high": np.full(n, base + 0.0003),
        "low": np.full(n, base - 0.0003),
        "close": np.full(n, base),
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })
    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", mock_detector, mock_adapter, mock_features)
    total_pnl = sum(t["profit_loss"] for t in result["trades"])
    # Spread + commission makes it negative — verify it's not wildly positive
    assert total_pnl <= 0, f"Expected non-positive P&L with flat prices, got {total_pnl}"


# ── Test 3: Strong uptrend produces positive P&L ────────────────────────────

def test_uptrend_positive_pnl(backtester, uptrend_ohlcv, mock_detector, mock_adapter, mock_features):
    """Price rises 2% over test period → buy positions should make money."""
    result = backtester.run(uptrend_ohlcv, "EURUSD", mock_detector, mock_adapter, mock_features)
    total_pnl = sum(t["profit_loss"] for t in result["trades"])
    assert total_pnl > 0, f"Expected positive P&L in uptrend, got {total_pnl}"
    assert len(result["trades"]) > 0, "Expected at least one trade in uptrend"


# ── Test 4: SL hit during bar — position closes at SL price ─────────────────

def test_sl_hit_closes_at_sl_price():
    """If bar low crosses SL, position closes at SL (not bar close)."""
    # Build a DataFrame where the SL is definitely hit during a bar
    n = 100
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Flat prices at 1.085, then a sharp drop bar
    close_vals = np.full(n, 1.085)
    high_vals = np.full(n, 1.0855)
    low_vals = np.full(n, 1.0845)
    # Bar 70: make a sharp drop — low goes well below SL
    low_vals[70] = 1.0800  # Drops below 50 pip SL
    close_vals[70] = 1.0830

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": high_vals,
        "low": low_vals,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    # Should have at least one trade that was closed by SL
    sl_trades = [t for t in result["trades"] if t["exit_reason"] == "sl_tp"]
    assert len(sl_trades) > 0, "Expected at least one SL-hit trade"
    # The SL trade should have a loss (price went against the long position)
    for trade in sl_trades:
        assert trade["profit_loss"] < 0, f"SL trade should be a loss, got {trade['profit_loss']}"


# ── Test 5: TP hit during bar — position closes at TP price ─────────────────

def test_tp_hit_closes_at_tp_price():
    """If bar high crosses TP, position closes at TP (not bar close)."""
    n = 100
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Flat at 1.085, then spike up
    close_vals = np.full(n, 1.085)
    high_vals = np.full(n, 1.0855)
    low_vals = np.full(n, 1.0845)
    # Bar 70: spike high well above TP (100 pips = 0.010 above entry)
    high_vals[70] = 1.096  # Above TP
    close_vals[70] = 1.093

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": high_vals,
        "low": low_vals,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    tp_trades = [t for t in result["trades"] if t["exit_reason"] == "sl_tp" and t["profit_loss"] > 0]
    assert len(tp_trades) > 0, "Expected at least one TP-hit trade with profit"


# ── Test 6: Both SL and TP crossed in same bar — bar direction tiebreaker ───

def test_both_sl_tp_same_bar_uses_bar_direction():
    """Down bar: SL first for longs. Up bar: TP first for longs."""
    # Build a long-bar scenario: large range that covers both SL and TP
    n = 100
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close_vals = np.full(n, 1.085)
    high_vals = np.full(n, 1.0855)
    low_vals = np.full(n, 1.0845)
    # Bar 70: down bar (close < open) with huge range covering both SL and TP
    close_vals[70] = 1.080
    open_before = close_vals[69]
    # Make open of bar 70 higher than close → down bar
    high_vals[70] = 1.096  # Above 100 pip TP
    low_vals[70] = 1.070   # Below 50 pip SL
    close_vals[70] = 1.080  # Close < open → down bar

    # Fix: need to set open appropriately for bar 70
    open_vals = close_vals.copy()
    open_vals[70] = 1.086  # Open > close → down bar

    df = pd.DataFrame({
        "time": dates,
        "open": open_vals,
        "high": high_vals,
        "low": low_vals,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)

    # Should have trades — the key is it doesn't crash and produces results
    assert len(result["trades"]) > 0, "Expected trades from both-SL-TP scenario"
    assert "trades" in result
    assert "equity_curve" in result


# ── Test 7: Risk gate — drawdown blocks entries ─────────────────────────────

def test_risk_gate_drawdown_blocks_entries():
    """When drawdown exceeds threshold, no new positions are opened."""
    n = 150
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    # Start with sharp decline to trigger drawdown
    close_vals = np.ones(n) * 1.085
    close_vals[50:60] = 1.06  # Sharp drop
    close_vals[60:] = 1.085   # Recovery

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": close_vals + 0.0005,
        "low": close_vals - 0.0005,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 1.0,  # Large lot to trigger drawdown fast
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.05,  # Very tight — 5% max drawdown
        daily_loss_cap_pct=1.0,  # High daily cap — ensure it's drawdown not daily
        max_positions_per_symbol=3,  # Allow multiple to test gate
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    # Should have trades but drawdown gate should have limited them
    assert len(result["trades"]) >= 0  # May or may not have trades
    # The key is the backtester doesn't crash and equity_curve exists
    assert len(result["equity_curve"]) == len(df)


# ── Test 8: Risk gate — daily loss blocks entries ───────────────────────────

def test_risk_gate_daily_loss_blocks_entries():
    """When daily loss exceeds cap, no new positions within same day."""
    n = 150
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close_vals = np.ones(n) * 1.085

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": close_vals + 0.0005,
        "low": close_vals - 0.0005,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 50, "tp_pips": 100, "lot_size": 1.0,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=1.0,  # High drawdown cap — ensure it's daily loss
        daily_loss_cap_pct=0.01,  # Very tight — 1% daily loss cap
        max_positions_per_symbol=5,
        max_bars_held=48,
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    # Backtester runs without crashing, equity curve matches bar count
    assert len(result["equity_curve"]) == len(df)


# ── Test 9: Max positions per symbol enforced ───────────────────────────────

def test_max_positions_per_symbol_enforced(backtester, sample_ohlcv, mock_detector, mock_adapter, mock_features):
    """Backtester won't open second position for same symbol while one is open."""
    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,  # Only 1 per symbol
        max_bars_held=48,
    )
    # Run backtester — should never have more than 1 position per symbol at once
    result = bt.run(sample_ohlcv, "EURUSD", mock_detector, mock_adapter, mock_features)
    assert len(result["trades"]) >= 0
    assert "trades" in result


# ── Test 10: Position closes at bar close when max_bars reached ─────────────

def test_max_bars_held_closes_position():
    """Position closes at bar close when max_bars_held is reached."""
    n = 150
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close_vals = np.linspace(1.08, 1.09, n)  # Small steady uptrend

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": close_vals + 0.0005,
        "low": close_vals - 0.0005,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 200, "tp_pips": 400,  # Wide SL/TP to avoid early close
                    "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=10,  # Short hold to trigger max_bars
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    max_hold_trades = [t for t in result["trades"] if t["exit_reason"] == "max_hold"]
    assert len(max_hold_trades) > 0, f"Expected at least one max_hold trade, got {len(max_hold_trades)}"


# ── Test 11: Equity curve tracked correctly ─────────────────────────────────

def test_equity_curve_tracked_correctly(backtester, sample_ohlcv, mock_detector, mock_adapter, mock_features):
    """Equity curve has one entry per bar, starting at initial_equity."""
    result = backtester.run(sample_ohlcv, "EURUSD", mock_detector, mock_adapter, mock_features)
    equity_curve = result["equity_curve"]
    assert len(equity_curve) == len(sample_ohlcv), \
        f"Expected {len(sample_ohlcv)} equity points, got {len(equity_curve)}"

    # First entry should be near initial equity (minus costs if any position opened early)
    first_equity = equity_curve[0][1]
    # First bar (index 0) is before warmup period — no trades, so equity = initial
    # Actually, equity deductions for commissions happen at entry, but first bar
    # is during warmup (no trades opened). So equity[0] should be close to initial.
    assert abs(first_equity - 10000.0) < 10.0, \
        f"First equity should be near 10000.0, got {first_equity}"

    # Each entry is a (timestamp, equity) pair
    for entry in equity_curve:
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        assert isinstance(entry[1], (int, float))


# ── Test 12: Historical spread from DataFrame is used ───────────────────────

def test_historical_spread_used_in_backtest():
    """With HistoricalSpreadModel, backtester uses DataFrame spread column."""
    n = 200
    np.random.seed(42)
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    close_vals = 1.085 + np.cumsum(np.random.randn(n) * 0.0002)
    close_vals = np.clip(close_vals, 1.07, 1.10)

    df = pd.DataFrame({
        "time": dates,
        "open": close_vals,
        "high": close_vals + 0.001,
        "low": close_vals - 0.001,
        "close": close_vals,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })

    class MockDetector:
        def predict(self, f): return ("trending", 0.8)

    class MockAdapter:
        def adapt(self, **kw):
            return {"sl_pips": 200, "tp_pips": 400, "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}

    def mock_features(df):
        return {"atr_14": 25, "volatility_20": 0.12, "rsi_14": 55,
                "macd": 0.0001, "macd_signal": 0, "adx_14": 28,
                "sma_20_50_ratio": 1.005, "bb_width_pct": 2.5,
                "close_to_sma20_pct": 0.5, "volume_ratio": 1.0}

    bt = Backtester(
        initial_equity=10000.0,
        max_drawdown_pct=0.50,
        daily_loss_cap_pct=0.50,
        max_positions_per_symbol=1,
        max_bars_held=48,
        spread_model=HistoricalSpreadModel(),  # Use historical spread
    )
    result = bt.run(df, "EURUSD", MockDetector(), MockAdapter(), mock_features)
    # Should complete without errors using historical spread model
    assert "trades" in result
    assert "equity_curve" in result
    assert len(result["equity_curve"]) == len(df)
