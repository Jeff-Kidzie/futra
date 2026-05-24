"""Tests for MT5 connector — connection lifecycle, auto-reconnect, and None-handling.

All tests use mock MT5 (no live MetaTrader5 package needed per D-11).
"""
import pytest
from python.mt5_connector import (
    initialize_mt5, shutdown_mt5, is_connected, ensure_connected, MT5Error
)


class TestInitialize:
    """Tests for initialize_mt5()."""

    def test_initialize_success(self, mock_mt5):
        """initialize_mt5() calls mt5.initialize with correct kwargs and returns True."""
        result = initialize_mt5()
        assert result is True
        assert is_connected() is True
        mock_mt5.initialize.assert_called_once()
        # Verify path is in kwargs
        assert "path" in mock_mt5.initialize.call_args.kwargs

    def test_initialize_failure(self, mock_mt5):
        """initialize_mt5() raises MT5Error when mt5.initialize returns False."""
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (1, "Init failed")
        with pytest.raises(MT5Error, match="Init failed"):
            initialize_mt5()

    def test_initialize_returns_none(self, mock_mt5):
        """initialize_mt5() raises MT5Error when mt5.initialize returns None."""
        mock_mt5.initialize.return_value = None
        with pytest.raises(MT5Error, match="returned None"):
            initialize_mt5()


class TestShutdown:
    """Tests for shutdown_mt5()."""

    def test_shutdown(self, mock_mt5):
        """shutdown_mt5() calls mt5.shutdown and sets connected flag to False."""
        initialize_mt5()
        assert is_connected() is True
        shutdown_mt5()
        assert is_connected() is False
        mock_mt5.shutdown.assert_called_once()

    def test_is_connected_when_terminal_info_none(self, mock_mt5):
        """is_connected() returns False when terminal_info returns None."""
        initialize_mt5()
        assert is_connected() is True
        # Now simulate disconnection
        mock_mt5.terminal_info.return_value = None
        assert is_connected() is False


class TestEnsureConnected:
    """Tests for ensure_connected() — auto-reconnect logic."""

    def test_ensure_connected_already_connected(self, mock_mt5):
        """ensure_connected() does not re-initialize when already connected."""
        initialize_mt5()
        call_count_before = mock_mt5.initialize.call_count
        ensure_connected()
        assert mock_mt5.initialize.call_count == call_count_before  # No re-init

    def test_ensure_connected_reconnects(self, mock_mt5):
        """ensure_connected() reconnects when mt5 is disconnected."""
        initialize_mt5()
        initial_calls = mock_mt5.initialize.call_count
        # Use side_effect: first return None (simulates disconnect),
        # then return valid terminal_info (simulates successful reconnect)
        terminal_responses = [None, mock_mt5.terminal_info.return_value]
        mock_mt5.terminal_info.side_effect = terminal_responses
        ensure_connected()
        # Should have called initialize at least once more (reconnect)
        assert mock_mt5.initialize.call_count > initial_calls

    def test_ensure_connected_raises_after_max_retries(self, mock_mt5):
        """ensure_connected() raises MT5Error after exhausting max retries."""
        mock_mt5.initialize.return_value = False
        mock_mt5.terminal_info.return_value = None
        mock_mt5.last_error.return_value = (1, "Failed")
        with pytest.raises(MT5Error, match="Failed to reconnect"):
            ensure_connected()


class TestConfig:
    """Tests for config.py defaults."""

    def test_config_defaults(self):
        """config.py loads expected defaults."""
        from python.config import (
            DEFAULT_SYMBOLS, TIMEFRAMES, POLLING_INTERVALS,
            MAX_RETRIES, RETRY_DELAY_SECONDS, IPC_DIR, MT5_PATH
        )
        assert DEFAULT_SYMBOLS == ["EURUSD", "GBPUSD", "USDJPY"]
        assert "M15" in TIMEFRAMES
        assert "H1" in TIMEFRAMES
        assert "H4" in TIMEFRAMES
        assert "D1" in TIMEFRAMES
        assert "M15" in POLLING_INTERVALS
        assert "H1" in POLLING_INTERVALS
        assert "H4" in POLLING_INTERVALS
        assert "D1" in POLLING_INTERVALS
        assert MAX_RETRIES == 3
        assert RETRY_DELAY_SECONDS == 5.0
        assert IPC_DIR is not None
        assert MT5_PATH is not None
