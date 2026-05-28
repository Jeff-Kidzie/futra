"""GET /api/positions — current open positions."""
# RED phase stub — returns empty list (tests will run but auth tests may fail)
from fastapi import APIRouter, Depends
from ..auth import require_auth
from ..models import Position

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=list[Position])
async def get_positions(user_id: int = Depends(require_auth)):
    """Get current open positions."""
    return []
