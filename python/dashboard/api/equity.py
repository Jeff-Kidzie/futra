"""GET /api/equity-curve — computed equity time series for charting."""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from ..auth import require_auth
from ..models import EquityPoint
from ...config import IPC_DIR

logger = logging.getLogger(__name__)

TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"
router = APIRouter(prefix="/api/equity-curve", tags=["equity"])


def compute_equity_curve(
    trade_log_path: Path | None = None,
    initial_balance: float = 10000.0,
    days: int = 30,
) -> list[dict]:
    """Replay trades from JSONL log to build daily equity curve."""
    path = trade_log_path or TRADE_LOG_PATH
    if not path.exists():
        today = datetime.now(timezone.utc).date().isoformat()
        return [{"time": today, "value": initial_balance}]

    # Collect trade_close events
    closes: list[dict] = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("event") == "trade_close":
                    closes.append(entry)
    except Exception as e:
        logger.error("Error reading trade log for equity: %s", e)
        today = datetime.now(timezone.utc).date().isoformat()
        return [{"time": today, "value": initial_balance}]

    if not closes:
        today = datetime.now(timezone.utc).date().isoformat()
        return [{"time": today, "value": initial_balance}]

    # Aggregate daily P&L from trade_close events
    equity_map: dict[str, float] = {}
    for close_entry in closes:
        try:
            ts = close_entry["timestamp"].replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            day_key = dt.date().isoformat()
            profit = close_entry.get("profit", 0)
            equity_map[day_key] = equity_map.get(day_key, 0) + profit
        except Exception:
            continue

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days)

    if not equity_map:
        return [{"time": today.isoformat(), "value": initial_balance}]

    # Walk from the earliest trade day forward, accumulating running equity from
    # initial_balance. This ensures the window's first point reflects all prior
    # P&L (bug fix: previously the curve restarted from initial_balance at
    # start_date, ignoring trades older than the window).
    first_trade_day = datetime.fromisoformat(min(equity_map.keys())).date()
    walk_start = min(first_trade_day, start_date)

    equity_value = initial_balance
    points: list[dict] = []
    current_date = walk_start
    while current_date <= today:
        day_str = current_date.isoformat()
        if day_str in equity_map:
            equity_value += equity_map[day_str]
        if current_date >= start_date:
            points.append({"time": day_str, "value": round(equity_value, 2)})
        current_date += timedelta(days=1)

    if not points:
        points = [{"time": today.isoformat(), "value": round(equity_value, 2)}]

    return points


@router.get("", response_model=list[EquityPoint])
async def get_equity_curve(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(require_auth),
):
    """Get equity curve data points for the specified number of days."""
    curve = compute_equity_curve(days=days)
    return [EquityPoint(**p) for p in curve]
