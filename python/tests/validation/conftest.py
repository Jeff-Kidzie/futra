"""Test fixtures for validation tests."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_ohlcv_dataframe_with_spread():
    """500-bar OHLCV DataFrame with realistic EURUSD prices and spread column.
    
    Prices in 1.08-1.10 range. Spread in points (8-15, representing 0.8-1.5 pips
    at 5-digit precision where 1 pip = 10 points).
    """
    np.random.seed(42)
    n = 500
    dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    base = 1.085
    close = base + np.cumsum(np.random.randn(n) * 0.0001)
    close = np.clip(close, 1.075, 1.095)
    spread_values = np.random.randint(8, 16, n)  # 0.8-1.5 pips at 5-digit precision
    
    return pd.DataFrame({
        "time": dates,
        "open": close - np.random.rand(n) * 0.0002,
        "high": close + np.random.rand(n) * 0.0005,
        "low": close - np.random.rand(n) * 0.0005,
        "close": close,
        "tick_volume": np.random.randint(500, 5000, n),
        "spread": spread_values,
        "real_volume": np.zeros(n),
    })
