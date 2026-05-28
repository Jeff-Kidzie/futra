"""Test performance metrics: Sharpe, Sortino, drawdown, profit factor, etc.

TDD RED phase — all tests expect python/validation/metrics.py to exist
with the pure computation functions specified in 03-01-PLAN.md.
"""

import pytest
import numpy as np
from datetime import datetime

from python.validation.metrics import (
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_max_drawdown,
    compute_profit_factor,
    compute_win_rate,
    compute_avg_win_loss,
    compute_total_return,
    compute_calmar_ratio,
    compute_all_metrics,
)


# ── Test fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def rising_equity():
    """Steady 10% growth over 100 periods."""
    values = np.linspace(10000, 11000, 100)
    dates = [datetime(2024, 1, 1)] * 100  # Timestamps don't matter for math
    return list(zip(dates, values))


@pytest.fixture
def flat_equity():
    """Flat equity — zero returns."""
    values = np.ones(100) * 10000.0
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
def asymmetric_equity():
    """Many small gains, few large losses — asymmetric returns for Sortino test."""
    np.random.seed(42)
    values = [10000.0]
    for i in range(99):
        if i % 5 == 0:
            # Every 5th period: small loss
            values.append(values[-1] * 0.998)
        else:
            # Other periods: small gain
            values.append(values[-1] * 1.003)
    dates = [datetime(2024, 1, 1)] * 100
    return list(zip(dates, values))


@pytest.fixture
def sample_trades():
    """5 winning trades, 3 losing trades with known values."""
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


@pytest.fixture
def all_win_trades():
    """All winning trades — no losses."""
    return [
        {"profit_loss": 100, "symbol": "EURUSD"},
        {"profit_loss": 200, "symbol": "EURUSD"},
        {"profit_loss": 150, "symbol": "EURUSD"},
    ]


# ── Test 1: Rising equity → positive Sharpe ──────────────────────────────

def test_sharpe_rising_equity_positive(rising_equity):
    sharpe = compute_sharpe_ratio(rising_equity)
    assert sharpe > 0, f"Expected positive Sharpe for rising equity, got {sharpe}"


# ── Test 2: Flat equity → Sharpe ≈ 0 ─────────────────────────────────────

def test_sharpe_flat_equity_near_zero(flat_equity):
    sharpe = compute_sharpe_ratio(flat_equity)
    assert abs(sharpe) < 1.0, f"Expected Sharpe near 0 for flat equity, got {sharpe}"


# ── Test 3: Declining equity → negative Sharpe ───────────────────────────

def test_sharpe_declining_equity_negative(declining_equity):
    sharpe = compute_sharpe_ratio(declining_equity)
    assert sharpe < 0, f"Expected negative Sharpe for declining equity, got {sharpe}"


# ── Test 4: Sortino < Sharpe for asymmetric returns ──────────────────────

def test_sortino_less_than_sharpe_asymmetric(asymmetric_equity):
    sharpe = compute_sharpe_ratio(asymmetric_equity)
    sortino = compute_sortino_ratio(asymmetric_equity)
    # With asymmetric returns (few downsides), Sortino should differ from Sharpe
    # Sortino penalizes downside only; Sharpe penalizes all volatility
    assert isinstance(sortino, float)
    assert isinstance(sharpe, float)
    # Sortino should be higher than Sharpe when downside vol < total vol
    assert sortino > sharpe, f"Expected Sortino ({sortino}) > Sharpe ({sharpe}) for asymmetric returns"


# ── Test 5: Exact max drawdown with known peaks/troughs ──────────────────

def test_max_drawdown_exact(v_shaped_equity):
    mdd = compute_max_drawdown(v_shaped_equity)
    # Peak at 11000, trough at 9000 → MDD = (11000-9000)/11000 = 0.1818
    assert 0.18 < mdd < 0.19, f"Expected MDD ~0.1818, got {mdd}"


# ── Test 6: Profit factor — correct calculation ─────────────────────────

def test_profit_factor_correct(sample_trades):
    pf = compute_profit_factor(sample_trades)
    # Profits: 100+150+200+120+180 = 750
    # Losses: 50+30+80 = 160
    # PF = 750/160 = 4.6875
    assert 4.6 < pf < 4.7, f"Expected PF ~4.6875, got {pf}"


# ── Test 7: Profit factor with zero losses → inf ────────────────────────

def test_profit_factor_zero_losses_inf(all_win_trades):
    pf = compute_profit_factor(all_win_trades)
    assert pf == float('inf'), f"Expected inf with zero losses, got {pf}"


# ── Test 8: Win rate — correct calculation ──────────────────────────────

def test_win_rate_correct(sample_trades):
    wr = compute_win_rate(sample_trades)
    # 5 wins out of 8 = 0.625
    assert wr == 5/8, f"Expected win rate 5/8, got {wr}"


# ── Test 9: Avg win/loss ratio — correct calculation ────────────────────

def test_avg_win_loss_correct(sample_trades):
    awl = compute_avg_win_loss(sample_trades)
    # avg win = (100+150+200+120+180)/5 = 750/5 = 150
    # avg loss = (50+30+80)/3 = 160/3 ≈ 53.33
    # ratio = 150 / 53.33 ≈ 2.8125
    assert 2.8 < awl < 2.83, f"Expected avg win/loss ~2.8125, got {awl}"


# ── Test 10: Total return — correct percentage ──────────────────────────

def test_total_return_correct(rising_equity):
    tr = compute_total_return(rising_equity)
    # Start 10000, end 11000 → 1000/10000 = 0.10
    assert tr == pytest.approx(0.10, rel=1e-6)


def test_total_return_declining(declining_equity):
    tr = compute_total_return(declining_equity)
    # Start 10000, end 9000 → -1000/10000 = -0.10
    assert tr == pytest.approx(-0.10, rel=1e-6)


# ── Test 11: Calmar ratio — annualized return / max drawdown ────────────

def test_calmar_ratio_correct(rising_equity):
    # Rising with 10% return, near-zero drawdown → high Calmar
    cr = compute_calmar_ratio(rising_equity)
    # 10% return / tiny drawdown ≈ large number
    assert cr > 0, f"Expected positive Calmar for rising equity, got {cr}"


def test_calmar_ratio_with_v_shape(v_shaped_equity):
    cr = compute_calmar_ratio(v_shaped_equity)
    # End at 10500 from 10000 → 5% return / 18.18% MDD ≈ 0.275
    assert 0.2 < cr < 0.35, f"Expected Calmar ~0.275, got {cr}"


# ── Test 12: compute_all_metrics returns all expected keys ───────────────

def test_all_metrics_returns_all_keys(sample_trades, rising_equity):
    result = compute_all_metrics(sample_trades, rising_equity)
    expected_keys = {
        "sharpe_ratio", "sortino_ratio", "max_drawdown",
        "profit_factor", "win_rate", "avg_win_loss",
        "total_return", "calmar_ratio", "total_trades"
    }
    assert expected_keys == set(result.keys()), f"Missing keys: {expected_keys - set(result.keys())}"
    assert result["total_trades"] == 8


# ── Test 13: Empty trades → zeros/NaN, no crash ─────────────────────────

def test_all_metrics_empty_trades_no_crash():
    equity = [(datetime.now(), 10000.0)]
    result = compute_all_metrics([], equity)
    assert result["total_trades"] == 0
    assert result["sharpe_ratio"] == 0.0
    assert result["win_rate"] == 0.0
    # Should not crash
