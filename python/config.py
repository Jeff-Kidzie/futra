"""Central configuration for Futra trading system.

All values load from environment variables with sensible defaults.
Per T-01-07: MT5 credentials stored in environment variables, never hardcoded.
"""
import os
from pathlib import Path


# MT5 Connection
MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))  # 0 = use saved credentials
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# IPC Directory (local dev default, overridden in production)
IPC_DIR = Path(os.getenv("FUTRA_IPC_DIR", str(Path(__file__).parent.parent / "ipc")))

# Default trading symbols per D-08 (each symbol gets its own params file)
DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]

# Timeframes for OHLCV data per DATA-03
TIMEFRAMES = {
    "M15": 15 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}

# Polling intervals per timeframe (seconds) per D-07
POLLING_INTERVALS = {
    "M15": 900,    # 15 minutes
    "H1": 3600,    # 1 hour
    "H4": 14400,   # 4 hours
    "D1": 86400,   # 24 hours
}

# Connection resilience per DATA-10
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5.0

# Bars to fetch for historical data
DEFAULT_BAR_COUNT = 1000

# AI Engine configuration
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", str(Path(__file__).parent / "ai" / "decisions")))
AI_STRATEGY_DIR = Path(os.getenv("FUTRA_AI_STRATEGY_DIR", str(Path(__file__).parent / "ai" / "strategies")))
AI_DEFAULT_TIMEFRAME = os.getenv("FUTRA_AI_TIMEFRAME", "H1")
AI_DEFAULT_EQUITY = float(os.getenv("FUTRA_AI_EQUITY", "10000.0"))
