"""FastAPI application entry point."""
# RED phase — functional skeleton with auth and positions stubs
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from ..config import DASHBOARD_DEV_MODE
from .auth import router as auth_router
from .api.positions import router as positions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .db import init_db
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
