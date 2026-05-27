"""Tests for performance metrics: Sharpe, Sortino, drawdown, profit factor, etc.

All tests are pure Python/numpy — no MT5 connection required.
"""
import pytest
import numpy as np
from datetime import datetime
from python.validation.metrics import (
    compute_sharpe_ratio, compute_sortino_ratio,
    compute_max_drawdown, compute_profit_factor,
    compute_win_rate, compute_avg_win_loss,
    compute_total_return, compute_calmar_ratio,
    compute_all_metrics,
)


# --- Fixtures ---

@pytest.fixture
def rising_equity():
    """Steady 10% growth over 100 periods."""
    values = np.linspace(10000, 11000, 100)
    dates = [datetime(2024, 1, 1)] * 100
    return list(zip(dates, values))


@pytest.fixture
def flat_equity():
    """Flat equity at 10000."""
    values = np.full(100, 10000.0)
    dates = [datetime(2024, 1, 1)] * 100
    return list(zip(dates, values))


@pytest.fixture
def declining_equity():
    """Steady 10% decline over 100 periods."""
    values = np.linspace(10000, 9000, 100)
    dates = [datetime(2024, 1, 1)] * 100
    return list(zip(dates, values))


@pytest.fixture
def v_shaped_equity():
    """Peak at 11000, trough at 9000, back to 10500."""
    values = [10000]*10 + list(np.linspace(10000, 11000, 30)) + \
             list(np.linspace(11000, 9000, 40)) + list(np.linspace(9000, 10500, 20))
    dates = [datetime(2024, 1, 1)] * 100
    return list(zip(dates, values))


@pytest.fixture
def sample_trades():
    """5 winning trades, 3 losing trades."""
    return [
        {"profit_loss": 100, "symbol": "EURUSD"},
        {"profit_loss": 150, "symbol": "EURUSD"},
        {"profit_loss": -50, "symbol": "EURUSD"},
        {"profit_loss": 200, "symbol": "GBPUSD"},
        {"profit_loss": -30, "symbol": "EURUSD"},
        {"profit_loss": 120, "symbol": "USDJPY"},
        {"profit_loss": -80, "symbol": "EURUSD"},
        {"profit_loss": 180, "symbol": "EURUSD"},
    ]


# --- Test 1: Sharpe ratio with rising equity ---

def test_sharpe_rising_equity_positive(rising_equity):
    """Rising equity produces positive Sharpe ratio."""
    sharpe = compute_sharpe_ratio(rising_equity)
    assert sharpe > 0, f"Expected positive Sharpe, got {sharpe}"


# --- Test 2: Sharpe ratio with flat equity ---

def test_sharpe_flat_equity_zero(flat_equity):
    """Flat equity produces Sharpe ≈ 0."""
    sharpe = compute_sharpe_ratio(flat_equity)
    assert sharpe == pytest.approx(0.0, abs=1.0), f"Expected ~0 Sharpe, got {sharpe}"


# --- Test 3: Sharpe ratio with declining equity ---

def test_sharpe_declining_equity_negative(declining_equity):
    """Declining equity produces negative Sharpe ratio."""
    sharpe = compute_sharpe_ratio(declining_equity)
    assert sharpe < 0, f"Expected negative Sharpe, got {sharpe}"


# --- Test 4: Sortino ratio vs Sharpe for asymmetric returns ---

def test_sortino_ratio_punishes_downside(rising_equity):
    """Sortino ratio punishes downside more than Sharpe.
    
    For the same steady rising equity, Sortino should be >= Sharpe
    because there's no downside volatility.
    """
    sharpe = compute_sharpe_ratio(rising_equity)
    sortino = compute_sortino_ratio(rising_equity)
    # With no downside (steadily rising), Sortino should be >= Sharpe
    # It can be inf because there's no negative returns
    if sortino != float('inf'):
        assert sortino >= sharpe, f"Sortino {sortino} should be >= Sharpe {sharpe}"


# --- Test 5: Max drawdown with exact peak/trough ---

def test_max_drawdown_exact(v_shaped_equity):
    """Max drawdown from exact peak at 11000 to trough at 9000 = 18.18%.
    
    Peak at index ~40 (11000), trough at index ~80 (9000).
    MDD = (11000 - 9000) / 11000 = 2000/11000 = 18.18%
    """
    mdd = compute_max_drawdown(v_shaped_equity)
    assert 0.18 < mdd < 0.19, f"Expected ~18.18% MDD, got {mdd}"


# --- Test 6: Profit factor with known trades ---

def test_profit_factor_correct(sample_trades):
    """Profit factor = gross_profit / |gross_loss|.
    
    Profits: 100 + 150 + 200 + 120 + 180 = 750
    Losses: 50 + 30 + 80 = 160
    PF = 750 / 160 = 4.6875
    """
    pf = compute_profit_factor(sample_trades)
    assert 4.6 < pf < 4.7, f"Expected ~4.6875 PF, got {pf}"


# --- Test 7: Profit factor with zero losses ---

def test_profit_factor_zero_losses():
    """Profit factor is inf when there are no losses."""
    all_wins = [
        {"profit_loss": 100, "symbol": "EURUSD"},
        {"profit_loss": 200, "symbol": "GBPUSD"},
    ]
    pf = compute_profit_factor(all_wins)
    assert pf == float('inf'), f"Expected inf PF, got {pf}"


# --- Test 8: Win rate ---

def test_win_rate_correct(sample_trades):
    """Win rate = wins / total = 5/8 = 0.625."""
    wr = compute_win_rate(sample_trades)
    assert wr == 5/8, f"Expected 0.625 win rate, got {wr}"


# --- Test 9: Avg win/loss ---

def test_avg_win_loss_correct(sample_trades):
    """Avg win / avg loss.
    
    Avg win: (100 + 150 + 200 + 120 + 180) / 5 = 750/5 = 150
    Avg loss: (50 + 30 + 80) / 3 = 160/3 = 53.33
    Ratio: 150 / 53.33 = 2.8125
    """
    ratio = compute_avg_win_loss(sample_trades)
    assert 2.7 < ratio < 2.9, f"Expected ~2.8125 ratio, got {ratio}"


# --- Test 10: Total return ---

def test_total_return_correct(rising_equity):
    """Total return = (end - start) / start = (11000 - 10000) / 10000 = 10%."""
    total_return = compute_total_return(rising_equity)
    assert total_return == pytest.approx(0.10, abs=0.005), \
        f"Expected 10% return, got {total_return}"


# --- Test 11: Calmar ratio ---

def test_calmar_ratio_with_positive_return(v_shaped_equity):
    """Calmar = total_return / max_drawdown.
    
    total_return ≈ (10500-10000)/10000 = 0.05 (5% overall)
    MDD ≈ 18.18%
    Calmar ≈ 0.05 / 0.1818 ≈ 0.275
    """
    calmar = compute_calmar_ratio(v_shaped_equity)
    assert 0.2 < calmar < 0.4, f"Expected ~0.275 Calmar, got {calmar}"


def test_calmar_ratio_inf_with_no_drawdown(rising_equity):
    """Calmar is inf when there's positive return and no drawdown."""
    calmar = compute_calmar_ratio(rising_equity)
    assert calmar == float('inf'), f"Expected inf Calmar, got {calmar}"


# --- Test 12: compute_all_metrics returns all keys ---

def test_all_metrics_returns_all_keys(sample_trades, rising_equity):
    """compute_all_metrics() returns dict with all expected keys."""
    result = compute_all_metrics(sample_trades, rising_equity)
    expected_keys = {
        "sharpe_ratio", "sortino_ratio", "max_drawdown",
        "profit_factor", "win_rate", "avg_win_loss",
        "total_return", "calmar_ratio", "total_trades"
    }
    assert expected_keys == set(result.keys()), \
        f"Keys mismatch. Extra: {set(result.keys()) - expected_keys}. Missing: {expected_keys - set(result.keys())}"
    assert result["total_trades"] == 8


# --- Test 13: Empty trades / single-point equity ---

def test_all_metrics_empty_trades_no_crash():
    """compute_all_metrics() with empty trades and minimal equity curve
    returns zeros/None and doesn't crash.
    """
    result = compute_all_metrics([], [(datetime.now(), 10000.0)])
    assert result["total_trades"] == 0
    assert result["sharpe_ratio"] == 0.0
    assert result["sortino_ratio"] == 0.0
    assert result["max_drawdown"] == 0.0
    assert result["total_return"] == 0.0
