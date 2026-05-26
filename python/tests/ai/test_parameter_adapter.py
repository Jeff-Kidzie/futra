"""Tests for AI parameter adapter (ParameterAdapter)."""
import pytest
from python.ai.parameter_adapter import ParameterAdapter


@pytest.fixture
def adapter():
    """Create a ParameterAdapter with default settings."""
    return ParameterAdapter()


def test_adapt_returns_required_keys(adapter):
    """Test 1: adapt() returns dict with sl_pips, tp_pips, lot_size."""
    result = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    assert "sl_pips" in result
    assert "tp_pips" in result
    assert "lot_size" in result
    assert isinstance(result["sl_pips"], (int, float))
    assert isinstance(result["tp_pips"], (int, float))
    assert isinstance(result["lot_size"], (int, float))


def test_volatile_regime_wider_sl_smaller_lot(adapter):
    """Test 2: volatile regime → wider SL, smaller lot (risk reduction)."""
    normal = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    volatile = adapter.adapt("volatile", 0.8, 0.15, equity=10000.0)
    assert volatile["sl_pips"] > normal["sl_pips"], "Volatile SL should be wider"
    assert volatile["lot_size"] < normal["lot_size"], "Volatile lot should be smaller"


def test_quiet_regime_tighter_sl_normal_lot(adapter):
    """Test 3: quiet regime → tighter SL, normal lot."""
    normal = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    quiet = adapter.adapt("quiet", 0.8, 0.15, equity=10000.0)
    assert quiet["sl_pips"] < normal["sl_pips"], "Quiet SL should be tighter"


def test_trending_regime_wider_tp(adapter):
    """Test 4: trending regime → wider TP (let winners run)."""
    ranging = adapter.adapt("ranging", 0.8, 0.15, equity=10000.0)
    trending = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    assert trending["tp_pips"] > ranging["tp_pips"], "Trending TP should be wider"


def test_ranging_regime_tighter_tp(adapter):
    """Test 5: ranging regime → tighter TP (take profit at range boundaries)."""
    trending = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    ranging = adapter.adapt("ranging", 0.8, 0.15, equity=10000.0)
    assert ranging["tp_pips"] < trending["tp_pips"], "Ranging TP should be tighter"


def test_low_confidence_falls_back_to_conservative(adapter):
    """Test 6: Low confidence (<0.5) → conservative defaults regardless of regime."""
    high_conf = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    low_conf = adapter.adapt("trending", 0.3, 0.15, equity=10000.0)
    assert low_conf["sl_pips"] == adapter.default_sl, "Low conf should use default SL"
    assert low_conf["tp_pips"] == adapter.default_tp, "Low conf should use default TP"
    assert low_conf["lot_size"] == adapter.default_lot, "Low conf should use default lot"


def test_equity_scales_lot_proportionally(adapter):
    """Test 7: $10,000 equity produces larger lot than $1,000."""
    lot_small = adapter.adapt("trending", 0.8, 0.15, equity=1000.0)["lot_size"]
    lot_large = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)["lot_size"]
    assert lot_large > lot_small, f"Large equity lot ({lot_large}) should exceed small ({lot_small})"


def test_higher_atr_wider_sl(adapter):
    """Test 8: Higher ATR → wider SL in pips."""
    low_atr = adapter.adapt("trending", 0.8, 0.15, equity=10000.0, atr_pips=15.0)
    high_atr = adapter.adapt("trending", 0.8, 0.15, equity=10000.0, atr_pips=40.0)
    assert high_atr["sl_pips"] > low_atr["sl_pips"], "Higher ATR should produce wider SL"


def test_lot_size_capped_at_max_position_size(adapter):
    """Test 9: lot_size always capped at max_position_size."""
    adapter_small = ParameterAdapter(max_position_size=0.05)
    result = adapter_small.adapt("trending", 0.8, 0.15, equity=100000.0)
    assert result["lot_size"] <= 0.05, f"Lot {result['lot_size']} should not exceed max 0.05"


def test_sl_and_tp_always_positive(adapter):
    """Test 10: sl_pips and tp_pips are always > 0."""
    regimes = ["trending", "ranging", "volatile", "quiet"]
    for regime in regimes:
        result = adapter.adapt(regime, 0.8, 0.15, equity=10000.0)
        assert result["sl_pips"] > 0, f"SL should be positive for {regime}"
        assert result["tp_pips"] > 0, f"TP should be positive for {regime}"


def test_to_ipc_params_produces_correct_format(adapter):
    """Additional: to_ipc_params() returns dict with IPC-compatible keys."""
    adapted = adapter.adapt("trending", 0.8, 0.15, equity=10000.0)
    ipc = adapter.to_ipc_params(adapted, "EURUSD")
    assert ipc["symbol"] == "EURUSD"
    assert "sl_percent" in ipc
    assert "tp_percent" in ipc
    assert "max_position_size" in ipc
    assert "regime" in ipc
    assert "confidence" in ipc
    assert ipc["sl_percent"] > 0
    assert ipc["tp_percent"] > 0
