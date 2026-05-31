"""Strategy configuration manager: export/import RegimeDetector and ParameterAdapter settings.

Per AI-05: Strategy parameter export/import as JSON for versioning and A/B testing.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from ..config import STRATEGY_CONFIG_DIR

logger = logging.getLogger(__name__)

# Current strategy schema version — increment when config format changes
STRATEGY_SCHEMA_VERSION = "1.0.0"


class StrategyManager:
    """Export and import AI strategy configurations as JSON files."""

    REQUIRED_KEYS = {"regime_detector", "parameter_adapter", "metadata"}
    REQUIRED_DETECTOR_KEYS = {
        "adx_trend_threshold", "adx_low_threshold",
        "volatility_high_threshold", "volatility_low_threshold",
        "bb_width_high", "bb_width_low", "trend_ratio_far",
    }
    REQUIRED_ADAPTER_KEYS = {
        "max_position_size", "default_sl_pips",
        "default_tp_pips", "default_lot_size", "max_risk_pct",
    }

    def __init__(self, strategy_dir: Path | None = None):
        self.strategy_dir = strategy_dir or STRATEGY_CONFIG_DIR
        self.strategy_dir.mkdir(parents=True, exist_ok=True)

    def export_strategy(
        self,
        detector,
        adapter,
        filepath: Path | None = None,
        description: str = "",
    ) -> Path:
        """Export current RegimeDetector and ParameterAdapter settings to JSON."""
        regime_config = {
            "adx_trend_threshold": detector.adx_trend,
            "adx_low_threshold": detector.adx_low,
            "volatility_high_threshold": detector.vol_high,
            "volatility_low_threshold": detector.vol_low,
            "bb_width_high": detector.bb_high,
            "bb_width_low": detector.bb_low,
            "trend_ratio_far": detector.trend_ratio,
        }

        adapter_config = {
            "max_position_size": adapter.max_position_size,
            "default_sl_pips": adapter.default_sl,
            "default_tp_pips": adapter.default_tp,
            "default_lot_size": adapter.default_lot,
            "max_risk_pct": adapter.max_risk,
            "sl_multipliers": adapter.SL_MULTIPLIERS,
            "tp_multipliers": adapter.TP_MULTIPLIERS,
            "lot_multipliers": adapter.LOT_MULTIPLIERS,
        }

        regime_labels = {
            "TRENDING": detector.TRENDING,
            "RANGING": detector.RANGING,
            "VOLATILE": detector.VOLATILE,
            "QUIET": detector.QUIET,
        }

        strategy = {
            "metadata": {
                "version": STRATEGY_SCHEMA_VERSION,
                "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "description": description,
            },
            "regime_detector": regime_config,
            "parameter_adapter": adapter_config,
            "regime_labels": regime_labels,
        }

        if filepath is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filepath = self.strategy_dir / f"strategy_{ts}.json"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(strategy, f, indent=2)

        logger.info(f"Strategy exported to {filepath}")
        return filepath

    def import_strategy(self, filepath: Path) -> dict:
        """Read a strategy JSON file and return the config dict.

        Validates required keys are present.

        Raises:
            ValueError: If required keys are missing or file is malformed
            FileNotFoundError: If filepath does not exist
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Strategy file not found: {filepath}")

        with open(filepath, "r") as f:
            strategy = json.load(f)

        # Validate top-level structure
        missing = self.REQUIRED_KEYS - set(strategy.keys())
        if missing:
            raise ValueError(f"Strategy file missing required keys: {missing}")

        # Validate detector keys
        detector = strategy.get("regime_detector", {})
        missing_det = self.REQUIRED_DETECTOR_KEYS - set(detector.keys())
        if missing_det:
            raise ValueError(f"Regime detector config missing keys: {missing_det}")

        # Validate adapter keys
        adapter = strategy.get("parameter_adapter", {})
        missing_adp = self.REQUIRED_ADAPTER_KEYS - set(adapter.keys())
        if missing_adp:
            raise ValueError(f"Parameter adapter config missing keys: {missing_adp}")

        logger.info(
            f"Strategy imported from {filepath} "
            f"(v{strategy['metadata'].get('version', 'unknown')})"
        )
        return strategy

    def apply_strategy(self, detector, adapter, strategy: dict) -> bool:
        """Apply imported strategy settings to detector and adapter in-place."""
        reg = strategy["regime_detector"]
        par = strategy["parameter_adapter"]

        # Apply detector thresholds
        detector.adx_trend = reg["adx_trend_threshold"]
        detector.adx_low = reg["adx_low_threshold"]
        detector.vol_high = reg["volatility_high_threshold"]
        detector.vol_low = reg["volatility_low_threshold"]
        detector.bb_high = reg["bb_width_high"]
        detector.bb_low = reg["bb_width_low"]
        detector.trend_ratio = reg["trend_ratio_far"]

        # Apply adapter settings
        adapter.max_position_size = par["max_position_size"]
        adapter.default_sl = par["default_sl_pips"]
        adapter.default_tp = par["default_tp_pips"]
        adapter.default_lot = par["default_lot_size"]
        adapter.max_risk = par["max_risk_pct"]

        # Apply multiplier overrides if present
        if "sl_multipliers" in par:
            adapter.SL_MULTIPLIERS.update(par["sl_multipliers"])
        if "tp_multipliers" in par:
            adapter.TP_MULTIPLIERS.update(par["tp_multipliers"])
        if "lot_multipliers" in par:
            adapter.LOT_MULTIPLIERS.update(par["lot_multipliers"])

        logger.info("Strategy applied to detector and adapter instances")
        return True
