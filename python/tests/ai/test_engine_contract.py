"""G5 contract tests: AIEngine default-on DecisionLogger + timeframe propagation.

These tests verify the post-G5 behavior:
- AIEngine() with no args instantiates a real DecisionLogger by default
- AIEngine(enable_decision_log=False) keeps decision_logger=None
- AIEngine(decision_logger=mock) preserves explicit injection
- evaluate_symbol passes self.timeframe through to log_decision

Existing tests in test_engine.py use the old semantics and will be
updated in plan 06 (Wave C).
"""
import pytest
from unittest.mock import MagicMock, patch
from python.ai.engine import AIEngine
from python.ai.decision_logger import DecisionLogger


class TestDefaultOnLogger:
    """AIEngine instantiates DecisionLogger by default (S6 pattern)."""

    def test_default_constructor_creates_decision_logger(self):
        """AIEngine() with no args sets decision_logger to a DecisionLogger instance."""
        engine = AIEngine()
        assert isinstance(engine.decision_logger, DecisionLogger)

    def test_explicit_symbols_still_gets_default_logger(self):
        """AIEngine(symbols=['EURUSD']) still gets a default DecisionLogger."""
        engine = AIEngine(symbols=["EURUSD"])
        assert isinstance(engine.decision_logger, DecisionLogger)

    def test_enable_decision_log_true_default(self):
        """enable_decision_log defaults to True."""
        engine = AIEngine()
        assert isinstance(engine.decision_logger, DecisionLogger)


class TestExplicitDisable:
    """AIEngine(enable_decision_log=False) keeps decision_logger=None."""

    def test_disable_via_kwarg(self):
        """AIEngine(enable_decision_log=False) sets decision_logger to None."""
        engine = AIEngine(enable_decision_log=False)
        assert engine.decision_logger is None

    def test_disable_with_symbols(self):
        """enable_decision_log=False works with other kwargs."""
        engine = AIEngine(symbols=["EURUSD"], enable_decision_log=False)
        assert engine.decision_logger is None


class TestExplicitInjection:
    """AIEngine(decision_logger=mock) preserves explicit injection."""

    def test_explicit_logger_wins(self):
        """Explicit decision_logger argument is preserved."""
        mock_logger = MagicMock()
        engine = AIEngine(decision_logger=mock_logger)
        assert engine.decision_logger is mock_logger

    def test_explicit_logger_with_enable_false(self):
        """Explicit logger wins even when enable_decision_log=False."""
        mock_logger = MagicMock()
        engine = AIEngine(decision_logger=mock_logger, enable_decision_log=False)
        assert engine.decision_logger is mock_logger

    def test_explicit_none_with_enable_true(self):
        """Explicit None + enable_decision_log=True creates default logger."""
        engine = AIEngine(decision_logger=None, enable_decision_log=True)
        assert isinstance(engine.decision_logger, DecisionLogger)


class TestTimeframePropagation:
    """evaluate_symbol passes self.timeframe through to log_decision."""

    def test_evaluate_symbol_passes_timeframe(self):
        """When evaluate_symbol logs a decision, it passes timeframe=self.timeframe."""
        mock_logger = MagicMock()
        engine = AIEngine(
            symbols=["EURUSD"],
            timeframe="H4",
            decision_logger=mock_logger,
        )

        # Mock the entire evaluate_symbol pipeline to isolate the logging call
        with patch.object(engine, "detector") as mock_detector, \
             patch.object(engine, "adapter") as mock_adapter, \
             patch("python.ai.engine.ensure_connected"), \
             patch("python.ai.engine.fetch_historical_ohlcv") as mock_fetch, \
             patch("python.ai.engine.compute_features") as mock_features, \
             patch("python.ai.engine.write_symbol_params"):

            import pandas as pd
            mock_fetch.return_value = pd.DataFrame()
            mock_features.return_value = {
                "volatility_20": 0.15,
                "atr_14": 25.0,
                "adx_14": 30.0,
                "rsi_14": 55.0,
                "bb_width_pct": 3.0,
                "close_to_sma20_pct": 1.5,
            }
            mock_detector.predict.return_value = ("trending", 0.85)
            mock_adapter.adapt.return_value = {
                "sl_pips": 50.0,
                "tp_pips": 100.0,
                "lot_size": 0.10,
            }
            mock_adapter.to_ipc_params.return_value = {
                "sl_percent": 0.005,
                "tp_percent": 0.01,
                "max_position_size": 0.10,
                "regime": "trending",
                "confidence": 0.85,
            }

            engine.evaluate_symbol("EURUSD")

            # Verify log_decision was called with timeframe=self.timeframe
            mock_logger.log_decision.assert_called_once()
            call_kwargs = mock_logger.log_decision.call_args
            assert call_kwargs.kwargs.get("timeframe") == "H4" or \
                   (call_kwargs.args and "H4" in call_kwargs.args), \
                   f"timeframe='H4' not found in log_decision call: {call_kwargs}"


class TestSourceCodeGuards:
    """Mechanical assertions on source code."""

    def test_enable_decision_log_kwarg_exists(self):
        """Source code contains enable_decision_log: bool = True."""
        src = open("python/ai/engine.py").read()
        assert "enable_decision_log: bool = True" in src

    def test_default_on_instantiation_exists(self):
        """Source code contains DecisionLogger() default-on instantiation."""
        src = open("python/ai/engine.py").read()
        assert "DecisionLogger()" in src

    def test_timeframe_propagation_exists(self):
        """Source code contains timeframe=self.timeframe in log_decision call."""
        src = open("python/ai/engine.py").read()
        assert "timeframe=self.timeframe" in src
