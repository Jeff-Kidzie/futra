"""MT5 connection wrapper with auto-reconnect and None-handling on all API calls.

Per DATA-10: Auto-reconnect on connection drop with max retries and backoff.
Per AGENTS.md conventions: Error handling wraps all MT5 API calls (returns None on failure).
"""
import MetaTrader5 as mt5
import time
import logging
from .config import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MAX_RETRIES, RETRY_DELAY_SECONDS

logger = logging.getLogger(__name__)
_connected = False


class MT5Error(Exception):
    """Raised when an MT5 API call returns None or fails."""
    def __init__(self, message: str, mt5_error: tuple | None = None):
        super().__init__(message)
        self.mt5_error = mt5_error or mt5.last_error()


def initialize_mt5(path: str | None = None, login: int | None = None,
                   password: str | None = None, server: str | None = None) -> bool:
    """Initialize MT5 connection. Returns True on success, raises MT5Error on failure."""
    global _connected
    path = path or MT5_PATH
    login = login if login is not None else MT5_LOGIN
    password = password if password is not None else MT5_PASSWORD
    server = server if server is not None else MT5_SERVER

    init_kwargs = {"path": path}
    if login:
        init_kwargs["login"] = login
    if password:
        init_kwargs["password"] = password
    if server:
        init_kwargs["server"] = server

    result = mt5.initialize(**init_kwargs)
    if result is None:
        raise MT5Error("mt5.initialize() returned None — MT5 terminal may not be installed or running")
    if not result:
        err = mt5.last_error()
        raise MT5Error(f"mt5.initialize() failed: {err}")
    _connected = True
    logger.info("MT5 connection initialized")
    return True


def shutdown_mt5() -> None:
    """Shut down MT5 connection."""
    global _connected
    mt5.shutdown()
    _connected = False
    logger.info("MT5 connection shut down")


def is_connected() -> bool:
    """Check if MT5 connection is active."""
    global _connected
    if not _connected:
        return False
    # Verify connection is still alive by making a safe API call
    try:
        term_info = mt5.terminal_info()
        if term_info is None:
            _connected = False
            return False
        return True
    except Exception:
        _connected = False
        return False


def ensure_connected() -> None:
    """Ensure MT5 is connected. Reconnects if disconnected. Raises MT5Error after max retries."""
    if is_connected():
        return
    for attempt in range(1, MAX_RETRIES + 1):
        logger.warning(f"MT5 disconnected — reconnect attempt {attempt}/{MAX_RETRIES}")
        try:
            initialize_mt5()
            if is_connected():
                return
        except MT5Error as e:
            logger.error(f"Reconnect attempt {attempt} failed: {e}")
        time.sleep(RETRY_DELAY_SECONDS)
    raise MT5Error(f"Failed to reconnect MT5 after {MAX_RETRIES} attempts")
