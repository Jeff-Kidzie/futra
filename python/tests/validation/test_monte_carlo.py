"""Tests for Monte Carlo simulation — trade-reshuffling bootstrap.

Per BACK-04: Tests strategy robustness across randomized trade sequences.
"""
import pytest
import numpy as np


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
    from python.validation.monte_carlo import MonteCarlo
    return MonteCarlo(iterations=500, initial_equity=10000.0, random_seed=42)


# --- Test 1: run() returns all expected keys ---
def test_run_returns_expected_keys(mc, positive_trades):
    result = mc.run(positive_trades)
    assert "iterations" in result
    assert "final_equity" in result
    assert "max_drawdown" in result
    assert "sharpe_ratio" in result
    assert "profit_factor" in result
    assert "confidence_in_profitability" in result
    assert result["iterations"] == 500


# --- Test 2: Each metric stats dict contains all percentile fields ---
def test_metric_stats_have_all_percentiles(mc, positive_trades):
    result = mc.run(positive_trades)
    for key in ["mean", "median", "pct_5", "pct_25", "pct_75", "pct_95"]:
        assert key in result["final_equity"], f"Missing {key} in final_equity"
        assert key in result["max_drawdown"], f"Missing {key} in max_drawdown"
        assert key in result["sharpe_ratio"], f"Missing {key} in sharpe_ratio"
        assert key in result["profit_factor"], f"Missing {key} in profit_factor"


# --- Test 3: All-positive trades → CIP = 100% ---
def test_all_positive_trades_cip_100(mc, positive_trades):
    result = mc.run(positive_trades)
    assert result["confidence_in_profitability"] == 1.0


# --- Test 4: Mixed positive-expectancy trades → CIP > 90% ---
def test_positive_expectancy_high_cip(mc, mixed_trades):
    result = mc.run(mixed_trades)
    # 50*$100 + 25*(-$50) = $3750 total profit positive
    # CIP should be very high (almost always profitable)
    assert result["confidence_in_profitability"] > 0.90


# --- Test 5: Negative expectancy trades → CIP = 0% ---
def test_negative_expectancy_cip_zero(mc, negative_trades):
    result = mc.run(negative_trades)
    assert result["confidence_in_profitability"] == 0.0


# --- Test 6: N iterations produces correct count ---
def test_iteration_count_matches_configured(positive_trades):
    from python.validation.monte_carlo import MonteCarlo
    mc_custom = MonteCarlo(iterations=100, random_seed=42)
    result = mc_custom.run(positive_trades)
    assert result["iterations"] == 100


# --- Test 7: Reshuffling produces different results (not all identical) ---
def test_reshuffling_produces_variable_results(positive_trades):
    from python.validation.monte_carlo import MonteCarlo
    # Two runs with different seeds produce different equity distributions
    mc1 = MonteCarlo(iterations=200, random_seed=42)
    mc2 = MonteCarlo(iterations=200, random_seed=99)
    result1 = mc1.run(positive_trades)
    result2 = mc2.run(positive_trades)
    # With different seeds, the mean final equity should differ slightly
    assert result1["final_equity"]["mean"] != result2["final_equity"]["mean"]


# --- Test 8: Empty trades list handled gracefully ---
def test_empty_trades_no_crash(mc):
    result = mc.run([])
    assert result["iterations"] == 0
    assert result["confidence_in_profitability"] == 0.0
    assert result["final_equity"]["mean"] == 0
