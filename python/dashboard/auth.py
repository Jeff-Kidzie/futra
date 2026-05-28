"""Authentication: login/logout, token generation, auth middleware."""
import secrets
import logging
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import APIRouter, Depends, Request, HTTPException
from .db import get_db, init_db
from .models import LoginRequest, LoginResponse
from ..config import SESSION_EXPIRY_HOURS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _ensure_default_admin(db):
    """Create default admin user if no users exist. Returns (created, password)."""
    row = db.execute("SELECT COUNT(*) FROM users").fetchone()
    if row[0] == 0:
        password = secrets.token_hex(8)
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash),
        )
        db.commit()
        logger.warning(
            "Default admin user created: username=admin, password=%s",
            password,
        )
        return True, password
    return False, None


async def require_auth(request: Request, db=Depends(get_db)):
    """FastAPI dependency: validate Bearer token from Authorization header.

    Returns user_id on success. Raises HTTPException(401) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    row = db.execute(
        "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    expires_at = row["expires_at"]
    if expires_at < datetime.now(timezone.utc).isoformat():
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()
        raise HTTPException(status_code=401, detail="Token expired")

    return row["user_id"]


@router.post("/login", response_model=LoginResponse)
async def login(login_req: LoginRequest, db=Depends(get_db)):
    """Authenticate user with username/password. Returns bearer token."""
    row = db.execute(
        "SELECT * FROM users WHERE username = ?", (login_req.username,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(login_req.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_hex(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat()
    db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, row["id"], expires_at),
    )
    db.commit()
    return LoginResponse(token=token, expires_at=expires_at)


@router.post("/logout")
async def logout(request: Request, db=Depends(get_db)):
    """Invalidate the bearer token by removing from sessions table."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()
    return {"status": "ok"}
