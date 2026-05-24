"""Mock MT5 infrastructure per D-11 — mock MT5 data files for fully local testing."""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd


@pytest.fixture
def temp_ipc_dir(tmp_path):
    """Temporary IPC directory for tests."""
    ipc_dir = tmp_path / "Futra"
    ipc_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path  # Return base path, IPC_DIR is `base / "Futra"`


@pytest.fixture
def mock_mt5():
    """Mock MetaTrader5 package with realistic responses."""
    with patch("python.mt5_connector.mt5") as mock:
        mock.initialize.return_value = True
        mock.shutdown.return_value = None
        mock.last_error.return_value = (0, "Success")
        mock.terminal_info.return_value = MagicMock(
            community_account=True,
            community_connection=True,
            connected=True,
            dlls_allowed=False,
            trade_allowed=True,
            tradeapi_disabled=False,
        )

        # Mock account info
        mock.account_info.return_value = MagicMock(
            login=12345,
            balance=10000.0,
            equity=10050.0,
            margin=500.0,
            margin_free=9550.0,
            margin_level=2010.0,
            leverage=100,
            currency="USD",
        )

        # Mock symbol info
        def make_symbol_info(symbol="EURUSD"):
            return MagicMock(
                name=symbol,
                spread=10,
                digits=5,
                trade_mode=4,
                point=0.00001,
                ask=1.08500,
                bid=1.08490,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                filling_mode=3,
            )
        mock.symbol_info.side_effect = make_symbol_info

        yield mock


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data as a pandas DataFrame matching mt5.copy_rates_from_pos output."""
    dates = pd.date_range("2026-01-01", periods=100, freq="1h")
    np.random.seed(42)
    close = 1.0800 + np.cumsum(np.random.randn(100) * 0.001)
    data = pd.DataFrame({
        "time": dates,
        "open": close - np.random.rand(100) * 0.0005,
        "high": close + np.random.rand(100) * 0.001,
        "low": close - np.random.rand(100) * 0.001,
        "close": close,
        "tick_volume": np.random.randint(100, 1000, 100),
        "spread": np.full(100, 10),
        "real_volume": np.zeros(100),
    })
    return data


@pytest.fixture
def mock_mt5_with_data(mock_mt5, sample_ohlcv_data):
    """Mock MT5 that returns sample OHLCV data from copy_rates_from_pos()."""
    def copy_rates_from_pos(symbol, timeframe, start_pos, count):
        return sample_ohlcv_data.iloc[start_pos:start_pos + count].to_records(index=False)
    mock_mt5.copy_rates_from_pos.side_effect = copy_rates_from_pos
    return mock_mt5
