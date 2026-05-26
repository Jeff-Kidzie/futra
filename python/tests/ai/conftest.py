"""Fixtures for AI engine tests — deterministic OHLCV DataFrames without MT5 dependency."""
import pytest
import numpy as np
import pandas as pd


def _make_ohlcv_dataframe(n_rows, close_base=1.0850, volatility=0.001, seed=42):
    """Helper to build realistic OHLCV DataFrames."""
    np.random.seed(seed)
    dates = pd.date_range("2026-01-01", periods=n_rows, freq="1h")
    close = close_base + np.cumsum(np.random.randn(n_rows) * volatility)
    data = pd.DataFrame({
        "time": dates,
        "open": close - np.abs(np.random.randn(n_rows) * volatility * 0.5),
        "high": close + np.abs(np.random.randn(n_rows) * volatility),
        "low": close - np.abs(np.random.randn(n_rows) * volatility),
        "close": close,
        "tick_volume": np.random.randint(500, 2000, n_rows).astype(float),
        "spread": np.full(n_rows, 10.0),
        "real_volume": np.zeros(n_rows),
    })
    return data


@pytest.fixture
def sample_ohlcv_dataframe():
    """200-row DataFrame with realistic EURUSD OHLCV data (close around 1.08-1.10)."""
    return _make_ohlcv_dataframe(200, close_base=1.0850, volatility=0.001)


@pytest.fixture
def flat_market_dataframe():
    """200 rows of near-constant prices (±0.0001) for edge case testing."""
    return _make_ohlcv_dataframe(200, close_base=1.0850, volatility=0.00001)


@pytest.fixture
def tiny_dataframe():
    """20 rows (below min bar threshold of 50) for graceful degradation testing."""
    return _make_ohlcv_dataframe(20, close_base=1.0850, volatility=0.001)


@pytest.fixture
def volatile_dataframe():
    """200 rows with 2% daily swings for volatility feature testing."""
    return _make_ohlcv_dataframe(200, close_base=1.0850, volatility=0.02)
