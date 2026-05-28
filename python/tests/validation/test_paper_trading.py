"""Tests for paper trading mode — AI engine scheduler for demo MT5.

Per BACK-05: Forward-testing without real capital.
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_engine():
    """Mock AIEngine that returns fixed results from run_once()."""
    engine = MagicMock()
    engine.symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    engine.run_once.return_value = [
        {
            "symbol": "EURUSD", "regime": "trending", "confidence": 0.85,
            "adapted": {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01,
                       "regime": "trending", "confidence": 0.85}
        },
        {
            "symbol": "GBPUSD", "regime": "ranging", "confidence": 0.70,
            "adapted": {"sl_pips": 40, "tp_pips": 70, "lot_size": 0.01,
                       "regime": "ranging", "confidence": 0.70}
        },
        {
            "symbol": "USDJPY", "regime": "quiet", "confidence": 0.65,
            "adapted": {"sl_pips": 35, "tp_pips": 55, "lot_size": 0.01,
                       "regime": "quiet", "confidence": 0.65}
        },
    ]
    return engine


@pytest.fixture
def empty_engine():
    """Mock AIEngine that returns empty list from run_once()."""
    engine = MagicMock()
    engine.symbols = ["EURUSD", "GBPUSD"]
    engine.run_once.return_value = []
    return engine


@pytest.fixture
def failing_engine():
    """Mock AIEngine where some symbols return None."""
    engine = MagicMock()
    engine.symbols = ["EURUSD", "GBPUSD"]
    engine.run_once.return_value = [
        {"symbol": "EURUSD", "regime": "trending", "confidence": 0.8,
         "adapted": {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01,
                    "regime": "trending", "confidence": 0.8}},
        None,  # GBPUSD failed
    ]
    return engine


# --- Test 1: PaperTrader init with engine — uses engine.symbols ---
def test_paper_trader_init_with_engine(mock_engine):
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=mock_engine)
    assert trader.engine is mock_engine
    assert trader.symbols == ["EURUSD", "GBPUSD", "USDJPY"]


# --- Test 2: PaperTrader init without engine — uses provided symbols ---
def test_paper_trader_init_without_engine():
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=None, symbols=["EURUSD"])
    assert trader.engine is None
    assert trader.symbols == ["EURUSD"]


# --- Test 3: run_cycle() calls engine.run_once() exactly once ---
def test_run_cycle_calls_engine_run_once(mock_engine):
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=mock_engine)
    results = trader.run_cycle()
    mock_engine.run_once.assert_called_once()
    assert len(results) == 3
    assert trader.cycle_count == 1


# --- Test 4: run_cycle() without engine raises ValueError ---
def test_run_cycle_without_engine_raises():
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=None)
    with pytest.raises(ValueError, match="no AIEngine"):
        trader.run_cycle()


# --- Test 5: run_cycle() handles engine returning empty list ---
def test_run_cycle_empty_engine_result(empty_engine):
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=empty_engine)
    results = trader.run_cycle()
    assert results == []
    assert trader.cycle_count == 1


# --- Test 6: run_cycle() handles None entries in results gracefully ---
def test_run_cycle_handles_none_results(failing_engine):
    from python.validation.paper_trading import PaperTrader
    trader = PaperTrader(engine=failing_engine)
    results = trader.run_cycle()
    # Results include both successful and None entries
    assert len(results) == 2
    # Cycle should still count even with None entries
    assert trader.cycle_count == 1
