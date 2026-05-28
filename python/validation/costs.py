"""Cost models for backtesting: spread, commission, slippage, swap.

All models are pure Python — no MT5 connection required.
Designed for composability: mix and match cost models per symbol.
"""
import logging
from typing import Optional
import pandas as pd
from ..config import (
    DEFAULT_SPREAD_PIPS, COMMISSION_PER_LOT,
    SLIPPAGE_PIPS_MAJORS, SLIPPAGE_PIPS_MINORS,
    PIP_SIZE,
)

logger = logging.getLogger(__name__)

# Majors: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
MAJORS = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"}


class SpreadModel:
    """Base class for spread models. Returns spread in price units per symbol."""
    def get_spread(self, symbol: str, timestamp=None, ohlcv_df=None) -> float:
        raise NotImplementedError


class FixedSpreadModel(SpreadModel):
    """Constant spread per symbol from config DEFAULT_SPREAD_PIPS."""

    def __init__(self, spread_pips: dict[str, float] | None = None):
        self.spread_pips = spread_pips or DEFAULT_SPREAD_PIPS

    def get_spread(self, symbol: str, timestamp=None, ohlcv_df=None) -> float:
        pips = self.spread_pips.get(symbol, 1.5)
        pip_size = PIP_SIZE.get(symbol, 0.0001)
        return pips * pip_size


class HistoricalSpreadModel(SpreadModel):
    """Reads spread from historical OHLCV DataFrame's 'spread' column.

    The MT5 API returns spread in points (not pips). For most forex pairs,
    points = pips * 10 (since 1 pip = 10 points at 5-digit precision).
    """

    def __init__(self, points_to_price: float = 0.00001):
        self.points_to_price = points_to_price

    def get_spread(self, symbol: str, timestamp=None, ohlcv_df=None) -> float:
        if ohlcv_df is None or ohlcv_df.empty:
            return 0.0
        # Use the spread value at the given timestamp or the latest
        if timestamp is not None and 'time' in ohlcv_df.columns:
            row = ohlcv_df[ohlcv_df['time'] == timestamp]
            if not row.empty:
                avg_spread_points = row['spread'].iloc[0]
            else:
                avg_spread_points = ohlcv_df['spread'].mean()
        else:
            avg_spread_points = ohlcv_df['spread'].mean()

        return float(avg_spread_points) * self.points_to_price


class CommissionModel:
    """Base class for commission models. Returns commission cost in account currency."""
    def get_commission(self, symbol: str, volume: float, direction: str) -> float:
        raise NotImplementedError


class PerLotCommissionModel(CommissionModel):
    """Commission per lot traded. Default: $7/lot round-turn ($3.50 per side)."""

    def __init__(self, commission_per_lot: float | None = None):
        self.per_lot = commission_per_lot if commission_per_lot is not None else COMMISSION_PER_LOT

    def get_commission(self, symbol: str, volume: float, direction: str) -> float:
        # Round-turn commission split: half on entry, half on exit.
        # When called with direction, charge entry-side commission.
        # Direction: "buy" or "sell" — both sides pay commission.
        return self.per_lot / 2.0 * volume


class SlippageModel:
    """Base class for slippage models. Returns slippage in pips for a symbol."""
    def get_slippage_pips(self, symbol: str) -> float:
        raise NotImplementedError


class FixedSlippageModel(SlippageModel):
    """Fixed slippage per symbol: majors get tighter slippage than minors/exotics."""

    def __init__(self, majors_pips: float | None = None, minors_pips: float | None = None):
        self.majors_pips = majors_pips if majors_pips is not None else SLIPPAGE_PIPS_MAJORS
        self.minors_pips = minors_pips if minors_pips is not None else SLIPPAGE_PIPS_MINORS

    def get_slippage_pips(self, symbol: str) -> float:
        if symbol in MAJORS:
            return self.majors_pips
        return self.minors_pips


class SwapModel:
    """Base class for swap/rollover models. Returns swap cost for holding overnight."""
    def get_swap(self, symbol: str, volume: float, days_held: int) -> float:
        raise NotImplementedError


class NoSwapModel(SwapModel):
    """No swap charges — default for initial backtesting."""
    def get_swap(self, symbol: str, volume: float, days_held: int) -> float:
        return 0.0


def apply_costs(entry_price: float, exit_price: float, symbol: str,
                volume: float, direction: str,
                spread_model: SpreadModel,
                commission_model: CommissionModel,
                slippage_model: SlippageModel,
                timestamp=None, ohlcv_df=None) -> tuple[float, float, float]:
    """Apply trading costs to entry and exit prices.

    Returns: (adjusted_entry, adjusted_exit, total_costs)

    Entry: price + half_spread + slippage (cost of opening)
    Exit: price - half_spread (cost of closing)
    Total costs: spread + commission + slippage in account currency
    """
    spread = spread_model.get_spread(symbol, timestamp, ohlcv_df)
    half_spread = spread / 2.0
    slippage_pips = slippage_model.get_slippage_pips(symbol)
    slippage_price = slippage_pips * PIP_SIZE.get(symbol, 0.0001)

    # Entry: buy at ask (price + half spread + slippage)
    if direction == "buy":
        adjusted_entry = entry_price + half_spread + slippage_price
        adjusted_exit = exit_price - half_spread
    else:  # sell
        # Sell at bid (price - half spread). Entry via sell = short at bid.
        # For simplicity in backtesting, model as symmetrical:
        adjusted_entry = entry_price - half_spread - slippage_price
        adjusted_exit = exit_price + half_spread

    commission = commission_model.get_commission(symbol, volume, direction) * 2.0  # both sides

    total_costs = spread + slippage_price + commission
    return (adjusted_entry, adjusted_exit, total_costs)
