"""AI decision logger: records every parameter decision as structured JSONL.

Per AI-04: Logs regime, confidence, chosen parameters, and reasoning.
Per D-08: Per-symbol files in dedicated directory.
"""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from ..config import AI_LOG_DIR

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Structured JSONL logger for AI parameter decisions.

    Writes one JSON object per line to a rotating daily log file.
    Human-readable format — each line is a complete, self-contained decision record.
    """

    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or AI_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_date = None
        self._file_path = None

    def _get_log_path(self) -> Path:
        """Get today's log file path. Rotates daily."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._current_date:
            self._current_date = today
            self._file_path = self.log_dir / f"ai_decisions_{today}.jsonl"
        return self._file_path

    def _build_reasoning(
        self,
        symbol: str,
        regime: str,
        confidence: float,
        sl_pips: float,
        tp_pips: float,
        lot_size: float,
        volatility: float | None,
        atr: float | None,
    ) -> str:
        """Build human-readable reasoning for the parameter decision."""
        parts = []

        # Regime context
        parts.append(f"Market regime for {symbol}: {regime} (confidence: {confidence:.0%})")

        # Volatility context
        if volatility is not None:
            parts.append(f"Annualized volatility: {volatility:.1%}")
        if atr is not None and atr > 0:
            parts.append(f"ATR(14): {atr:.1f} pips")

        # Parameter reasoning
        rr_ratio = tp_pips / sl_pips if sl_pips > 0 else 0
        parts.append(
            f"Set SL={sl_pips:.1f}pips, TP={tp_pips:.1f}pips "
            f"(RR={rr_ratio:.1f}:1), lot={lot_size:.2f}"
        )

        # Regime-specific explanation
        regime_reasons = {
            "trending": "Trending market — wider TP to let winners run, normal position sizing",
            "ranging": "Ranging market — tighter TP to capture range-bound reversals, reduced position sizing",
            "volatile": "Volatile market — wider SL to avoid noise-stops, half position sizing for risk management",
            "quiet": "Quiet market — tight SL for precision entries, normal sizing due to low noise",
        }
        reason = regime_reasons.get(
            regime, f"Unknown regime ({regime}) — using conservative defaults"
        )
        parts.append(reason)

        return ". ".join(parts)

    def log_decision(
        self,
        symbol: str,
        regime: str,
        confidence: float,
        sl_pips: float,
        tp_pips: float,
        lot_size: float,
        volatility: float | None = None,
        atr: float | None = None,
        features: dict[str, float] | None = None,
    ) -> Path:
        """Record an AI parameter decision to the JSONL log.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            regime: Detected regime ("trending"/"ranging"/"volatile"/"quiet")
            confidence: Regime confidence (0.0-1.0)
            sl_pips: Adapted stop-loss in pips
            tp_pips: Adapted take-profit in pips
            lot_size: Adapted position size in lots
            volatility: Annualized volatility (optional)
            atr: ATR value in pips (optional)
            features: Diagnostic feature snapshot (optional)

        Returns: Path to the log file written to.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build diagnostic feature snapshot (6 most diagnostic keys)
        features_snapshot = {}
        if features:
            feature_keys = [
                "atr_14", "volatility_20", "rsi_14", "adx_14",
                "bb_width_pct", "close_to_sma20_pct",
            ]
            for key in feature_keys:
                val = features.get(key)
                if isinstance(val, (int, float)) and not (
                    isinstance(val, float) and val != val
                ):
                    features_snapshot[key] = round(val, 4)
                else:
                    features_snapshot[key] = None

        reasoning = self._build_reasoning(
            symbol, regime, confidence, sl_pips, tp_pips, lot_size, volatility, atr
        )

        record = {
            "timestamp": timestamp,
            "symbol": symbol,
            "regime": regime,
            "confidence": round(confidence, 4),
            "sl_pips": round(sl_pips, 1),
            "tp_pips": round(tp_pips, 1),
            "lot_size": round(lot_size, 2),
            "volatility": round(volatility, 4) if volatility is not None else None,
            "atr": round(atr, 1) if atr is not None else None,
            "features_snapshot": features_snapshot,
            "reasoning": reasoning,
        }

        log_path = self._get_log_path()
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(f"Logged AI decision: {symbol} {regime}")
        except IOError as e:
            logger.error(f"Failed to write decision log: {e}")

        return log_path
