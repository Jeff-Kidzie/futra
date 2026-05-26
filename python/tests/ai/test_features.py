"""Tests for AI feature engineering module (compute_features)."""
import pytest
import numpy as np
import pandas as pd
from python.ai.features import compute_features


REQUIRED_KEYS = {
    "atr_14", "volatility_20", "rsi_14", "macd", "macd_signal",
    "adx_14", "sma_20_50_ratio", "bb_width_pct", "close_to_sma20_pct",
    "volume_ratio",
}


def test_compute_features_accepts_ohlcv_dataframe(sample_ohlcv_dataframe):
    """Test 1: compute_features() accepts OHLCV DataFrame and returns dict of features."""
    df = sample_ohlcv_dataframe
    result = compute_features(df)
    assert isinstance(result, dict)
    assert REQUIRED_KEYS.issubset(set(result.keys()))
    for key in REQUIRED_KEYS:
        assert isinstance(result[key], float), f"{key} should be float, got {type(result[key])}"


def test_volatility_features_are_positive(sample_ohlcv_dataframe):
    """Test 2: ATR and historical volatility are positive floats."""
    df = sample_ohlcv_dataframe
    result = compute_features(df)
    assert result["atr_14"] > 0, f"ATR should be positive, got {result['atr_14']}"
    assert result["volatility_20"] > 0, f"Volatility should be positive, got {result['volatility_20']}"


def test_momentum_features_in_valid_range(sample_ohlcv_dataframe):
    """Test 3: RSI in [0,100]; MACD and signal line computed."""
    df = sample_ohlcv_dataframe
    result = compute_features(df)
    assert 0 <= result["rsi_14"] <= 100, f"RSI should be in [0,100], got {result['rsi_14']}"
    assert isinstance(result["macd"], float), "MACD should be float"
    assert isinstance(result["macd_signal"], float), "MACD signal should be float"


def test_trend_features_present(sample_ohlcv_dataframe):
    """Test 4: ADX present; SMA ratio > 0."""
    df = sample_ohlcv_dataframe
    result = compute_features(df)
    assert isinstance(result["adx_14"], float), "ADX should be float"
    assert result["sma_20_50_ratio"] > 0, f"SMA ratio should be > 0, got {result['sma_20_50_ratio']}"


def test_regime_features_are_floats(sample_ohlcv_dataframe):
    """Test 5: BB width and close-to-SMA distance are floats."""
    df = sample_ohlcv_dataframe
    result = compute_features(df)
    assert isinstance(result["bb_width_pct"], float), "BB width should be float"
    assert isinstance(result["close_to_sma20_pct"], float), "Close-to-SMA should be float"


def test_compute_features_handles_tiny_dataframe(tiny_dataframe):
    """Test 6: Returns NaN-filled features when DataFrame has < 50 rows."""
    df = tiny_dataframe
    result = compute_features(df)
    assert REQUIRED_KEYS.issubset(set(result.keys()))
    # All values should be NaN for insufficient data
    for key in REQUIRED_KEYS:
        assert pd.isna(result[key]), f"{key} should be NaN for tiny DataFrame, got {result[key]}"


def test_compute_features_preserves_input_dataframe(sample_ohlcv_dataframe):
    """Test 7: Input DataFrame is not modified — column order unchanged, no side effects."""
    df = sample_ohlcv_dataframe
    original_columns = list(df.columns)
    original_shape = df.shape
    original_values = df.copy()

    compute_features(df)

    assert list(df.columns) == original_columns, "Columns should not change"
    assert df.shape == original_shape, "Shape should not change"
    pd.testing.assert_frame_equal(df, original_values, check_exact=False)
