"""Tests for AI decision logger (DecisionLogger)."""
import json
import pytest
from pathlib import Path
from datetime import datetime
from python.ai.decision_logger import DecisionLogger


@pytest.fixture
def logger(tmp_path):
    """Create a DecisionLogger writing to a temp directory."""
    log_dir = tmp_path / "ai_decisions"
    return DecisionLogger(log_dir=log_dir)


def test_log_decision_creates_file(logger, tmp_path):
    """Test 1: First log_decision() call creates the log file."""
    log_dir = tmp_path / "ai_decisions"
    assert not any(log_dir.glob("*.jsonl"))
    logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.01)
    files = list(log_dir.glob("*.jsonl"))
    assert len(files) == 1


def test_log_line_is_valid_json_with_required_keys(logger, tmp_path):
    """Test 2: Each line is valid JSON with all required keys."""
    logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.01)
    log_dir = tmp_path / "ai_decisions"
    file = next(log_dir.glob("*.jsonl"))
    line = file.read_text().strip()
    record = json.loads(line)
    required = {
        "timestamp", "symbol", "regime", "confidence", "sl_pips",
        "tp_pips", "lot_size", "volatility", "features_snapshot", "reasoning",
    }
    assert required.issubset(set(record.keys()))


def test_timestamp_is_iso8601_utc(logger, tmp_path):
    """Test 3: timestamp is parseable ISO8601 UTC."""
    logger.log_decision("EURUSD", "quiet", 0.6, 30.0, 60.0, 0.01)
    log_dir = tmp_path / "ai_decisions"
    file = next(log_dir.glob("*.jsonl"))
    record = json.loads(file.read_text().strip())
    dt = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
    assert dt.tzinfo is not None


def test_reasoning_is_not_empty(logger, tmp_path):
    """Test 4: reasoning field is human-readable, not empty."""
    logger.log_decision(
        "EURUSD", "volatile", 0.7, 80.0, 140.0, 0.01,
        volatility=0.28, atr=45.0,
    )
    log_dir = tmp_path / "ai_decisions"
    file = next(log_dir.glob("*.jsonl"))
    record = json.loads(file.read_text().strip())
    reasoning = record["reasoning"]
    assert len(reasoning) > 20
    assert "EURUSD" in reasoning
    assert "volatile" in reasoning.lower()
    assert "SL=" in reasoning or "sl" in reasoning.lower()


def test_log_appends_not_overwrites(logger, tmp_path):
    """Test 5: Two calls produce 2 lines in the same file."""
    logger.log_decision("EURUSD", "trending", 0.8, 50.0, 100.0, 0.01)
    logger.log_decision("GBPUSD", "ranging", 0.7, 40.0, 80.0, 0.01)
    log_dir = tmp_path / "ai_decisions"
    file = next(log_dir.glob("*.jsonl"))
    lines = file.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        json.loads(line)


def test_log_directory_autocreated(tmp_path):
    """Test 6: Log directory created automatically if missing."""
    log_dir = tmp_path / "nonexistent" / "ai_decisions"
    assert not log_dir.exists()
    logger = DecisionLogger(log_dir=log_dir)
    assert log_dir.exists()


def test_features_snapshot_subset(logger, tmp_path):
    """Test 7: features_snapshot contains only the 6 diagnostic keys."""
    features = {
        "atr_14": 25.0, "volatility_20": 0.15, "rsi_14": 55.0,
        "adx_14": 30.0, "bb_width_pct": 3.0, "close_to_sma20_pct": 1.5,
        "macd": 0.001, "macd_signal": 0.0008, "sma_20_50_ratio": 1.002,
        "volume_ratio": 1.1,
    }
    logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.01, features=features)
    log_dir = tmp_path / "ai_decisions"
    file = next(log_dir.glob("*.jsonl"))
    record = json.loads(file.read_text().strip())
    snapshot = record["features_snapshot"]
    expected_keys = {"atr_14", "volatility_20", "rsi_14", "adx_14", "bb_width_pct", "close_to_sma20_pct"}
    assert set(snapshot.keys()) == expected_keys


def test_log_decision_accepts_optional_ipc_dir(tmp_path):
    """Test 8: DecisionLogger accepts optional log_dir parameter."""
    custom_dir = tmp_path / "custom_log"
    logger = DecisionLogger(log_dir=custom_dir)
    assert custom_dir.exists()
    logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.01)
    files = list(custom_dir.glob("*.jsonl"))
    assert len(files) == 1
