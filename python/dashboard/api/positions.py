"""GET /api/positions — current open positions."""
from fastapi import APIRouter, Depends
from ..auth import require_auth
from ..models import Position
from . import _mt5_cache

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=list[Position])
async def get_positions(user_id: int = Depends(require_auth)):
    """Get current open positions with P&L."""
    positions = _mt5_cache.get("positions", [])
    return [Position(**p) for p in positions]
