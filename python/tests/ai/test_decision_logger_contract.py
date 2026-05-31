"""G2 contract tests: DecisionLogger single-file mode + required timeframe parameter.

These tests verify the post-G2 behavior:
- Single canonical file: decision_log.jsonl (no daily rotation)
- timeframe is a required parameter (TypeError on omission)
- Record dict includes timeframe (passes Pydantic Decision validation)

Existing tests in test_decision_logger.py use the old signature and will be
updated in plan 06 (Wave C).
"""
import json
import pytest
from pathlib import Path
from python.ai.decision_logger import DecisionLogger
from python.dashboard.models import Decision


@pytest.fixture
def logger(tmp_path):
    """Create a DecisionLogger writing to a temp directory."""
    log_dir = tmp_path / "ai_decisions"
    return DecisionLogger(log_dir=log_dir)


class TestSingleFileMode:
    """DecisionLogger writes to a single canonical decision_log.jsonl."""

    def test_creates_decision_log_jsonl(self, logger, tmp_path):
        """DecisionLogger creates decision_log.jsonl on first log_decision call."""
        log_dir = tmp_path / "ai_decisions"
        logger.log_decision(
            "EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10
        )
        log_file = log_dir / "decision_log.jsonl"
        assert log_file.exists(), "decision_log.jsonl not created"

    def test_log_path_attribute(self, logger, tmp_path):
        """DecisionLogger has a log_path attribute set to decision_log.jsonl."""
        log_dir = tmp_path / "ai_decisions"
        assert hasattr(logger, "log_path")
        assert logger.log_path == log_dir / "decision_log.jsonl"

    def test_no_daily_rotation_attributes(self, logger):
        """DecisionLogger no longer has _current_date or _file_path attributes."""
        assert not hasattr(logger, "_current_date")
        assert not hasattr(logger, "_file_path")

    def test_no_get_log_path_method(self, logger):
        """DecisionLogger no longer has _get_log_path method."""
        assert not hasattr(logger, "_get_log_path")

    def test_three_calls_same_file(self, logger, tmp_path):
        """Three back-to-back log_decision calls all append to the SAME file."""
        log_dir = tmp_path / "ai_decisions"
        logger.log_decision("EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10)
        logger.log_decision("GBPUSD", "H1", "ranging", 0.70, 40.0, 80.0, 0.05)
        logger.log_decision("USDJPY", "H1", "volatile", 0.60, 60.0, 120.0, 0.03)

        log_file = log_dir / "decision_log.jsonl"
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 3, f"Expected 3 lines in same file, got {len(lines)}"

        # Verify no daily-rotation files exist
        all_jsonl = list(log_dir.glob("*.jsonl"))
        assert len(all_jsonl) == 1, f"Expected exactly 1 JSONL file, got {len(all_jsonl)}"
        assert all_jsonl[0].name == "decision_log.jsonl"


class TestRequiredTimeframe:
    """log_decision requires timeframe as second positional argument."""

    def test_log_decision_with_timeframe_succeeds(self, logger):
        """log_decision with timeframe argument succeeds."""
        result = logger.log_decision(
            "EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10
        )
        assert isinstance(result, Path)

    def test_log_decision_without_timeframe_raises_type_error(self, logger):
        """Calling log_decision WITHOUT timeframe raises TypeError."""
        with pytest.raises(TypeError):
            # Old signature: 6 positional args (no timeframe)
            logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.10)

    def test_timeframe_in_record(self, logger, tmp_path):
        """Emitted record contains timeframe field with correct value."""
        log_dir = tmp_path / "ai_decisions"
        logger.log_decision(
            "EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10
        )
        log_file = log_dir / "decision_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "timeframe" in record, "Record missing timeframe field"
        assert record["timeframe"] == "H1"

    def test_timeframe_position_between_symbol_and_regime(self, logger, tmp_path):
        """timeframe is the second positional parameter (after symbol, before regime)."""
        log_dir = tmp_path / "ai_decisions"
        # Using keyword args to verify the parameter exists with correct name
        logger.log_decision(
            symbol="EURUSD",
            timeframe="H4",
            regime="ranging",
            confidence=0.70,
            sl_pips=40.0,
            tp_pips=80.0,
            lot_size=0.05,
        )
        log_file = log_dir / "decision_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["timeframe"] == "H4"
        assert record["symbol"] == "EURUSD"
        assert record["regime"] == "ranging"


class TestPydanticRoundTrip:
    """Emitted records pass Decision Pydantic validation."""

    def test_record_passes_pydantic_validation(self, logger, tmp_path):
        """Each emitted record passes Decision(**record) Pydantic validation."""
        log_dir = tmp_path / "ai_decisions"
        logger.log_decision(
            "EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10
        )
        log_file = log_dir / "decision_log.jsonl"
        record = json.loads(log_file.read_text().strip())
        # Must not raise ValidationError
        decision = Decision(**record)
        assert decision.timeframe == "H1"
        assert decision.symbol == "EURUSD"
        assert decision.regime == "trending"

    def test_multiple_records_all_pass_pydantic(self, logger, tmp_path):
        """Multiple emitted records all pass Pydantic validation."""
        log_dir = tmp_path / "ai_decisions"
        logger.log_decision("EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.10)
        logger.log_decision("GBPUSD", "M15", "ranging", 0.70, 40.0, 80.0, 0.05)
        logger.log_decision("USDJPY", "H4", "volatile", 0.60, 60.0, 120.0, 0.03)

        log_file = log_dir / "decision_log.jsonl"
        for line in log_file.read_text().strip().splitlines():
            record = json.loads(line)
            decision = Decision(**record)
            assert decision.timeframe in ("H1", "M15", "H4")


class TestSourceCodeGuards:
    """Mechanical assertions on source code to prevent regression."""

    def test_no_daily_rotation_filename_in_source(self):
        """Source code contains no reference to ai_decisions_ (daily rotation gone)."""
        src = Path("python/ai/decision_logger.py").read_text()
        assert "ai_decisions_" not in src, "Daily rotation filename pattern still in source"

    def test_no_get_log_path_in_source(self):
        """Source code contains no _get_log_path method."""
        src = Path("python/ai/decision_logger.py").read_text()
        assert "_get_log_path" not in src, "_get_log_path method still in source"

    def test_single_file_path_constant_in_source(self):
        """Source code sets self.log_path to decision_log.jsonl."""
        src = Path("python/ai/decision_logger.py").read_text()
        assert 'self.log_path = self.log_dir / "decision_log.jsonl"' in src
