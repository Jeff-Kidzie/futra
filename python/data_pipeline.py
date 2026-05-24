"""Data pipeline: historical OHLCV fetch and real-time polling across symbols/timeframes.

Per DATA-01: Connects to MT5 for historical data.
Per DATA-02: Supports multiple symbols.
Per DATA-03: Supports multiple timeframes (M15, H1, H4, D1).
Per D-07: Periodic polling with configurable intervals.
"""
import MetaTrader5 as mt5
import pandas as pd
import logging
import time
from typing import Callable
from .mt5_connector import ensure_connected, MT5Error
from .config import TIMEFRAMES, DEFAULT_SYMBOLS, DEFAULT_BAR_COUNT

logger = logging.getLogger(__name__)

# Map timeframe strings to MT5 constants
MT5_TIMEFRAMES = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def fetch_historical_ohlcv(symbol: str, timeframe: str,
                            bar_count: int = DEFAULT_BAR_COUNT) -> pd.DataFrame:
    """Fetch historical OHLCV bars from MT5. Per DATA-01 and DATA-02."""
    ensure_connected()
    tf = MT5_TIMEFRAMES.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}. Valid: {list(MT5_TIMEFRAMES.keys())}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bar_count)
    if rates is None:
        err = mt5.last_error()
        raise MT5Error(
            f"Failed to fetch {bar_count} {timeframe} bars for {symbol}: {err}")
    if len(rates) == 0:
        logger.warning(f"No data returned for {symbol} {timeframe}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def get_latest_bar(symbol: str, timeframe: str) -> pd.Series | None:
    """Get the most recent completed bar for a symbol/timeframe."""
    ensure_connected()
    tf = MT5_TIMEFRAMES.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 1)
    if rates is None or len(rates) == 0:
        return None
    # Use DataFrame for consistent field-name handling across pandas versions
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    series = df.iloc[0]
    return series


def start_real_time_polling(symbols: list[str] | None = None,
                             timeframe: str = "M15",
                             callback: Callable[[str, str, pd.DataFrame], None] | None = None,
                             interval_seconds: int | None = None) -> None:
    """Blocking polling loop that fetches latest data and calls callback per D-07.
    Returns on KeyboardInterrupt. For production use, wrap in a thread."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS
    if interval_seconds is None:
        from .config import POLLING_INTERVALS
        interval_seconds = POLLING_INTERVALS.get(timeframe, 900)

    logger.info(f"Starting real-time polling: {symbols} @ {timeframe} every {interval_seconds}s")
    while True:
        try:
            ensure_connected()
            for symbol in symbols:
                try:
                    data = fetch_historical_ohlcv(symbol, timeframe, bar_count=10)
                    if callback:
                        callback(symbol, timeframe, data)
                except MT5Error as e:
                    logger.error(f"Poll error for {symbol}: {e}")
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
            break
        except MT5Error as e:
            logger.error(f"MT5 connection lost during polling: {e}. Retrying in {interval_seconds}s...")
            time.sleep(interval_seconds)
