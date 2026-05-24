"""Tests for data_pipeline.py — historical OHLCV fetch, latest bar, and error handling.

All tests use mock MT5 with sample data (no live MT5 connection needed per D-11).
"""
import pytest
import pandas as pd
from python.data_pipeline import fetch_historical_ohlcv, get_latest_bar
from python.mt5_connector import MT5Error


class TestFetchHistoricalOHLCV:
    """Tests for fetch_historical_ohlcv()."""

    def test_returns_dataframe_with_correct_columns(self, mock_mt5_with_data):
        """fetch_historical_ohlcv returns DataFrame with expected OHLCV columns."""
        result = fetch_historical_ohlcv("EURUSD", "H1", 100)
        assert isinstance(result, pd.DataFrame)
        expected_cols = ["time", "open", "high", "low", "close",
                         "tick_volume", "spread", "real_volume"]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"
        assert len(result) == 100

    def test_unknown_timeframe_raises(self, mock_mt5):
        """fetch_historical_ohlcv raises ValueError for unknown timeframe."""
        with pytest.raises(ValueError, match="Unknown timeframe"):
            fetch_historical_ohlcv("EURUSD", "INVALID", 100)

    def test_none_return_raises_mt5_error(self, mock_mt5):
        """fetch_historical_ohlcv raises MT5Error when copy_rates_from_pos returns None."""
        mock_mt5.copy_rates_from_pos.return_value = None
        mock_mt5.last_error.return_value = (1, "No data")
        with pytest.raises(MT5Error, match="Failed to fetch"):
            fetch_historical_ohlcv("EURUSD", "H1", 100)


class TestGetLatestBar:
    """Tests for get_latest_bar()."""

    def test_returns_series_with_price_fields(self, mock_mt5_with_data):
        """get_latest_bar returns a pd.Series with OHLC fields."""
        result = get_latest_bar("EURUSD", "H1")
        assert isinstance(result, pd.Series)
        for field in ["open", "high", "low", "close"]:
            assert field in result.index, f"Missing field: {field}"

    def test_none_return_returns_none(self, mock_mt5):
        """get_latest_bar returns None when copy_rates_from_pos returns None."""
        mock_mt5.copy_rates_from_pos.return_value = None
        result = get_latest_bar("EURUSD", "H1")
        assert result is None
