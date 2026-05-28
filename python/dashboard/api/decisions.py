"""GET /api/decisions — paginated AI decision log from decision_log.jsonl."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from ..auth import require_auth
from ..models import Decision
from ...config import AI_LOG_DIR

logger = logging.getLogger(__name__)

DECISION_LOG_PATH = AI_LOG_DIR / "decision_log.jsonl"
router = APIRouter(prefix="/api/decisions", tags=["decisions"])


def read_decisions(symbol: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """Read AI decision log from JSONL file."""
    if not DECISION_LOG_PATH.exists():
        return []

    decisions: list[dict] = []
    try:
        with open(DECISION_LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Malformed JSON line in decision_log.jsonl, skipping")
                    continue

                if symbol is None or entry.get("symbol") == symbol:
                    decisions.append(entry)
    except Exception as e:
        logger.error("Error reading decision log: %s", e)
        return []

    # Sort by timestamp descending
    decisions.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
    return decisions[offset:offset + limit]


@router.get("", response_model=list[Decision])
async def get_decisions(
    symbol: str | None = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(require_auth),
):
    """Get paginated AI decision log with optional symbol filter."""
    decisions = read_decisions(symbol=symbol, limit=limit, offset=offset)
    return [Decision(**d) for d in decisions]
