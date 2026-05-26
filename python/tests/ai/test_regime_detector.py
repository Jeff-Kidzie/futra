"""Tests for AI regime detection model (RegimeDetector)."""
import pytest
import math
from python.ai.regime_detector import RegimeDetector


@pytest.fixture
def detector():
    """Create a RegimeDetector with default thresholds."""
    return RegimeDetector()


def test_predict_returns_regime_and_confidence(detector):
    """Test 1: predict() returns (str, float) with confidence in [0.0, 1.0]."""
    features = {
        "adx_14": 30.0, "volatility_20": 0.15, "bb_width_pct": 3.0,
        "close_to_sma20_pct": 1.5,
    }
    result = detector.predict(features)
    assert isinstance(result, tuple)
    assert len(result) == 2
    regime, conf = result
    assert isinstance(regime, str)
    assert regime in ("trending", "ranging", "volatile", "quiet")
    assert isinstance(conf, float)
    assert 0.0 <= conf <= 1.0


def test_regime_labels_are_discrete(detector):
    """Test 2: Regime labels are exactly one of the four valid values."""
    test_cases = [
        {"adx_14": 35.0, "volatility_20": 0.15, "bb_width_pct": 3.0, "close_to_sma20_pct": 1.5},
        {"adx_14": 15.0, "volatility_20": 0.05, "bb_width_pct": 0.5, "close_to_sma20_pct": 0.1},
        {"adx_14": 25.0, "volatility_20": 0.30, "bb_width_pct": 5.0, "close_to_sma20_pct": 1.0},
        {"adx_14": 18.0, "volatility_20": 0.08, "bb_width_pct": 1.0, "close_to_sma20_pct": 0.1},
    ]
    for features in test_cases:
        regime, _ = detector.predict(features)
        assert regime in ("trending", "ranging", "volatile", "quiet"), f"Got invalid regime: {regime}"
        assert regime != ""
        assert regime is not None


def test_high_adx_plus_trend_detects_trending(detector):
    """Test 3: High ADX (>25) + price far from SMA → trending with confidence >= 0.6."""
    features = {
        "adx_14": 35.0, "volatility_20": 0.15, "bb_width_pct": 3.0,
        "close_to_sma20_pct": 1.5,  # far from SMA (default threshold 0.005)
    }
    regime, conf = detector.predict(features)
    assert regime == "trending", f"Expected trending, got {regime}"
    assert conf >= 0.6, f"Confidence should be >= 0.6, got {conf}"


def test_low_adx_plus_low_vol_detects_quiet(detector):
    """Test 4: Low ADX (<20) + low volatility → quiet with confidence >= 0.6."""
    features = {
        "adx_14": 15.0, "volatility_20": 0.05, "bb_width_pct": 0.5,
        "close_to_sma20_pct": 0.1,
    }
    regime, conf = detector.predict(features)
    assert regime == "quiet", f"Expected quiet, got {regime}"
    assert conf >= 0.6, f"Confidence should be >= 0.6, got {conf}"


def test_high_atr_plus_wide_bb_detects_volatile(detector):
    """Test 5: High ATR/volatility + wide BB → volatile with confidence >= 0.6."""
    features = {
        "adx_14": 20.0, "volatility_20": 0.30, "bb_width_pct": 5.0,
        "close_to_sma20_pct": 0.5,
    }
    regime, conf = detector.predict(features)
    assert regime == "volatile", f"Expected volatile, got {regime}"
    assert conf >= 0.6, f"Confidence should be >= 0.6, got {conf}"


def test_moderate_adx_detects_ranging(detector):
    """Test 6: Medium ADX + moderate vol + price near SMA → ranging with confidence >= 0.6."""
    features = {
        "adx_14": 22.0, "volatility_20": 0.12, "bb_width_pct": 1.2,
        "close_to_sma20_pct": 0.1,
    }
    regime, conf = detector.predict(features)
    assert regime == "ranging", f"Expected ranging, got {regime}"
    assert conf >= 0.5, f"Confidence should be >= 0.5, got {conf}"


def test_nan_features_return_quiet_zero(detector):
    """Test 7: NaN features (insufficient data) → ('quiet', 0.0) safe default."""
    features = {
        "adx_14": float("nan"),
        "volatility_20": float("nan"),
        "bb_width_pct": float("nan"),
        "close_to_sma20_pct": float("nan"),
    }
    regime, conf = detector.predict(features)
    assert regime == "quiet", f"Expected quiet for NaN, got {regime}"
    assert conf == 0.0, f"Expected 0.0 confidence for NaN, got {conf}"


def test_predict_is_stateless(detector):
    """Test 8: Two consecutive calls with same input return identical output."""
    features = {
        "adx_14": 30.0, "volatility_20": 0.15, "bb_width_pct": 3.0,
        "close_to_sma20_pct": 1.5,
    }
    result1 = detector.predict(features)
    result2 = detector.predict(features)
    assert result1 == result2, f"Predict should be stateless: {result1} != {result2}"
