"""Tests for AI strategy manager (StrategyManager)."""
import json
import pytest
from pathlib import Path
from python.ai.regime_detector import RegimeDetector
from python.ai.parameter_adapter import ParameterAdapter
from python.ai.strategy_manager import StrategyManager


@pytest.fixture
def manager(tmp_path):
    return StrategyManager(strategy_dir=tmp_path / "strategies")


@pytest.fixture
def detector():
    return RegimeDetector(adx_trend_threshold=30.0, adx_low_threshold=15.0)


@pytest.fixture
def adapter():
    return ParameterAdapter(max_position_size=0.2, default_sl_pips=60.0, default_tp_pips=120.0)


def test_export_writes_valid_json(manager, detector, adapter, tmp_path):
    """Test 1: Export writes a valid JSON file."""
    path = manager.export_strategy(
        detector, adapter, filepath=tmp_path / "test_strategy.json"
    )
    assert path.exists()
    data = json.loads(path.read_text())
    assert "metadata" in data
    assert "regime_detector" in data
    assert "parameter_adapter" in data


def test_export_contains_detector_thresholds(manager, detector, adapter, tmp_path):
    """Test 2: Exported JSON has all 7 RegimeDetector thresholds."""
    path = manager.export_strategy(
        detector, adapter, filepath=tmp_path / "test_strategy.json"
    )
    data = json.loads(path.read_text())
    reg = data["regime_detector"]
    assert reg["adx_trend_threshold"] == 30.0
    assert reg["adx_low_threshold"] == 15.0
    assert "volatility_high_threshold" in reg
    assert "bb_width_high" in reg
    assert "trend_ratio_far" in reg


def test_export_contains_adapter_settings(manager, detector, adapter, tmp_path):
    """Test 3: Exported JSON has all 5 ParameterAdapter numeric settings."""
    path = manager.export_strategy(
        detector, adapter, filepath=tmp_path / "test_strategy.json"
    )
    data = json.loads(path.read_text())
    par = data["parameter_adapter"]
    assert par["max_position_size"] == 0.2
    assert par["default_sl_pips"] == 60.0
    assert par["default_tp_pips"] == 120.0
    assert par["default_lot_size"] == 0.10
    assert par["max_risk_pct"] == 0.02


def test_export_includes_metadata(manager, detector, adapter, tmp_path):
    """Test 4: Exported JSON has metadata with exported_at, version, description."""
    path = manager.export_strategy(
        detector, adapter,
        filepath=tmp_path / "test_strategy.json",
        description="Test strategy v1",
    )
    data = json.loads(path.read_text())
    meta = data["metadata"]
    assert meta["version"] == "1.0.0"
    assert "exported_at" in meta
    assert meta["description"] == "Test strategy v1"


def test_import_reads_strategy(manager, detector, adapter, tmp_path):
    """Test 5: import_strategy() reads and returns strategy dict."""
    path = manager.export_strategy(
        detector, adapter, filepath=tmp_path / "test_strategy.json"
    )
    strategy = manager.import_strategy(path)
    assert strategy["regime_detector"]["adx_trend_threshold"] == 30.0
    assert strategy["parameter_adapter"]["max_position_size"] == 0.2


def test_round_trip_produces_identical_output(manager, detector, adapter, tmp_path):
    """Test 6: Round-trip export→import→apply produces same predict/adapt output."""
    path = manager.export_strategy(
        detector, adapter, filepath=tmp_path / "test_strategy.json"
    )

    strategy = manager.import_strategy(path)
    new_detector = RegimeDetector()
    new_adapter = ParameterAdapter()
    manager.apply_strategy(new_detector, new_adapter, strategy)

    features = {
        "adx_14": 30.0, "volatility_20": 0.15, "bb_width_pct": 3.0,
        "close_to_sma20_pct": 1.5,
    }
    orig_regime, orig_conf = detector.predict(features)
    new_regime, new_conf = new_detector.predict(features)
    assert orig_regime == new_regime
    assert orig_conf == new_conf

    orig_params = adapter.adapt("trending", 0.8, 0.15)
    new_params = new_adapter.adapt("trending", 0.8, 0.15)
    assert orig_params["sl_pips"] == new_params["sl_pips"]
    assert orig_params["tp_pips"] == new_params["tp_pips"]
    assert orig_params["lot_size"] == new_params["lot_size"]


def test_import_raises_on_missing_keys(manager, tmp_path):
    """Test 7: import_strategy() raises ValueError for missing required keys."""
    bad_file = tmp_path / "bad_strategy.json"
    bad_file.write_text(json.dumps({"metadata": {}, "regime_detector": {}}))
    with pytest.raises(ValueError, match="missing required keys"):
        manager.import_strategy(bad_file)


def test_apply_strategy_modifies_instances(manager, detector, adapter, tmp_path):
    """Test 8: apply_strategy() modifies detector and adapter attributes in-place."""
    path = manager.export_strategy(
        RegimeDetector(adx_trend_threshold=40.0),
        ParameterAdapter(max_position_size=0.5),
        filepath=tmp_path / "test_strategy.json",
    )
    strategy = manager.import_strategy(path)
    result = manager.apply_strategy(detector, adapter, strategy)
    assert result is True
    assert detector.adx_trend == 40.0
    assert adapter.max_position_size == 0.5
