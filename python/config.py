"""Central configuration for Futra trading system.

All values load from environment variables with sensible defaults.
Per T-01-07: MT5 credentials stored in environment variables, never hardcoded.
"""
import os
import secrets
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


# --- Validation Configuration ---

# Backtesting
DEFAULT_INITIAL_EQUITY = float(os.getenv("FUTRA_BACKTEST_EQUITY", "10000.0"))
DEFAULT_BACKTEST_TIMEFRAME = os.getenv("FUTRA_BACKTEST_TIMEFRAME", "H1")

# Costs — per-symbol spread in pips
DEFAULT_SPREAD_PIPS = {
    "EURUSD": 1.0, "GBPUSD": 1.5, "USDJPY": 1.5,
    "USDCHF": 1.5, "AUDUSD": 1.5, "NZDUSD": 2.0,
    "USDCAD": 1.5, "EURGBP": 2.0, "EURJPY": 2.0,
    "GBPJPY": 3.0, "XAUUSD": 20.0,
}

# Commission per lot in account currency ($7 per lot round-turn = typical retail)
COMMISSION_PER_LOT = float(os.getenv("FUTRA_COMMISSION_PER_LOT", "7.0"))

# Slippage in pips
SLIPPAGE_PIPS_MAJORS = float(os.getenv("FUTRA_SLIPPAGE_MAJORS", "0.5"))
SLIPPAGE_PIPS_MINORS = float(os.getenv("FUTRA_SLIPPAGE_MINORS", "1.0"))

# Walk-forward
WF_IN_SAMPLE_YEARS = int(os.getenv("FUTRA_WF_INSAMPLE_YEARS", "2"))
WF_OUT_OF_SAMPLE_MONTHS = int(os.getenv("FUTRA_WF_OOS_MONTHS", "6"))
WF_MIN_OOS_TRADES = int(os.getenv("FUTRA_WF_MIN_TRADES", "10"))

# Monte Carlo
MC_ITERATIONS = int(os.getenv("FUTRA_MC_ITERATIONS", "2000"))
MC_CONFIDENCE_LEVEL = float(os.getenv("FUTRA_MC_CONFIDENCE", "0.95"))

# Paper trading
PAPER_TRADING_INTERVAL_SECONDS = int(os.getenv("FUTRA_PAPER_INTERVAL", "3600"))
MT5_DEMO_LOGIN = int(os.getenv("MT5_DEMO_LOGIN", "0"))
MT5_DEMO_PASSWORD = os.getenv("MT5_DEMO_PASSWORD", "")
MT5_DEMO_SERVER = os.getenv("MT5_DEMO_SERVER", "")

# Pip size per symbol (difference between 1 pip in price units)
# Standard: Forex pairs quoted to 4 decimal places → pip = 0.0001
# JPY pairs quoted to 2 decimal places → pip = 0.01
# Gold (XAUUSD) → pip = 0.10
PIP_SIZE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01,
    "USDCHF": 0.0001, "AUDUSD": 0.0001, "NZDUSD": 0.0001,
    "USDCAD": 0.0001, "EURGBP": 0.0001, "EURJPY": 0.01,
    "GBPJPY": 0.01, "XAUUSD": 0.10,
}

# --- Dashboard Configuration ---
DASHBOARD_DB_PATH = Path(os.getenv("FUTRA_DASHBOARD_DB", "dashboard.db"))
DASHBOARD_DEV_MODE = os.getenv("FUTRA_DASHBOARD_DEV", "false").lower() == "true"
FRONTEND_BUILD_DIR = Path(os.getenv("FUTRA_FRONTEND_DIR", "frontend/build"))
SESSION_EXPIRY_HOURS = int(os.getenv("FUTRA_SESSION_EXPIRY_HOURS", "24"))
DASHBOARD_POLL_INTERVAL = float(os.getenv("FUTRA_DASHBOARD_POLL", "1.0"))
DRAWDOWN_ALERT_THRESHOLD = float(os.getenv("FUTRA_DRAWDOWN_ALERT_PCT", "10.0"))
DAILY_LOSS_ALERT_THRESHOLD = float(os.getenv("FUTRA_DAILY_LOSS_ALERT", "500.0"))
# AI log directory (Phase 2) — may not exist until Phase 2 is executed
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", "logs/ai"))
STRATEGY_CONFIG_DIR = Path(os.getenv("FUTRA_STRATEGY_CONFIG_DIR", "configs/strategies"))


# --- Production Deployment Configuration ---

# Caddy/HTTPS domain (for production reverse proxy)
DASHBOARD_DOMAIN = os.getenv("FUTRA_DASHBOARD_DOMAIN", "localhost")

# Initial balance for equity curve computation (can be overridden per account)
FUTRA_INITIAL_BALANCE = float(os.getenv("FUTRA_INITIAL_BALANCE", "10000.0"))

# Session secret for token generation (override in production!)
# If not set, a random secret is generated on startup (sessions invalidate on restart)
SESSION_SECRET = os.getenv("FUTRA_SESSION_SECRET", secrets.token_hex(32))
