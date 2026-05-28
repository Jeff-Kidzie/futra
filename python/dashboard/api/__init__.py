# Futra Dashboard API
# Shared MT5 data cache (updated by background thread, read by API routes)
import asyncio
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_mt5_lock = threading.Lock()
_mt5_cache = {
    "positions": [],
    "account": None,
    "last_update": None,
}

_previous_positions = None
_previous_account = None


def _position_to_dict(pos) -> dict:
    """Convert an MT5 position object to a dictionary."""
    return {
        "ticket": pos.ticket,
        "symbol": pos.symbol,
        "direction": "buy" if pos.type == 0 else "sell",
        "volume": pos.volume,
        "open_price": pos.price_open,
        "current_price": pos.price_current,
        "sl": pos.sl,
        "tp": pos.tp,
        "profit": pos.profit,
        "swap": pos.swap,
        "open_time": str(pos.time) if hasattr(pos, "time") else "",
    }


async def poll_mt5_state():
    """Background task: poll MT5 periodically and update cache."""
    global _previous_positions, _previous_account
    from ..config import DASHBOARD_POLL_INTERVAL
    from ..ws import manager

    while True:
        try:
            import MetaTrader5 as mt5

            with _mt5_lock:
                # Get positions
                try:
                    raw_positions = mt5.positions_get()
                    if raw_positions:
                        current_positions = [_position_to_dict(p) for p in raw_positions]
                    else:
                        current_positions = []
                except Exception:
                    current_positions = []

                # Get account info
                try:
                    account = mt5.account_info()
                    if account:
                        current_account = {
                            "balance": account.balance,
                            "equity": account.equity,
                            "margin": account.margin,
                            "free_margin": account.margin_free,
                            "daily_pnl": 0.0,
                        }
                    else:
                        current_account = None
                except Exception:
                    current_account = None

            _mt5_cache["positions"] = current_positions
            _mt5_cache["account"] = current_account

            # Broadcast if changed
            if current_positions != _previous_positions:
                await manager.broadcast_to_all("positions_update", {"positions": current_positions})
                _previous_positions = current_positions

            if current_account != _previous_account:
                await manager.broadcast_to_all("account_update", current_account)
                _previous_account = current_account

        except Exception as e:
            logger.error("MT5 poll error: %s", e)

        await asyncio.sleep(DASHBOARD_POLL_INTERVAL)


async def heartbeat_task():
    """Send periodic heartbeat and check for dead connections."""
    from ..ws import manager

    while True:
        await asyncio.sleep(30)
        try:
            await manager.heartbeat_check()
        except Exception as e:
            logger.error("Heartbeat error: %s", e)
