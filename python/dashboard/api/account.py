"""GET /api/account — balance, equity, margin, free margin, daily P&L."""
from fastapi import APIRouter, Depends
from ..auth import require_auth
from ..models import AccountInfo
from . import _mt5_cache

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("", response_model=AccountInfo)
async def get_account(user_id: int = Depends(require_auth)):
    """Get current account summary."""
    account = _mt5_cache.get("account")
    if account is None:
        return AccountInfo(balance=0, equity=0, margin=0, free_margin=0, daily_pnl=0)
    return AccountInfo(**account)
