"""GET /api/drawdown — computed drawdown time series."""
from fastapi import APIRouter, Depends, Query
from ..auth import require_auth
from ..models import DrawdownPoint
from .equity import compute_equity_curve

router = APIRouter(prefix="/api/drawdown", tags=["drawdown"])


def compute_drawdown_curve(equity_curve: list[dict]) -> list[dict]:
    """Compute drawdown from equity curve: (peak - current) / peak * 100."""
    if not equity_curve:
        return []

    peak = equity_curve[0]["value"]
    drawdowns: list[dict] = []

    for point in equity_curve:
        value = point["value"]
        if value > peak:
            peak = value
        dd_pct = round(((peak - value) / peak) * 100, 2)
        # Represent as negative percentage
        drawdowns.append({
            "time": point["time"],
            "value": -dd_pct,
        })

    return drawdowns


@router.get("", response_model=list[DrawdownPoint])
async def get_drawdown(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(require_auth),
):
    """Get drawdown curve data points."""
    equity_curve = compute_equity_curve(days=days)
    curve = compute_drawdown_curve(equity_curve)
    return [DrawdownPoint(**p) for p in curve]
