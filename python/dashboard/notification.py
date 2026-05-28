"""Background alert monitor for threshold breach detection."""
import asyncio
import time
import logging
from datetime import datetime, timezone
from .db import get_db
from .ws import manager
from .api import _mt5_lock, _mt5_cache
from ..config import DRAWDOWN_ALERT_THRESHOLD, DAILY_LOSS_ALERT_THRESHOLD

# Import MT5 at module level for testability (mocked in tests)
try:
    import MetaTrader5 as _mt5_module
except ImportError:
    _mt5_module = None

logger = logging.getLogger(__name__)


class AlertMonitor:
    """Monitors trading state and creates alerts when thresholds are breached."""

    def __init__(self):
        self._last_alerts: dict[tuple, float] = {}  # {(type, message_hash): last_alert_time}

    async def run(self):
        """Main loop: check all alert conditions every 10 seconds."""
        while True:
            try:
                self.check_mt5_connection()
                self.check_drawdown()
            except Exception as e:
                logger.error("Alert monitor error: %s", e)
            await asyncio.sleep(10)

    def _create_alert(self, alert_type: str, message: str, severity: str):
        """Persist alert to DB and broadcast via WebSocket. Deduplicate."""
        dedup_key = (alert_type, hash(message))
        now = time.time()
        # Don't repeat same alert within 60 seconds
        if dedup_key in self._last_alerts and now - self._last_alerts[dedup_key] < 60:
            return
        self._last_alerts[dedup_key] = now

        db = get_db()
        try:
            cursor = db.execute(
                "INSERT INTO alerts (type, message, severity) VALUES (?, ?, ?)",
                (alert_type, message, severity),
            )
            alert_id = cursor.lastrowid
            db.commit()
            alert = {
                "id": alert_id,
                "type": alert_type,
                "message": message,
                "severity": severity,
                "acknowledged": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            # Broadcast via WebSocket (fire-and-forget to avoid blocking)
            try:
                asyncio.create_task(manager.broadcast_to_all("alert", alert))
            except RuntimeError:
                # No running event loop (test context)
                pass
        finally:
            db.close()

    def check_mt5_connection(self):
        """Check if MT5 terminal is running."""
        if _mt5_module is None:
            return
        try:
            info = _mt5_module.terminal_info()
            if info is None:
                self._create_alert("connection_lost", "MT5 terminal disconnected", "critical")
        except Exception:
            self._create_alert("connection_lost", "MT5 connection check failed", "critical")

    def check_drawdown(self):
        """Check if current drawdown exceeds threshold."""
        account = _mt5_cache.get("account")
        if account is None:
            return
        balance = account.get("balance", 0)
        equity = account.get("equity", 0)
        if balance > 0:
            drawdown_pct = ((balance - equity) / balance) * 100
            if drawdown_pct >= DRAWDOWN_ALERT_THRESHOLD:
                self._create_alert(
                    "drawdown",
                    f"Drawdown alert: {drawdown_pct:.1f}% (threshold: {DRAWDOWN_ALERT_THRESHOLD}%)",
                    "critical",
                )
