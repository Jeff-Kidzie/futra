"""Kill switch trigger script — writes kill_switch.json to IPC directory.

Per D-01: File-based kill switch signal — EA polls the file every tick.
Per D-02: Configurable close_positions flag — when true, EA closes all open positions.
Per D-03: Triggerable via Python script (remote SSH or scheduled task).
Per T-01-02: Atomic write prevents EA from reading partially-written JSON.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .config import IPC_DIR


def _write_kill_switch_file(active: bool, close_positions: bool = False,
                             reason: str = "manual", ipc_dir: Path | None = None) -> Path:
    """Write the kill switch signal file. Per D-01, D-02 contract."""
    ipc_dir = ipc_dir or (IPC_DIR / "Futra")
    ipc_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "active": active,
        "close_positions": close_positions,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    file_path = ipc_dir / "kill_switch.json"
    tmp_path = ipc_dir / "kill_switch.json.tmp"

    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, file_path)  # Atomic write per D-02 (EA reads this file every tick)
    return file_path


def activate_kill_switch(close_positions: bool = False, reason: str = "manual",
                         ipc_dir: Path | None = None) -> Path:
    """Activate the kill switch. Set close_positions=True to close all positions."""
    return _write_kill_switch_file(active=True, close_positions=close_positions,
                                    reason=reason, ipc_dir=ipc_dir)


def deactivate_kill_switch(ipc_dir: Path | None = None) -> Path:
    """Deactivate the kill switch, allowing trading to resume."""
    return _write_kill_switch_file(active=False, close_positions=False,
                                    reason="manual_reset", ipc_dir=ipc_dir)
