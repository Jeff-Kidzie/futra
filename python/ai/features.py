"""AI feature engineering: computes technical indicators from OHLCV DataFrames.

Uses TA-Lib for indicator computation. All features are computed from DataFrame input —
no live MT5 connection needed. Per AI-01: features feed regime detection and parameter adaptation.
"""
import numpy as np
import pandas as pd
import talib

MIN_BAR_COUNT = 50

FEATURE_KEYS = [
    "atr_14",
    "volatility_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "adx_14",
    "sma_20_50_ratio",
    "bb_width_pct",
    "close_to_sma20_pct",
    "volume_ratio",
]


def _nan_dict() -> dict[str, float]:
    """Return a dict with all feature keys set to NaN."""
    return {key: float("nan") for key in FEATURE_KEYS}


def compute_features(df: pd.DataFrame) -> dict[str, float]:
    """Compute technical indicator features from OHLCV DataFrame.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, tick_volume.

    Returns:
        dict with 10 feature keys (all float values). Returns NaN-filled dict
        when DataFrame has fewer than 50 rows.
    """
    if len(df) < MIN_BAR_COUNT:
        return _nan_dict()

    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    tick_volume = df["tick_volume"].values.astype(float)

    # ATR (14-period)
    atr = talib.ATR(high, low, close, timeperiod=14)
    atr_14 = float(atr[-1]) if not np.isnan(atr[-1]) else float("nan")

    # Historical volatility (20-period annualized)
    returns = df["close"].pct_change().dropna()
    if len(returns) >= 20:
        vol_20 = float(returns.tail(20).std() * np.sqrt(252))
    else:
        vol_20 = float("nan")

    # RSI (14-period)
    rsi = talib.RSI(close, timeperiod=14)
    rsi_14 = float(rsi[-1]) if not np.isnan(rsi[-1]) else float("nan")

    # MACD (12, 26, 9)
    macd_line, macd_signal, _ = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )
    macd_val = float(macd_line[-1]) if not np.isnan(macd_line[-1]) else float("nan")
    macd_sig = float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else float("nan")

    # ADX (14-period)
    adx = talib.ADX(high, low, close, timeperiod=14)
    adx_14 = float(adx[-1]) if not np.isnan(adx[-1]) else float("nan")

    # SMA(20) / SMA(50) ratio
    sma_20 = talib.SMA(close, timeperiod=20)
    sma_50 = talib.SMA(close, timeperiod=50)
    if not np.isnan(sma_20[-1]) and not np.isnan(sma_50[-1]) and sma_50[-1] != 0:
        sma_ratio = float(sma_20[-1] / sma_50[-1])
    else:
        sma_ratio = float("nan")

    # Bollinger Bands (20, 2)
    upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
    if not np.isnan(upper[-1]) and not np.isnan(lower[-1]) and not np.isnan(middle[-1]) and middle[-1] != 0:
        bb_width = float((upper[-1] - lower[-1]) / middle[-1] * 100)
    else:
        bb_width = float("nan")

    # Close-to-SMA20 percentage
    if not np.isnan(sma_20[-1]) and sma_20[-1] != 0:
        close_to_sma = float((close[-1] - sma_20[-1]) / sma_20[-1] * 100)
    else:
        close_to_sma = float("nan")

    # Volume ratio: 5-period mean / 20-period mean
    vol_5_mean = np.nanmean(tick_volume[-5:])
    vol_20_mean = np.nanmean(tick_volume[-20:])
    if vol_20_mean > 0:
        vol_ratio = float(vol_5_mean / vol_20_mean)
    else:
        vol_ratio = float("nan")

    return {
        "atr_14": atr_14,
        "volatility_20": vol_20,
        "rsi_14": rsi_14,
        "macd": macd_val,
        "macd_signal": macd_sig,
        "adx_14": adx_14,
        "sma_20_50_ratio": sma_ratio,
        "bb_width_pct": bb_width,
        "close_to_sma20_pct": close_to_sma,
        "volume_ratio": vol_ratio,
    }
