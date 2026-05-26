"""AI regime detection: classifies market regime from computed features.

Uses interpretable threshold rules per PITFALLS.md #1:
- Start rule-based, validate on walk-forward data before adding ML.
- Interface designed for drop-in replacement with sklearn classifiers.
"""
import pandas as pd


class RegimeDetector:
    """Classifies market regime from computed features.

    Uses interpretable threshold rules. The predict(features) -> (str, float)
    interface mirrors sklearn's .predict() pattern for later ML swap-in.
    """

    # Regime labels
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"

    def __init__(
        self,
        adx_trend_threshold: float = 25.0,
        adx_low_threshold: float = 20.0,
        volatility_high_threshold: float = 0.25,
        volatility_low_threshold: float = 0.10,
        bb_width_high: float = 4.0,
        bb_width_low: float = 1.5,
        trend_ratio_far: float = 0.005,
    ):
        """Initialize with configurable thresholds.

        Args:
            adx_trend_threshold: ADX above this → trending signal
            adx_low_threshold: ADX below this → no trend
            volatility_high_threshold: Annualized vol above this → volatile
            volatility_low_threshold: Annualized vol below this → quiet
            bb_width_high: BB width % above this → volatile regime
            bb_width_low: BB width % below this → ranging/quiet
            trend_ratio_far: |close_to_sma20_pct| above this → trend confirmation
        """
        self.adx_trend = adx_trend_threshold
        self.adx_low = adx_low_threshold
        self.vol_high = volatility_high_threshold
        self.vol_low = volatility_low_threshold
        self.bb_high = bb_width_high
        self.bb_low = bb_width_low
        self.trend_ratio = trend_ratio_far

    def predict(self, features: dict[str, float]) -> tuple[str, float]:
        """Classify regime from feature dict.

        Returns:
            (regime_label, confidence) where regime is one of
            "trending"/"ranging"/"volatile"/"quiet" and confidence is 0.0-1.0.
        """
        # NaN guard — insufficient data → safe default
        adx = features.get("adx_14", float("nan"))
        if pd.isna(adx):
            return (self.QUIET, 0.0)

        vol = features.get("volatility_20", float("nan"))
        bb = features.get("bb_width_pct", float("nan"))
        trend_dist = abs(features.get("close_to_sma20_pct", 0.0))

        # Rule priority: VOLATILE > TRENDING > QUIET > RANGING

        # VOLATILE: High volatility OR wide bands — risk is elevated
        if (not pd.isna(vol) and vol > self.vol_high) or (
            not pd.isna(bb) and bb > self.bb_high
        ):
            vol_contrib = 0.0
            if not pd.isna(vol):
                vol_contrib = min((vol - self.vol_high) * 2.0, 0.3)
            bb_contrib = 0.0
            if not pd.isna(bb):
                bb_contrib = min((bb - self.bb_high) / self.bb_high, 0.3)
            confidence = min(0.9, 0.6 + max(vol_contrib, bb_contrib))
            return (self.VOLATILE, round(confidence, 2))

        # TRENDING: Strong ADX + price far from SMA
        if adx > self.adx_trend and trend_dist > self.trend_ratio:
            confidence = min(0.95, 0.6 + min(adx - self.adx_trend, 15) / 50)
            return (self.TRENDING, round(confidence, 2))

        # QUIET: Low ADX + low volatility + narrow bands
        if (
            adx < self.adx_low
            and (pd.isna(vol) or vol < self.vol_low)
            and (pd.isna(bb) or bb < self.bb_low)
        ):
            confidence = min(0.9, 0.5 + (self.adx_low - adx) / 40)
            return (self.QUIET, round(confidence, 2))

        # RANGING: Everything else — moderate ADX, moderate vol, price near SMA
        confidence = 0.5 + min(adx / 60, 0.4)
        return (self.RANGING, round(confidence, 2))
