"""AI parameter adapter: adapts SL/TP and position sizing based on regime, confidence, and volatility.

Per RISK-06: Position sizing adapts to account equity, recent metrics, volatility, and regime.
Per AI-02: SL/TP levels adapt based on detected regime and volatility.
"""


class ParameterAdapter:
    """Adapts SL/TP and position sizing based on regime, confidence, and volatility."""

    # Base defaults — conservative starting point
    DEFAULT_SL_PIPS = 50.0
    DEFAULT_TP_PIPS = 100.0
    DEFAULT_LOT_SIZE = 0.10   # 0.10 lot baseline (allows volatile reduction below floor)
    MAX_RISK_PCT = 0.02

    # Regime multipliers for SL (wider = more room = higher multiplier)
    SL_MULTIPLIERS = {
        "trending": 1.0,
        "ranging": 0.8,
        "volatile": 1.5,
        "quiet": 0.7,
    }

    # Regime multipliers for TP
    TP_MULTIPLIERS = {
        "trending": 1.5,
        "ranging": 0.7,
        "volatile": 1.3,
        "quiet": 0.8,
    }

    # Regime multipliers for position size
    LOT_MULTIPLIERS = {
        "trending": 1.0,
        "ranging": 0.8,
        "volatile": 0.5,
        "quiet": 1.0,
    }

    def __init__(
        self,
        max_position_size: float = 0.1,
        default_sl_pips: float = DEFAULT_SL_PIPS,
        default_tp_pips: float = DEFAULT_TP_PIPS,
        default_lot_size: float = DEFAULT_LOT_SIZE,
        max_risk_pct: float = MAX_RISK_PCT,
    ):
        self.max_position_size = max_position_size
        self.default_sl = default_sl_pips
        self.default_tp = default_tp_pips
        self.default_lot = default_lot_size
        self.max_risk = max_risk_pct

    def adapt(
        self,
        regime: str,
        confidence: float,
        volatility: float | None,
        equity: float = 10000.0,
        atr_pips: float | None = None,
    ) -> dict:
        """Compute adapted SL/TP and position sizing.

        Args:
            regime: One of "trending"/"ranging"/"volatile"/"quiet"
            confidence: 0.0-1.0 confidence in regime classification
            volatility: Annualized volatility (e.g., 0.15 = 15%)
            equity: Current account equity in account currency
            atr_pips: ATR in pips. If provided, used instead of volatility for SL scaling.

        Returns:
            dict with keys: sl_pips, tp_pips, lot_size, regime, confidence
        """
        # Safety: low confidence → conservative defaults
        if confidence < 0.5:
            return {
                "sl_pips": self.default_sl,
                "tp_pips": self.default_tp,
                "lot_size": self.default_lot,
                "regime": regime,
                "confidence": confidence,
            }

        # Get regime multipliers
        sl_mult = self.SL_MULTIPLIERS.get(regime, 1.0)
        tp_mult = self.TP_MULTIPLIERS.get(regime, 1.0)
        lot_mult = self.LOT_MULTIPLIERS.get(regime, 1.0)

        # SL calculation: base * regime multiplier * volatility factor
        vol_factor = 1.0
        if atr_pips is not None and atr_pips > 0:
            vol_factor = max(0.5, atr_pips / 20.0)
        elif volatility is not None and volatility > 0:
            vol_factor = max(0.5, volatility / 0.15)

        sl_pips = round(self.default_sl * sl_mult * vol_factor, 1)
        sl_pips = max(sl_pips, 10.0)  # Floor: never less than 10 pips

        # TP calculation: base * regime multiplier * volatility factor
        tp_pips = round(self.default_tp * tp_mult * vol_factor, 1)
        # Ensure TP >= 1.5x SL (minimum risk-reward)
        if tp_pips < sl_pips * 1.5:
            tp_pips = round(sl_pips * 1.5, 1)

        # Position sizing: Kelly-adjacent fractional sizing
        equity_ratio = equity / 10000.0
        lot_size = self.default_lot * equity_ratio * lot_mult
        lot_size = max(lot_size, 0.01)  # Floor: minimum tradeable size
        lot_size = min(lot_size, self.max_position_size)  # Cap
        lot_size = round(lot_size, 2)

        return {
            "sl_pips": sl_pips,
            "tp_pips": tp_pips,
            "lot_size": lot_size,
            "regime": regime,
            "confidence": confidence,
        }

    def to_ipc_params(self, adapted: dict, symbol: str) -> dict:
        """Convert adapted parameters to IPC params format.

        SL/TP stored as percentages (pips → percentage using approximation).
        1 pip ≈ 0.01% of price for most forex pairs.
        """
        sl_percent = adapted["sl_pips"] * 0.01
        tp_percent = adapted["tp_pips"] * 0.01
        return {
            "symbol": symbol,
            "sl_percent": round(sl_percent, 4),
            "tp_percent": round(tp_percent, 4),
            "max_position_size": adapted["lot_size"],
            "regime": adapted["regime"],
            "confidence": adapted["confidence"],
        }
