"""Tests for ipc_writer.py and ipc_reader.py — per-symbol params files, atomic writes,
EA state reading, and trade log reading.

Tests validate IPC contract compliance per Plan 01-01: JSON structure, filename
convention, atomic write pattern. All tests use temp directories (no live MT5).
"""
import json
from pathlib import Path
from python.ipc.ipc_writer import write_symbol_params
from python.ipc.ipc_reader import read_ea_state, read_trade_log


class TestWriteSymbolParams:
    """Tests for write_symbol_params() — per-symbol params file creation."""

    def test_creates_file_with_correct_structure(self, temp_ipc_dir):
        """write_symbol_params writes {SYMBOL}_params.json with all contract fields."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = write_symbol_params(
            "EURUSD", sl_percent=0.02, tp_percent=0.04,
            max_position_size=0.1, ipc_dir=ipc_futra
        )
        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)

        assert data["symbol"] == "EURUSD"
        assert data["sl_percent"] == 0.02
        assert data["tp_percent"] == 0.04
        assert data["max_position_size"] == 0.1
        assert data["regime"] == "trending"
        assert data["confidence"] == 0.85
        # Timestamp must be ISO8601 format (contains "T" and "Z")
        assert "T" in data["timestamp"]
        assert data["timestamp"].endswith("Z")

    def test_atomic_write_no_tmp_remains(self, temp_ipc_dir):
        """write_symbol_params leaves no .tmp file after write (atomic rename)."""
        ipc_futra = temp_ipc_dir / "Futra"
        write_symbol_params("EURUSD", 0.02, 0.04, 0.1, ipc_dir=ipc_futra)
        # No .tmp file should remain
        tmp_file = ipc_futra / "EURUSD_params.json.tmp"
        assert not tmp_file.exists(), f"Temporary file {tmp_file} was not cleaned up"

    def test_writes_multiple_symbols(self, temp_ipc_dir):
        """write_symbol_params creates separate files for each symbol."""
        ipc_futra = temp_ipc_dir / "Futra"
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        for sym in symbols:
            write_symbol_params(sym, 0.02, 0.04, 0.1, ipc_dir=ipc_futra)

        for sym in symbols:
            filepath = ipc_futra / f"{sym}_params.json"
            assert filepath.exists(), f"Missing params file for {sym}"

    def test_filename_matches_symbol(self, temp_ipc_dir):
        """write_symbol_params creates file named {SYMBOL}_params.json."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = write_symbol_params("GBPUSD", 0.01, 0.03, 0.05, ipc_dir=ipc_futra)
        assert filepath.name == "GBPUSD_params.json"


class TestReadEAState:
    """Tests for read_ea_state() — reading EA state file."""

    def test_reads_valid_ea_state(self, temp_ipc_dir):
        """read_ea_state returns dict with expected keys when file exists."""
        ipc_futra = temp_ipc_dir / "Futra"
        ipc_futra.mkdir(parents=True, exist_ok=True)
        state = {
            "timestamp": "2026-05-24T12:00:00Z",
            "kill_switch_active": False,
            "open_positions": 0,
            "last_trade_timestamp": "2026-05-24T11:55:00Z",
        }
        with open(ipc_futra / "ea_state.json", "w") as f:
            json.dump(state, f)

        result = read_ea_state(ipc_dir=ipc_futra)
        assert result is not None
        assert result["kill_switch_active"] == False
        assert result["open_positions"] == 0

    def test_missing_file_returns_none(self, temp_ipc_dir):
        """read_ea_state returns None when ea_state.json doesn't exist."""
        ipc_futra = temp_ipc_dir / "Futra"
        ipc_futra.mkdir(parents=True, exist_ok=True)
        result = read_ea_state(ipc_dir=ipc_futra)
        assert result is None


class TestReadTradeLog:
    """Tests for read_trade_log() — reading JSONL trade log."""

    def test_reads_multiple_lines(self, temp_ipc_dir):
        """read_trade_log returns list of dicts from JSONL file."""
        ipc_futra = temp_ipc_dir / "Futra"
        ipc_futra.mkdir(parents=True, exist_ok=True)
        trades = [
            {"ticket": 1, "symbol": "EURUSD", "type": "buy", "volume": 0.1},
            {"ticket": 2, "symbol": "GBPUSD", "type": "sell", "volume": 0.05},
            {"ticket": 3, "symbol": "USDJPY", "type": "buy", "volume": 0.1},
        ]
        with open(ipc_futra / "trade_log.jsonl", "w") as f:
            for t in trades:
                f.write(json.dumps(t) + "\n")

        result = read_trade_log(ipc_dir=ipc_futra)
        assert len(result) == 3
        assert result[0]["ticket"] == 1
        assert result[1]["symbol"] == "GBPUSD"

    def test_missing_file_returns_empty_list(self, temp_ipc_dir):
        """read_trade_log returns empty list when trade_log.jsonl doesn't exist."""
        ipc_futra = temp_ipc_dir / "Futra"
        ipc_futra.mkdir(parents=True, exist_ok=True)
        result = read_trade_log(ipc_dir=ipc_futra)
        assert result == []
