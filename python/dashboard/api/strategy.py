"""GET /api/strategy — current strategy config JSON."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends
from ..auth import require_auth
from ..models import StrategyConfig
from ...config import STRATEGY_CONFIG_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/strategy", tags=["strategy"])


def read_strategy_config() -> dict:
    """Read the latest strategy config JSON file."""
    path = STRATEGY_CONFIG_DIR
    if not path.exists():
        return {}

    json_files = sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        return {}

    try:
        with open(json_files[0], "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to read strategy config: %s", e)
        return {}


@router.get("", response_model=StrategyConfig)
async def get_strategy(user_id: int = Depends(require_auth)):
    """Get current strategy configuration."""
    config = read_strategy_config()
    return StrategyConfig(config=config)
