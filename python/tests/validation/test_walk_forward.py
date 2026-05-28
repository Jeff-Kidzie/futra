"""Tests for walk-forward validation — anchored expanding-window strategy evaluation.

Per BACK-03: Proves the strategy generalizes beyond training data.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def multi_year_ohlcv():
    """3 years of daily OHLCV data (~1095 bars)."""
    n = 365 * 3
    dates = [datetime(2021, 1, 1) + timedelta(days=i) for i in range(n)]
    close = 1.08 + np.cumsum(np.random.randn(n) * 0.001)
    return pd.DataFrame({
        "time": dates,
        "open": close,
        "high": close + 0.001,
        "low": close - 0.001,
        "close": close,
        "tick_volume": np.ones(n) * 1000,
        "spread": np.ones(n) * 10,
    })


@pytest.fixture
def mock_backtester():
    """Mock backtester that returns realistic results with profitable trades."""
    class MockBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            n_trades = max(1, len(df) // 50)  # ~1 trade per 50 bars
            trades = [{"profit_loss": 10.0, "symbol": symbol} for _ in range(n_trades)]
            # Use timestamps from df if available
            if "time" in df.columns:
                timestamps = df["time"].tolist()
            else:
                timestamps = list(range(len(df)))
            equity = list(zip(timestamps,
                            np.linspace(10000, 10000 + len(df) * 0.5, len(df))))
            return {"trades": trades, "equity_curve": equity, "final_equity": equity[-1][1]}
    return MockBacktester()


@pytest.fixture
def low_trade_backtester():
    """Mock backtester that returns very few trades (below min_oos_trades)."""
    class LowTradeBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            trades = [{"profit_loss": 50.0, "symbol": symbol}]
            if "time" in df.columns:
                timestamps = df["time"].tolist()
            else:
                timestamps = list(range(len(df)))
            equity = list(zip(timestamps,
                            np.linspace(10000, 10050, len(df))))
            return {"trades": trades, "equity_curve": equity, "final_equity": equity[-1][1]}
    return LowTradeBacktester()


# --- Test 1: Window generation produces correct count ---
def test_generate_windows_correct_count(multi_year_ohlcv):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    windows = wf._generate_windows(multi_year_ohlcv)
    # 3 years total: IS 2 years, OOS 6 months. Windows: 2
    assert len(windows) == 2


# --- Test 2: run() returns expected keys ---
def test_walk_forward_run_returns_expected_keys(multi_year_ohlcv, mock_backtester):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    assert "windows" in result
    assert "aggregate" in result
    assert "passed" in result
    assert len(result["windows"]) == 2


# --- Test 3: Window date ranges are correct ---
def test_window_date_ranges_are_correct(multi_year_ohlcv):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    windows = wf._generate_windows(multi_year_ohlcv)
    start = datetime(2021, 1, 1)
    # Window 1 IS end should be ~2 years after start (accounting for leap years)
    window_1_is_end = windows[0]["is_end"]
    delta_days = (window_1_is_end - start).days
    assert 700 < delta_days < 760  # ~2 years with leap year tolerance


# --- Test 4: Per-window result contains all required fields ---
def test_per_window_result_structure(multi_year_ohlcv, mock_backtester):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    window = result["windows"][0]
    assert "window_index" in window
    assert "is_start" in window
    assert "is_end" in window
    assert "oos_start" in window
    assert "oos_end" in window
    assert "is_metrics" in window
    assert "oos_metrics" in window
    assert "is_oos_sharpe_ratio" in window
    assert isinstance(window["is_oos_sharpe_ratio"], (int, float))


# --- Test 5: Aggregate metrics contain all expected fields ---
def test_aggregate_metrics_structure(multi_year_ohlcv, mock_backtester):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    agg = result["aggregate"]
    assert "num_windows" in agg
    assert "mean_oos_sharpe" in agg
    assert "mean_oos_profit_factor" in agg
    assert "worst_window_drawdown" in agg
    assert "mean_is_oos_sharpe_ratio" in agg


# --- Test 6: Pass/fail criteria — very lenient thresholds ensure pass with profitable trades ---
def test_pass_criteria_with_lenient_thresholds(multi_year_ohlcv):
    from python.validation.walk_forward import WalkForward
    class AlwaysWinBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            n_trades = 30
            trades = [{"profit_loss": 100.0, "symbol": symbol} for _ in range(n_trades)]
            if "time" in df.columns:
                timestamps = df["time"].tolist()
            else:
                timestamps = list(range(len(df)))
            equity = list(zip(timestamps,
                            np.linspace(10000, 20000, len(df))))
            return {"trades": trades, "equity_curve": equity, "final_equity": 20000.0}

    wf = WalkForward(in_sample_years=2, out_of_sample_months=6,
                     min_sharpe=-999.0, min_profit_factor=0.0, max_drawdown=999.0)
    result = wf.run(multi_year_ohlcv, "EURUSD", AlwaysWinBacktester(),
                    None, None, lambda df: {})
    assert result["passed"] is True


# --- Test 7: Windows with fewer than min_oos_trades produce warning ---
def test_low_oos_trades_produces_warning(multi_year_ohlcv, low_trade_backtester):
    from python.validation.walk_forward import WalkForward
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6, min_oos_trades=10)
    result = wf.run(multi_year_ohlcv, "EURUSD", low_trade_backtester, None, None, lambda df: {})
    # The low_trade_backtester returns only 1 trade per window, below min_oos_trades=10
    # Each window should have a warning
    for window in result["windows"]:
        assert window["warning"] is not None
        assert "Only" in window["warning"]


# --- Test 8: Empty data handled gracefully ---
def test_empty_data_no_crash():
    from python.validation.walk_forward import WalkForward
    wf = WalkForward()
    empty_df = pd.DataFrame(columns=["time", "open", "high", "low", "close", "tick_volume", "spread"])
    result = wf.run(empty_df, "EURUSD", None, None, None, lambda df: {})
    assert result["windows"] == []
    assert result["passed"] is False
    assert "error" in result
