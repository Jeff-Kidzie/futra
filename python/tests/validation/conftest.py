"""Fixtures for validation tests — sample OHLCV DataFrames with spread data."""
import pytest
import numpy as np
import pandas as pd


@pytest.fixture
def sample_ohlcv_dataframe_with_spread():
    """500-row OHLCV DataFrame with realistic EURUSD prices (1.08-1.10) and spread column.
    
    Spread values 8-15 points (representing 0.8-1.5 pips at 5-digit precision).
    """
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    # Generate realistic EURUSD prices in range 1.08-1.10
    close = np.linspace(1.08, 1.10, n) + np.random.randn(n) * 0.0005
    close = np.clip(close, 1.08, 1.10)
    spread_values = np.random.randint(8, 16, n)  # 8-15 points
    return pd.DataFrame({
        "time": dates,
        "open": close - np.abs(np.random.randn(n) * 0.0002),
        "high": close + np.abs(np.random.randn(n) * 0.0005),
        "low": close - np.abs(np.random.randn(n) * 0.0005),
        "close": close,
        "tick_volume": np.random.randint(500, 2000, n),
        "spread": spread_values,
        "real_volume": np.zeros(n),
    })


@pytest.fixture
def flat_ohlcv_no_movement():
    """100 bars of perfectly flat EURUSD at 1.085 — no price movement."""
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame({
        "time": dates,
        "open": np.full(n, 1.085),
        "high": np.full(n, 1.086),
        "low": np.full(n, 1.084),
        "close": np.full(n, 1.085),
        "tick_volume": np.ones(n) * 1000,
        "spread": np.full(n, 10),
        "real_volume": np.zeros(n),
    })
