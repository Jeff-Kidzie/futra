"""
IPC test utilities for EA integration testing.

Provides functions to create/cleanup IPC directories, write kill switch
and per-symbol params files, and read EA output files. Used by all EA
integration contract tests to verify the file-based IPC interface without
requiring a live MT5 connection (per D-10, D-11).
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

IPC_DIR_NAME = "Futra"


def create_ipc_dir(base_path: Path) -> Path:
    """Create the Futra/ IPC directory under base_path.

    Args:
        base_path: Parent directory (typically tmp_path from pytest).

    Returns:
        Path to the created Futra/ directory.
    """
    ipc_dir = base_path / IPC_DIR_NAME
    ipc_dir.mkdir(parents=True, exist_ok=True)
    return ipc_dir


def cleanup_ipc_dir(base_path: Path) -> None:
    """Remove the Futra/ IPC directory and all its contents.

    Args:
        base_path: Parent directory containing the Futra/ subdirectory.
    """
    ipc_dir = base_path / IPC_DIR_NAME
    if ipc_dir.exists():
        shutil.rmtree(ipc_dir)


def write_kill_switch(
    base_path: Path,
    active: bool,
    close_positions: bool,
    reason: str = "test",
) -> Path:
    """Write a kill_switch.json file to the IPC directory.

    Format matches the IPC contract defined in 01-01-PLAN.md:
    {
      "active": true/false,
      "close_positions": true/false,
      "reason": "manual_emergency",
      "timestamp": "2026-05-24T12:00:00Z"
    }

    Args:
        base_path: Parent directory containing Futra/.
        active: Whether the kill switch should activate.
        close_positions: Whether positions should be closed on activation.
        reason: Human-readable reason string.

    Returns:
        Path to the written kill_switch.json file.
    """
    ipc_dir = create_ipc_dir(base_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "active": active,
        "close_positions": close_positions,
        "reason": reason,
        "timestamp": timestamp,
    }
    ks_path = ipc_dir / "kill_switch.json"
    ks_path.write_text(json.dumps(data, indent=2))
    return ks_path


def write_symbol_params(
    base_path: Path,
    symbol: str,
    sl_percent: float,
    tp_percent: float,
    max_position_size: float,
    regime: str = "trending",
    confidence: float = 0.85,
) -> Path:
    """Write a per-symbol params file to the IPC directory.

    Format matches the IPC contract:
    {
      "symbol": "EURUSD",
      "timestamp": "2026-05-24T12:00:00Z",
      "sl_percent": 0.02,
      "tp_percent": 0.04,
      "max_position_size": 0.1,
      "regime": "trending",
      "confidence": 0.85
    }

    Args:
        base_path: Parent directory containing Futra/.
        symbol: Trading symbol name (e.g., "EURUSD").
        sl_percent: Stop-loss as percentage of entry price.
        tp_percent: Take-profit as percentage of entry price.
        max_position_size: Maximum lot size for this symbol.
        regime: Market regime classification.
        confidence: AI confidence score (0.0 to 1.0).

    Returns:
        Path to the written {SYMBOL}_params.json file.
    """
    ipc_dir = create_ipc_dir(base_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "symbol": symbol,
        "timestamp": timestamp,
        "sl_percent": sl_percent,
        "tp_percent": tp_percent,
        "max_position_size": max_position_size,
        "regime": regime,
        "confidence": confidence,
    }
    params_path = ipc_dir / f"{symbol}_params.json"
    params_path.write_text(json.dumps(data, indent=2))
    return params_path


def read_trade_log(base_path: Path) -> list[dict]:
    """Read and parse the trade_log.jsonl file.

    Each line is a JSON object matching the TradeResult struct fields.

    Args:
        base_path: Parent directory containing Futra/.

    Returns:
        List of parsed JSON trade log entries. Empty list if file
        doesn't exist or is empty.
    """
    ipc_dir = base_path / IPC_DIR_NAME
    log_path = ipc_dir / "trade_log.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def read_ea_state(base_path: Path) -> dict | None:
    """Read the ea_state.json file if it exists.

    Args:
        base_path: Parent directory containing Futra/.

    Returns:
        Parsed state dictionary, or None if the file doesn't exist.
    """
    ipc_dir = base_path / IPC_DIR_NAME
    state_path = ipc_dir / "ea_state.json"
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text())


@pytest.fixture
def temp_ipc_dir(tmp_path: Path) -> Path:
    """Pytest fixture providing a temporary IPC base directory.

    Creates the Futra/ subdirectory before each test and cleans it up
    afterward. Yields the base_path (parent), NOT the Futra/ dir.

    Usage:
        def test_something(temp_ipc_dir):
            write_kill_switch(temp_ipc_dir, active=True, ...)
    """
    create_ipc_dir(tmp_path)
    yield tmp_path
    cleanup_ipc_dir(tmp_path)
