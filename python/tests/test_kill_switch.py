"""Tests for kill_switch.py — activation, deactivation, file format, and atomic write.

All tests use temp IPC directories. Validates contract compliance per Plan 01-01:
kill_switch.json with active, close_positions, reason, timestamp fields.
"""
import json
from pathlib import Path
from python.kill_switch import activate_kill_switch, deactivate_kill_switch


class TestActivateKillSwitch:
    """Tests for activate_kill_switch()."""

    def test_default_activates_without_close(self, temp_ipc_dir):
        """activate_kill_switch() sets active=true, close_positions=false by default."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = activate_kill_switch(ipc_dir=ipc_futra)

        assert filepath.exists()
        assert filepath.name == "kill_switch.json"

        with open(filepath) as f:
            data = json.load(f)

        assert data["active"] is True
        assert data["close_positions"] is False
        assert data["reason"] == "manual"

    def test_activates_with_close_positions(self, temp_ipc_dir):
        """activate_kill_switch(close_positions=True) sets close_positions=true."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = activate_kill_switch(close_positions=True, ipc_dir=ipc_futra)

        with open(filepath) as f:
            data = json.load(f)

        assert data["active"] is True
        assert data["close_positions"] is True

    def test_creates_parent_directory(self, temp_ipc_dir):
        """activate_kill_switch creates IPC directory if it doesn't exist."""
        ipc_futra = temp_ipc_dir / "Futra"
        # temp_ipc_dir exists but Futra/ subdir doesn't
        filepath = activate_kill_switch(ipc_dir=ipc_futra)
        assert filepath.exists()

    def test_timestamp_is_iso8601(self, temp_ipc_dir):
        """activate_kill_switch writes ISO8601 timestamp."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = activate_kill_switch(ipc_dir=ipc_futra)
        with open(filepath) as f:
            data = json.load(f)
        # ISO8601 format contains "T" separator
        assert "T" in data["timestamp"]


class TestDeactivateKillSwitch:
    """Tests for deactivate_kill_switch()."""

    def test_deactivates(self, temp_ipc_dir):
        """deactivate_kill_switch() sets active=false."""
        ipc_futra = temp_ipc_dir / "Futra"
        # First activate
        activate_kill_switch(ipc_dir=ipc_futra)
        # Then deactivate
        filepath = deactivate_kill_switch(ipc_dir=ipc_futra)

        with open(filepath) as f:
            data = json.load(f)

        assert data["active"] is False
        assert data["close_positions"] is False
        assert data["reason"] == "manual_reset"

    def test_overwrites_previous_state(self, temp_ipc_dir):
        """deactivate_kill_switch overwrites an active kill switch."""
        ipc_futra = temp_ipc_dir / "Futra"
        activate_kill_switch(close_positions=True, ipc_dir=ipc_futra)
        filepath = deactivate_kill_switch(ipc_dir=ipc_futra)

        with open(filepath) as f:
            data = json.load(f)

        assert data["active"] is False
        assert data["close_positions"] is False


class TestAtomicWrite:
    """Tests for atomic write pattern (tmp + rename)."""

    def test_kill_switch_no_tmp_remains(self, temp_ipc_dir):
        """activate_kill_switch leaves no .tmp file after write."""
        ipc_futra = temp_ipc_dir / "Futra"
        activate_kill_switch(ipc_dir=ipc_futra)
        tmp_file = ipc_futra / "kill_switch.json.tmp"
        assert not tmp_file.exists(), f"Temporary file {tmp_file} was not cleaned up"

    def test_deactivate_no_tmp_remains(self, temp_ipc_dir):
        """deactivate_kill_switch leaves no .tmp file after write."""
        ipc_futra = temp_ipc_dir / "Futra"
        activate_kill_switch(ipc_dir=ipc_futra)
        deactivate_kill_switch(ipc_dir=ipc_futra)
        tmp_file = ipc_futra / "kill_switch.json.tmp"
        assert not tmp_file.exists(), f"Temporary file {tmp_file} was not cleaned up"


class TestFileLocation:
    """Tests for correct file path."""

    def test_writes_to_correct_path(self, temp_ipc_dir):
        """kill_switch.json is written to IPC_DIR / 'Futra' / 'kill_switch.json'."""
        ipc_futra = temp_ipc_dir / "Futra"
        filepath = activate_kill_switch(ipc_dir=ipc_futra)
        expected = ipc_futra / "kill_switch.json"
        assert filepath == expected
