"""FastAPI application entry point."""
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from ..config import DASHBOARD_DEV_MODE, FRONTEND_BUILD_DIR
from .db import init_db, get_db
from .auth import router as auth_router
from .ws import manager
from .notification import AlertMonitor
from .api.positions import router as positions_router
from .api.account import router as account_router
from .api.trades import router as trades_router
from .api.decisions import router as decisions_router
from .api.equity import router as equity_router
from .api.drawdown import router as drawdown_router
from .api.alerts import router as alerts_router
from .api.strategy import router as strategy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Start background tasks
    from .api import poll_mt5_state, heartbeat_task
    poll_task = asyncio.create_task(poll_mt5_state())
    hb_task = asyncio.create_task(heartbeat_task())
    alert_monitor = AlertMonitor()
    alert_task = asyncio.create_task(alert_monitor.run())
    yield
    # Cleanup
    for task in [poll_task, hb_task, alert_task]:
        task.cancel()
    await asyncio.gather(poll_task, hb_task, alert_task, return_exceptions=True)


app = FastAPI(title="Futra Dashboard", lifespan=lifespan)

if DASHBOARD_DEV_MODE:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(positions_router)
app.include_router(account_router)
app.include_router(trades_router)
app.include_router(decisions_router)
app.include_router(equity_router)
app.include_router(drawdown_router)
app.include_router(alerts_router)
app.include_router(strategy_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint with token auth via query parameter."""
    db = get_db()
    try:
        row = db.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        expires_at = row["expires_at"]
        if expires_at < datetime.now(timezone.utc).isoformat():
            db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            db.commit()
            await websocket.close(code=4001, reason="Unauthorized")
            return
        user_id = row["user_id"]
    finally:
        db.close()

    await manager.connect(websocket, user_id)
    try:
        await manager.handle_client_messages(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Serve frontend static files in production
if not DASHBOARD_DEV_MODE and FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")
