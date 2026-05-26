"""AI engine orchestration: evaluates market conditions per symbol and writes parameters.

Per ARCHITECTURE.md Pattern 3: Async service loop at configurable evaluation intervals.
Per AI-01: Classifies regime per symbol per timeframe.
Per AI-02: Adapts SL/TP and position sizing based on regime and volatility.
"""
import logging

from ..config import DEFAULT_SYMBOLS
from ..mt5_connector import ensure_connected, MT5Error
from ..data_pipeline import fetch_historical_ohlcv
from ..ipc.ipc_writer import write_symbol_params
from .features import compute_features
from .regime_detector import RegimeDetector
from .parameter_adapter import ParameterAdapter


class AIEngine:
    """Main AI orchestration — evaluates market conditions per symbol and writes parameters."""

    def __init__(
        self,
        symbols: list[str] | None = None,
        timeframe: str = "H1",
        regime_detector: RegimeDetector | None = None,
        parameter_adapter: ParameterAdapter | None = None,
    ):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.timeframe = timeframe
        self.detector = regime_detector or RegimeDetector()
        self.adapter = parameter_adapter or ParameterAdapter()
        self.logger = logging.getLogger(__name__)

    def evaluate_symbol(self, symbol: str) -> dict | None:
        """Full AI pipeline for one symbol: data → features → regime → params → IPC write.

        Returns: dict with evaluation result or None on failure.
        """
        try:
            # 1. Fetch latest data
            ensure_connected()
            df = fetch_historical_ohlcv(symbol, self.timeframe, bar_count=200)

            # 2. Compute features
            features = compute_features(df)

            # 3. Detect regime
            regime, confidence = self.detector.predict(features)

            # 4. Get volatility and ATR for SL scaling
            volatility = features.get("volatility_20", None)
            atr_pips = features.get("atr_14", None)

            # 5. Adapt parameters
            adapted = self.adapter.adapt(
                regime=regime,
                confidence=confidence,
                volatility=volatility,
                atr_pips=atr_pips,
                equity=10000.0,
            )

            # 6. Convert to IPC format and write
            ipc_params = self.adapter.to_ipc_params(adapted, symbol)
            write_symbol_params(
                symbol=symbol,
                sl_percent=ipc_params["sl_percent"],
                tp_percent=ipc_params["tp_percent"],
                max_position_size=ipc_params["max_position_size"],
                regime=ipc_params["regime"],
                confidence=ipc_params["confidence"],
            )

            self.logger.info(
                f"AI: {symbol} regime={regime} conf={confidence:.2f} "
                f"sl={adapted['sl_pips']}pips tp={adapted['tp_pips']}pips "
                f"lot={adapted['lot_size']}"
            )

            return {
                "symbol": symbol,
                "regime": regime,
                "confidence": confidence,
                "adapted": adapted,
            }

        except MT5Error as e:
            self.logger.error(f"AI engine: MT5 error for {symbol}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"AI engine: unexpected error for {symbol}: {e}", exc_info=True)
            return None

    def run_once(self) -> list[dict]:
        """Run one evaluation pass across all symbols. Returns list of results."""
        results = []
        for symbol in self.symbols:
            result = self.evaluate_symbol(symbol)
            if result is not None:
                results.append(result)
        return results
