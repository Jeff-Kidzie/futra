import pytest
from unittest.mock import MagicMock, patch
from python.validation.paper_trading import PaperTrader


@pytest.fixture
def mock_engine():
    """Mock AIEngine that returns fixed results from run_once()."""
    engine = MagicMock()
    engine.symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    engine.run_once.return_value = [
        {
            "symbol": "EURUSD", "regime": "trending", "confidence": 0.85,
            "adapted": {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01, "regime": "trending", "confidence": 0.85}
        },
        {
            "symbol": "GBPUSD", "regime": "ranging", "confidence": 0.70,
            "adapted": {"sl_pips": 40, "tp_pips": 70, "lot_size": 0.01, "regime": "ranging", "confidence": 0.70}
        },
        {
            "symbol": "USDJPY", "regime": "quiet", "confidence": 0.65,
            "adapted": {"sl_pips": 35, "tp_pips": 55, "lot_size": 0.01, "regime": "quiet", "confidence": 0.65}
        },
    ]
    return engine


@pytest.fixture
def failing_engine():
    """Mock AIEngine where one symbol fails."""
    engine = MagicMock()
    engine.symbols = ["EURUSD", "GBPUSD"]
    engine.run_once.return_value = [
        {"symbol": "EURUSD", "regime": "trending", "confidence": 0.8,
         "adapted": {"sl_pips": 50, "tp_pips": 100, "lot_size": 0.01, "regime": "trending", "confidence": 0.8}},
        None,  # GBPUSD failed
    ]
    return engine


def test_paper_trader_init_with_engine(mock_engine):
    """Test 1: PaperTrader.__init__() accepts an AIEngine instance."""
    trader = PaperTrader(engine=mock_engine)
    assert trader.engine is mock_engine
    assert trader.symbols == ["EURUSD", "GBPUSD", "USDJPY"]


def test_paper_trader_init_without_engine():
    """Test 2: PaperTrader can be constructed without an engine (engine=None)."""
    trader = PaperTrader(engine=None, symbols=["EURUSD"])
    assert trader.engine is None
    assert trader.symbols == ["EURUSD"]


def test_run_cycle_calls_engine_run_once(mock_engine):
    """Test 3: PaperTrader.run_cycle() calls engine.run_once() and returns results."""
    trader = PaperTrader(engine=mock_engine)
    results = trader.run_cycle()
    mock_engine.run_once.assert_called_once()
    assert len(results) == 3
    assert trader.cycle_count == 1


def test_run_cycle_without_engine_raises():
    """Test 4: run_cycle() raises ValueError when engine is None."""
    trader = PaperTrader(engine=None)
    with pytest.raises(ValueError, match="no AIEngine"):
        trader.run_cycle()


def test_run_cycle_handles_none_results(failing_engine):
    """Test 5: run_cycle() handles engine returning None entries gracefully."""
    trader = PaperTrader(engine=failing_engine)
    results = trader.run_cycle()
    # Results include both successful and None entries
    assert len(results) == 2
    # Cycle should still count
    assert trader.cycle_count == 1
