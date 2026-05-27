import pytest
import numpy as np
from python.validation.monte_carlo import MonteCarlo


@pytest.fixture
def positive_trades():
    """50 trades, all +$100 profit."""
    return [{"profit_loss": 100.0, "symbol": "EURUSD"} for _ in range(50)]


@pytest.fixture
def mixed_trades():
    """75 trades: 50 wins at $100, 25 losses at -$50. Positive expectancy."""
    wins = [{"profit_loss": 100.0, "symbol": "EURUSD"} for _ in range(50)]
    losses = [{"profit_loss": -50.0, "symbol": "EURUSD"} for _ in range(25)]
    return wins + losses


@pytest.fixture
def negative_trades():
    """All losing trades."""
    return [{"profit_loss": -10.0, "symbol": "EURUSD"} for _ in range(100)]


@pytest.fixture
def mc():
    """MonteCarlo with 500 iterations for fast testing."""
    return MonteCarlo(iterations=500, initial_equity=10000.0, random_seed=42)


def test_run_returns_expected_keys(mc, positive_trades):
    """Test 1: MonteCarlo.run() returns dict with expected top-level keys."""
    result = mc.run(positive_trades)
    assert "iterations" in result
    assert "final_equity" in result
    assert "max_drawdown" in result
    assert "sharpe_ratio" in result
    assert "profit_factor" in result
    assert "confidence_in_profitability" in result
    assert result["iterations"] == 500


def test_metric_stats_have_all_percentiles(mc, positive_trades):
    """Test 2: Each metric stats dict contains mean, median, pct_5, pct_25,
    pct_75, pct_95."""
    result = mc.run(positive_trades)
    for key in ["mean", "median", "pct_5", "pct_25", "pct_75", "pct_95"]:
        assert key in result["final_equity"]


def test_all_positive_trades_cip_100(mc, positive_trades):
    """Test 3: All-positive trades → CIP = 100% (1.0)."""
    result = mc.run(positive_trades)
    assert result["confidence_in_profitability"] == 1.0


def test_positive_expectancy_high_cip(mc, mixed_trades):
    """Test 4: Positive expectancy trades → CIP > 90%."""
    result = mc.run(mixed_trades)
    # 50*$100 + 25*(-$50) = $3750 total profit positive
    # CIP should be very high (almost always profitable)
    assert result["confidence_in_profitability"] > 0.90


def test_negative_expectancy_cip_zero(mc, negative_trades):
    """Test 5: All negative expectancy trades → CIP = 0% (0.0)."""
    result = mc.run(negative_trades)
    assert result["confidence_in_profitability"] == 0.0


def test_empty_trades_no_crash(mc):
    """Test 6: Empty trades list → returns all-zero stats, CIP=0%, no crash."""
    result = mc.run([])
    assert result["iterations"] == 0
    assert result["confidence_in_profitability"] == 0.0
    assert result["final_equity"]["mean"] == 0


def test_final_equity_positive_for_positive_trades(mc, positive_trades):
    """Test 7: Positive trades produce mean final equity > initial equity."""
    result = mc.run(positive_trades)
    assert result["final_equity"]["mean"] > 10000  # Above initial equity


# --- Test 8: Variable equity curves (not all identical) ---

def test_bootstrapping_produces_variable_results():
    """Test 8: With same trades, different random seeds produce different
    equity curves (randomness verified with different seeds)."""
    mc1 = MonteCarlo(iterations=200, initial_equity=10000.0, random_seed=42)
    mc2 = MonteCarlo(iterations=200, initial_equity=10000.0, random_seed=99)

    trades = [{"profit_loss": 50.0, "symbol": "EURUSD"} for _ in range(20)]
    trades += [{"profit_loss": -20.0, "symbol": "EURUSD"} for _ in range(10)]

    r1 = mc1.run(trades)
    r2 = mc2.run(trades)

    # Different seeds should produce different metric values
    assert r1["final_equity"]["mean"] != r2["final_equity"]["mean"]
