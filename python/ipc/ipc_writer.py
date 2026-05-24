"""IPC writer: writes per-symbol AI params files with atomic write pattern.

Per D-08: Each symbol gets its own params file ({SYMBOL}_params.json).
Per DATA-09: File-based IPC between Python and EA (DWX Connect pattern).
Per T-01-02: Atomic write prevents EA from reading partially-written files.
"""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from ..config import IPC_DIR

logger = logging.getLogger(__name__)


def write_symbol_params(symbol: str, sl_percent: float, tp_percent: float,
                        max_position_size: float, regime: str = "trending",
                        confidence: float = 0.85, ipc_dir: Path | None = None) -> Path:
    """Write per-symbol AI params file. Uses atomic write (tmp + rename) to prevent
    partial reads by the EA. Per D-08 and IPC contract from Plan 01-01."""
    ipc_dir = ipc_dir or (IPC_DIR / "Futra")
    ipc_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sl_percent": float(sl_percent),
        "tp_percent": float(tp_percent),
        "max_position_size": float(max_position_size),
        "regime": regime,
        "confidence": float(confidence),
    }

    # Atomic write: write to .tmp, then rename (prevents EA from reading partial file)
    final_path = ipc_dir / f"{symbol}_params.json"
    tmp_path = ipc_dir / f"{symbol}_params.json.tmp"

    try:
        with open(tmp_path, "w") as f:
            json.dump(params, f, indent=2)
        os.replace(tmp_path, final_path)  # Atomic on Windows + POSIX
        logger.debug(f"Written params for {symbol} to {final_path}")
    except Exception:
        # Clean up tmp file on failure
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    return final_path
