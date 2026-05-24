"""IPC reader: reads EA state and trade log files.

Reads ea_state.json (EA status) and trade_log.jsonl (trade history).
All reads are defensive — None/empty returns on missing or malformed files.
"""
import json
import logging
from pathlib import Path
from ..config import IPC_DIR

logger = logging.getLogger(__name__)


def read_ea_state(ipc_dir: Path | None = None) -> dict | None:
    """Read the EA state file. Returns None if file doesn't exist or is malformed."""
    ipc_dir = ipc_dir or (IPC_DIR / "Futra")
    state_file = ipc_dir / "ea_state.json"
    if not state_file.exists():
        return None
    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read EA state: {e}")
        return None


def read_trade_log(ipc_dir: Path | None = None) -> list[dict]:
    """Read the trade log file (JSONL). Returns list of trade dicts, empty list if no file."""
    ipc_dir = ipc_dir or (IPC_DIR / "Futra")
    log_file = ipc_dir / "trade_log.jsonl"
    if not log_file.exists():
        return []
    trades = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    trades.append(json.loads(line))
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read trade log: {e}")
    return trades
