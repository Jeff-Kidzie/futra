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


# --- Decision Logger Integration Tests (Plan 02-02, Task 3) ---

from python.ai.decision_logger import DecisionLogger


def test_engine_logs_decision_when_logger_provided():
    """Test 5: Engine calls DecisionLogger.log_decision() with correct params."""
    mock_logger = MagicMock(spec=DecisionLogger)
    detector = RegimeDetector()
    adapter = ParameterAdapter()
    engine = AIEngine(
        symbols=["EURUSD"],
        timeframe="H1",
        regime_detector=detector,
        parameter_adapter=adapter,
        decision_logger=mock_logger,
    )

    mock_df = _mock_df()
    mock_features = _mock_features()

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value=mock_features), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params"):
        engine.evaluate_symbol("EURUSD")

    mock_logger.log_decision.assert_called_once()
    call_kwargs = mock_logger.log_decision.call_args.kwargs
    assert call_kwargs["symbol"] == "EURUSD"
    assert call_kwargs["sl_pips"] > 0
    assert call_kwargs["tp_pips"] > 0
    assert call_kwargs["lot_size"] > 0


def test_engine_passes_features_to_logger():
    """Test 6: Feature snapshot is passed to the decision logger."""
    mock_logger = MagicMock(spec=DecisionLogger)
    engine = AIEngine(symbols=["EURUSD"], decision_logger=mock_logger)

    mock_df = _mock_df()
    mock_features = {"adx_14": 30.0, "volatility_20": 0.15, "atr_14": 25.0}

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value=mock_features), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params"):
        engine.evaluate_symbol("EURUSD")

    call_kwargs = mock_logger.log_decision.call_args.kwargs
    assert call_kwargs["features"] == mock_features


def test_engine_works_without_logger():
    """Test 7: Engine does not crash when decision_logger is None."""
    engine = AIEngine(symbols=["EURUSD"], decision_logger=None)

    mock_df = _mock_df()

    with patch("python.ai.engine.fetch_historical_ohlcv", return_value=mock_df), \
         patch("python.ai.engine.compute_features", return_value={"adx_14": 30.0}), \
         patch("python.ai.engine.ensure_connected"), \
         patch("python.ai.engine.write_symbol_params"):
        result = engine.evaluate_symbol("EURUSD")

    assert result is not None


def test_existing_engine_tests_still_pass():
    """Test 8: Existing engine behavior unchanged — smoke test."""
    engine = AIEngine(symbols=["EURUSD"])
    assert engine.symbols == ["EURUSD"]
    assert engine.timeframe == "H1"
    assert engine.detector is not None
    assert engine.adapter is not None
    assert engine.decision_logger is None
