"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from ..config import DASHBOARD_DEV_MODE, FRONTEND_BUILD_DIR
from .db import init_db
from .auth import router as auth_router
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
    yield


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

# Serve frontend static files in production
if not DASHBOARD_DEV_MODE and FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")
