"""Tests for AI engine orchestration (AIEngine)."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from python.ai.engine import AIEngine
from python.ai.regime_detector import RegimeDetector
from python.ai.parameter_adapter import ParameterAdapter


def _mock_df():
    """Create a 200-row mock OHLCV DataFrame."""
    return pd.DataFrame({
        "open": [1.08] * 200,
        "high": [1.09] * 200,
        "low": [1.07] * 200,
        "close": [1.085] * 200,
        "tick_volume": [1000.0] * 200,
    })


def _mock_features():
    """Create a mock feature dict."""
    return {
        "adx_14": 30.0, "volatility_20": 0.15, "bb_width_pct": 3.0,
        "close_to_sma20_pct": 1.5, "atr_14": 25.0, "rsi_14": 55.0,
        "macd": 0.001, "macd_signal": 0.0008, "sma_20_50_ratio": 1.002,
        "volume_ratio": 1.1,
    }


def test_evaluate_symbol_runs_full_pipeline():
    """Test 1: evaluate_symbol() reads data, passes through features→regime→adapter, writes IPC."""
    detector = RegimeDetector()
    adapter = ParameterAdapter()
    engine = AIEngine(
        symbols=["EURUSD"], timeframe="H1",
        regime_detector=detector, parameter_adapter=adapter,
    )

    mock_df = _mock_df()
    mock_feats = _mock_features()

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value=mock_feats), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params") as mock_write:
        result = engine.evaluate_symbol("EURUSD")

    assert result is not None
    assert result["symbol"] == "EURUSD"
    assert "regime" in result
    assert "confidence" in result
    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args.kwargs
    assert "sl_percent" in call_kwargs
    assert "tp_percent" in call_kwargs
    assert "max_position_size" in call_kwargs
    assert "regime" in call_kwargs
    assert "confidence" in call_kwargs


def test_engine_handles_mt5_error_gracefully():
    """Test 2: MT5Error is caught, logged, does not crash — returns None."""
    from python.mt5_connector import MT5Error

    engine = AIEngine(symbols=["EURUSD"])

    with patch("python.ai.engine.ensure_connected", side_effect=MT5Error("Connection failed")), \
         patch("python.ai.engine.write_symbol_params") as mock_write:
        result = engine.evaluate_symbol("EURUSD")

    assert result is None
    mock_write.assert_not_called()


def test_engine_per_symbol_evaluation():
    """Test 3: Different symbols get different params files."""
    detector = RegimeDetector()
    adapter = ParameterAdapter()
    engine = AIEngine(
        symbols=["EURUSD", "GBPUSD"], timeframe="H1",
        regime_detector=detector, parameter_adapter=adapter,
    )

    mock_df = _mock_df()
    mock_feats = _mock_features()

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value=mock_feats), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params") as mock_write:
        results = engine.run_once()

    assert len(results) == 2
    assert mock_write.call_count == 2
    # Verify different symbols were written
    symbols_written = {call.kwargs["symbol"] for call in mock_write.call_args_list}
    assert symbols_written == {"EURUSD", "GBPUSD"}


def test_engine_writes_ipc_in_correct_format():
    """Test 4: IPC params have exact keys EA expects."""
    detector = RegimeDetector()
    adapter = ParameterAdapter()
    engine = AIEngine(
        symbols=["EURUSD"], timeframe="H1",
        regime_detector=detector, parameter_adapter=adapter,
    )

    mock_df = _mock_df()
    mock_feats = _mock_features()

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value=mock_feats), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params") as mock_write:
        engine.evaluate_symbol("EURUSD")

    call_kwargs = mock_write.call_args.kwargs
    expected_keys = {"symbol", "sl_percent", "tp_percent", "max_position_size", "regime", "confidence"}
    assert expected_keys.issubset(set(call_kwargs.keys())), f"Missing keys: {expected_keys - set(call_kwargs.keys())}"
