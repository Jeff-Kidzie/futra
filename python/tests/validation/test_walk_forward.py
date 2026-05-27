import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from python.validation.walk_forward import WalkForward


@pytest.fixture
def multi_year_ohlcv():
    """3 years of daily OHLCV data."""
    n = 365 * 3  # ~1095 daily bars
    dates = [datetime(2021, 1, 1) + timedelta(days=i) for i in range(n)]
    close = 1.08 + np.cumsum(np.random.randn(n) * 0.001)
    return pd.DataFrame({
        "time": dates,
        "open": close, "high": close + 0.001, "low": close - 0.001,
        "close": close, "tick_volume": np.ones(n) * 1000, "spread": np.ones(n) * 10,
    })


@pytest.fixture
def mock_backtester():
    """Mock backtester that returns fixed results."""
    class MockBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            n_trades = max(1, len(df) // 50)  # ~1 trade per 50 bars
            trades = [{"profit_loss": 10.0, "symbol": symbol} for _ in range(n_trades)]
            equity = list(zip(df["time"] if "time" in df.columns else range(len(df)),
                            np.linspace(10000, 10000 + len(df) * 0.5, len(df))))
            return {"trades": trades, "equity_curve": equity, "final_equity": equity[-1][1]}
    return MockBacktester()


# --- Test 1: Window generation count ---

def test_generate_windows_correct_count(multi_year_ohlcv):
    """Test 1: WalkForward._generate_windows() splits a 3-year DataFrame into
    anchored expanding windows. With in_sample_years=2, oos_months=6:
    Window 1: IS=[0:730] days, OOS=[730:913] days.
    Window 2: IS=[0:913] days, OOS=[913:1096] days."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    windows = wf._generate_windows(multi_year_ohlcv)
    # 3 years total: IS 2 years, OOS 6 months.
    # Window 1: IS [year 0-2], OOS [year 2-2.5]
    # Window 2: IS [year 0-2.5], OOS [year 2.5-3.0]
    assert len(windows) == 2


# --- Test 2: WalkForward.run() returns expected dict structure ---

def test_walk_forward_run_returns_expected_keys(multi_year_ohlcv, mock_backtester):
    """Test 2: WalkForward.run() returns dict with keys: windows, aggregate, passed."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    assert "windows" in result
    assert "aggregate" in result
    assert "passed" in result
    assert len(result["windows"]) == 2


# --- Test 3: Window date ranges are correct ---

def test_window_date_ranges_are_correct(multi_year_ohlcv):
    """Test 3: Per-window result contains: window_index, is_start, is_end,
    oos_start, oos_end."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    windows = wf._generate_windows(multi_year_ohlcv)
    start = datetime(2021, 1, 1)
    # IS in days gets fuzzy due to leap years — check approximate
    window_1_is_end = windows[0]["is_end"]
    delta_days = (window_1_is_end - start).days
    assert 700 < delta_days < 760  # ~2 years with leap year tolerance


# --- Test 4: Pass/fail criteria present ---

def test_passed_criteria_checked(multi_year_ohlcv, mock_backtester):
    """Test 4: Aggregate contains mean_oos_sharpe, mean_oos_profit_factor,
    worst_window_drawdown, mean_is_oos_sharpe_ratio."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    assert "passed" in result
    assert "mean_oos_sharpe" in result["aggregate"]
    assert "mean_oos_profit_factor" in result["aggregate"]
    assert "worst_window_drawdown" in result["aggregate"]
    assert "mean_is_oos_sharpe_ratio" in result["aggregate"]


# --- Test 5: Per-window result structure ---

def test_per_window_result_structure(multi_year_ohlcv, mock_backtester):
    """Test 5: Per-window result contains window_index, is_start, is_end,
    oos_start, oos_end, is_metrics, oos_metrics, is_oos_sharpe_ratio."""
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


# --- Test 6: Insufficient OOS trades produces warning ---

def test_insufficient_oos_trades_produces_warning(multi_year_ohlcv):
    """Test 6: Windows with fewer than min_oos_trades produce warning in result."""
    # Use a very high min OOS trades threshold to trigger warning
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6, min_oos_trades=9999)
    # Use a mock backtester that returns minimal trades
    class FewTradeBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            trades = [{"profit_loss": 10.0, "symbol": symbol} for _ in range(1)]
            equity = list(zip(range(len(df)), np.linspace(10000, 10000 + len(df), len(df))))
            return {"trades": trades, "equity_curve": equity, "final_equity": 10000 + len(df)}
    result = wf.run(multi_year_ohlcv, "EURUSD", FewTradeBacktester(), None, None, lambda df: {})
    assert result["passed"] is not None  # Overall pass/fail still computed
    # At least one window should have a warning
    warnings = [w.get("warning") for w in result["windows"] if w.get("warning")]
    assert len(warnings) > 0


# --- Test 7: Empty data handled gracefully ---

def test_empty_data_returns_no_windows():
    """Test 7: WalkForward gracefully handles empty data — returns empty
    windows list, passed=False, no crash."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    empty_df = pd.DataFrame()
    windows = wf._generate_windows(empty_df)
    assert len(windows) == 0

    # Also test run() with empty data
    class MockBT:
        def run(self, df, symbol, detector, adapter, features_fn):
            return {"trades": [], "equity_curve": [], "final_equity": 10000}
    result = wf.run(empty_df, "EURUSD", MockBT(), None, None, lambda df: {})
    assert result["windows"] == []
    assert result["passed"] is False
    assert "error" in result


# --- Test 8: Window result has is_oos_sharpe_ratio (float) ---

def test_is_oos_sharpe_ratio_is_float(multi_year_ohlcv, mock_backtester):
    """Test 8: Per-window result contains is_oos_sharpe_ratio as float."""
    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)
    result = wf.run(multi_year_ohlcv, "EURUSD", mock_backtester, None, None, lambda df: {})
    for w in result["windows"]:
        assert isinstance(w["is_oos_sharpe_ratio"], float)


# --- Test 9: Pass/fail thresholds work ---

def test_pass_fail_thresholds_enforced(multi_year_ohlcv):
    """Test 9: Pass=TRUE when mean OOS Sharpe > min_sharpe AND mean OOS profit
    factor > min_profit_factor AND worst drawdown < max_drawdown. FALSE otherwise."""
    class GoodBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            n_t = max(1, len(df) // 40)
            trades = [{"profit_loss": 15.0, "symbol": symbol} for _ in range(n_t)]
            eq = list(zip(range(len(df)), np.linspace(10000, 10000 + n_t * 5, len(df))))
            return {"trades": trades, "equity_curve": eq, "final_equity": eq[-1][1]}

    class BadBacktester:
        def run(self, df, symbol, detector, adapter, features_fn):
            n_t = max(1, len(df) // 40)
            trades = [{"profit_loss": -5.0, "symbol": symbol} for _ in range(n_t)]
            eq = list(zip(range(len(df)), np.linspace(10000, 10000 - n_t * 5, len(df))))
            return {"trades": trades, "equity_curve": eq, "final_equity": eq[-1][1]}

    wf = WalkForward(in_sample_years=2, out_of_sample_months=6)

    good_result = wf.run(multi_year_ohlcv, "EURUSD", GoodBacktester(), None, None, lambda df: {})
    bad_result = wf.run(multi_year_ohlcv, "EURUSD", BadBacktester(), None, None, lambda df: {})

    # Good should pass, bad should not
    assert good_result["passed"] is True
    assert bad_result["passed"] is False
