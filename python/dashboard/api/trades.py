"""GET /api/trades — paginated trade history from trade_log.jsonl."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from ..auth import require_auth
from ..models import Trade
from ...config import IPC_DIR

logger = logging.getLogger(__name__)

TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"
router = APIRouter(prefix="/api/trades", tags=["trades"])


def read_trades(limit: int = 50, offset: int = 0) -> list[dict]:
    """Read trade history from JSONL log. Matches open/close by ticket."""
    if not TRADE_LOG_PATH.exists():
        return []

    open_trades: dict[int, dict] = {}
    closed_trades: list[dict] = []

    try:
        with open(TRADE_LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Malformed JSON line in trade_log.jsonl, skipping")
                    continue

                if entry.get("event") == "trade_open":
                    open_trades[entry["ticket"]] = entry
                elif entry.get("event") == "trade_close":
                    ticket = entry["ticket"]
                    if ticket in open_trades:
                        op = open_trades[ticket]
                        # Compute duration
                        try:
                            from datetime import datetime
                            open_dt = datetime.fromisoformat(op["timestamp"].replace("Z", "+00:00"))
                            close_dt = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                            delta = close_dt - open_dt
                            hours = delta.total_seconds() // 3600
                            minutes = (delta.total_seconds() % 3600) // 60
                            duration = f"{int(hours)}h {int(minutes)}m"
                        except Exception:
                            duration = "unknown"

                        closed_trades.append({
                            "ticket": ticket,
                            "symbol": op["symbol"],
                            "direction": op["direction"],
                            "entry_price": op["price"],
                            "exit_price": entry.get("close_price", 0),
                            "profit": entry.get("profit", 0),
                            "open_time": op["timestamp"],
                            "close_time": entry["timestamp"],
                            "duration": duration,
                            "regime": None,
                        })
    except Exception as e:
        logger.error("Error reading trade log: %s", e)
        return []

    # Sort by close_time descending (most recent first)
    closed_trades.sort(key=lambda t: t["close_time"], reverse=True)

    # Apply pagination
    return closed_trades[offset:offset + limit]


@router.get("", response_model=list[Trade])
async def get_trades(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(require_auth),
):
    """Get paginated trade history."""
    trades = read_trades(limit=limit, offset=offset)
    return [Trade(**t) for t in trades]
