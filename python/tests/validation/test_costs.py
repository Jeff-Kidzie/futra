"""Test cost models: spread, commission, slippage, and apply_costs() composition.

TDD RED phase — all tests expect python/validation/costs.py to exist
with the classes and functions specified in 03-01-PLAN.md.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from python.validation.costs import (
    FixedSpreadModel,
    HistoricalSpreadModel,
    PerLotCommissionModel,
    FixedSlippageModel,
    NoSwapModel,
    apply_costs,
)
from python.config import (
    DEFAULT_INITIAL_EQUITY,
    DEFAULT_SPREAD_PIPS,
    COMMISSION_PER_LOT,
    SLIPPAGE_PIPS_MAJORS,
    SLIPPAGE_PIPS_MINORS,
    PIP_SIZE,
    WF_IN_SAMPLE_YEARS,
    WF_OUT_OF_SAMPLE_MONTHS,
    WF_MIN_OOS_TRADES,
    MC_ITERATIONS,
    MC_CONFIDENCE_LEVEL,
    PAPER_TRADING_INTERVAL_SECONDS,
    MT5_DEMO_LOGIN,
    MT5_DEMO_PASSWORD,
    MT5_DEMO_SERVER,
)


# ── Test 1: FixedSpreadModel.get_spread("EURUSD") returns 1.0 pips ────

def test_fixed_spread_eurusd_returns_1_pip():
    """EURUSD spread = 1.0 pips * 0.0001 = 0.0001 in price units."""
    model = FixedSpreadModel()
    spread = model.get_spread("EURUSD")
    assert spread == pytest.approx(0.0001, rel=1e-6)  # 1.0 pips * 0.0001


def test_fixed_spread_usdjpy_uses_correct_pip_size():
    """USDJPY spread = 1.5 pips * 0.01 = 0.015 in price units."""
    model = FixedSpreadModel()
    spread = model.get_spread("USDJPY")
    assert spread == pytest.approx(0.015, rel=1e-6)  # 1.5 pips * 0.01


def test_fixed_spread_unknown_symbol_uses_default():
    """Unknown symbol falls back to 1.5 pips with standard pip size 0.0001."""
    model = FixedSpreadModel()
    spread = model.get_spread("UNKNOWN")
    assert spread == pytest.approx(0.00015, rel=1e-6)  # 1.5 pips * 0.0001


def test_fixed_spread_custom_spread_dict():
    """Custom spread dict overrides config defaults."""
    model = FixedSpreadModel({"EURUSD": 2.0, "USDJPY": 3.0})
    assert model.get_spread("EURUSD") == pytest.approx(0.0002, rel=1e-6)
    assert model.get_spread("USDJPY") == pytest.approx(0.03, rel=1e-6)


# ── Test 2: HistoricalSpreadModel reads spread from OHLCV DataFrame ────

def test_historical_spread_from_dataframe(sample_ohlcv_dataframe_with_spread):
    """Reads average spread from the DataFrame's 'spread' column."""
    model = HistoricalSpreadModel()
    df = sample_ohlcv_dataframe_with_spread
    spread = model.get_spread("EURUSD", ohlcv_df=df)
    # Average spread in points (8-15 range) * 0.00001 points_to_price
    expected_mean_points = df["spread"].mean()
    expected = expected_mean_points * 0.00001
    assert spread == pytest.approx(expected, rel=1e-6)
    assert spread > 0  # Must be positive


def test_historical_spread_empty_dataframe_returns_zero():
    """Empty DataFrame returns 0.0 spread."""
    model = HistoricalSpreadModel()
    spread = model.get_spread("EURUSD", ohlcv_df=pd.DataFrame())
    assert spread == 0.0


def test_historical_spread_with_timestamp(sample_ohlcv_dataframe_with_spread):
    """Specific timestamp looks up that bar's spread."""
    model = HistoricalSpreadModel()
    df = sample_ohlcv_dataframe_with_spread
    target_time = df["time"].iloc[10]
    spread_at_time = model.get_spread("EURUSD", timestamp=target_time, ohlcv_df=df)
    expected = df["spread"].iloc[10] * 0.00001
    assert spread_at_time == pytest.approx(expected, rel=1e-6)


# ── Test 3: PerLotCommissionModel ────

def test_per_lot_commission_default():
    """Default: $7/lot round-turn, so $3.50 per side * volume."""
    model = PerLotCommissionModel()
    commission = model.get_commission("EURUSD", 1.0, "buy")
    assert commission == pytest.approx(3.50, rel=1e-6)  # 7.0 / 2 * 1.0


def test_per_lot_commission_fractional_volume():
    """0.01 lot = $0.035 per side."""
    model = PerLotCommissionModel()
    commission = model.get_commission("EURUSD", 0.01, "buy")
    assert commission == pytest.approx(0.035, rel=1e-6)  # 3.50 * 0.01


def test_per_lot_commission_custom_rate():
    """Custom commission rate (e.g., $10/lot round-turn)."""
    model = PerLotCommissionModel(commission_per_lot=10.0)
    commission = model.get_commission("EURUSD", 1.0, "sell")
    assert commission == pytest.approx(5.0, rel=1e-6)  # 10.0 / 2


# ── Test 4: FixedSlippageModel ────

def test_fixed_slippage_major_default():
    """Major pairs (EURUSD) get 0.5 pips slippage."""
    model = FixedSlippageModel()
    assert model.get_slippage_pips("EURUSD") == 0.5
    assert model.get_slippage_pips("GBPUSD") == 0.5
    assert model.get_slippage_pips("USDJPY") == 0.5


def test_fixed_slippage_minor_default():
    """Minor pairs get 1.0 pips slippage."""
    model = FixedSlippageModel()
    assert model.get_slippage_pips("USDZAR") == 1.0
    assert model.get_slippage_pips("EURTRY") == 1.0
    assert model.get_slippage_pips("GBPNZD") == 1.0


def test_fixed_slippage_custom_values():
    """Custom slippage values for majors and minors."""
    model = FixedSlippageModel(majors_pips=0.3, minors_pips=2.0)
    assert model.get_slippage_pips("EURUSD") == 0.3
    assert model.get_slippage_pips("USDZAR") == 2.0


# ── Test 5: NoSwapModel always returns 0 ────

def test_no_swap_always_zero():
    """NoSwapModel returns 0 for any input."""
    model = NoSwapModel()
    assert model.get_swap("EURUSD", 1.0, 1) == 0.0
    assert model.get_swap("EURUSD", 0.01, 30) == 0.0
    assert model.get_swap("GBPUSD", 5.0, 365) == 0.0


# ── Test 6: config.py contains all validation constants ────

def test_validation_config_constants():
    """Verify all validation-related constants are present in config.py."""
    assert isinstance(DEFAULT_INITIAL_EQUITY, float)
    assert DEFAULT_INITIAL_EQUITY == 10000.0
    assert isinstance(DEFAULT_SPREAD_PIPS, dict)
    assert "EURUSD" in DEFAULT_SPREAD_PIPS
    assert DEFAULT_SPREAD_PIPS["EURUSD"] == 1.0
    assert isinstance(COMMISSION_PER_LOT, float)
    assert COMMISSION_PER_LOT == 7.0
    assert isinstance(SLIPPAGE_PIPS_MAJORS, float)
    assert SLIPPAGE_PIPS_MAJORS == 0.5
    assert isinstance(SLIPPAGE_PIPS_MINORS, float)
    assert SLIPPAGE_PIPS_MINORS == 1.0
    
    # PIP_SIZE dict
    assert isinstance(PIP_SIZE, dict)
    assert PIP_SIZE["EURUSD"] == 0.0001
    assert PIP_SIZE["USDJPY"] == 0.01
    assert PIP_SIZE["XAUUSD"] == 0.10
    
    # Walk-forward config
    assert isinstance(WF_IN_SAMPLE_YEARS, int)
    assert WF_IN_SAMPLE_YEARS == 2
    assert isinstance(WF_OUT_OF_SAMPLE_MONTHS, int)
    assert WF_OUT_OF_SAMPLE_MONTHS == 6
    assert isinstance(WF_MIN_OOS_TRADES, int)
    assert WF_MIN_OOS_TRADES == 10
    
    # Monte Carlo config
    assert isinstance(MC_ITERATIONS, int)
    assert MC_ITERATIONS == 2000
    assert isinstance(MC_CONFIDENCE_LEVEL, float)
    assert MC_CONFIDENCE_LEVEL == 0.95
    
    # Paper trading config
    assert isinstance(PAPER_TRADING_INTERVAL_SECONDS, int)
    assert PAPER_TRADING_INTERVAL_SECONDS == 3600
    assert isinstance(MT5_DEMO_LOGIN, int)
    assert isinstance(MT5_DEMO_PASSWORD, str)
    assert isinstance(MT5_DEMO_SERVER, str)


# ── Test 7: apply_costs() composability ────

def test_apply_costs_buy_entry():
    """Buy entry: price + half_spread + slippage. Exit: price - half_spread."""
    spread_model = FixedSpreadModel()
    commission_model = PerLotCommissionModel()
    slippage_model = FixedSlippageModel()
    
    adjusted_entry, adjusted_exit, total_costs = apply_costs(
        entry_price=1.08500,
        exit_price=1.08600,
        symbol="EURUSD",
        volume=0.01,
        direction="buy",
        spread_model=spread_model,
        commission_model=commission_model,
        slippage_model=slippage_model,
    )
    
    # Spread: 1.0 pips = 0.0001, half = 0.00005
    # Slippage: 0.5 pips = 0.00005
    # Entry: 1.08500 + 0.00005 + 0.00005 = 1.08510
    assert adjusted_entry == pytest.approx(1.08510, rel=1e-6)
    # Exit: 1.08600 - 0.00005 = 1.08595
    assert adjusted_exit == pytest.approx(1.08595, rel=1e-6)
    # Total costs: spread + slippage + both-sides commission
    # spread = 0.0001, slippage = 0.00005, commission = 0.035 * 2 = 0.07
    assert total_costs == pytest.approx(0.0001 + 0.00005 + 0.07, rel=1e-6)


def test_apply_costs_sell_entry():
    """Sell entry: price - half_spread - slippage. Exit: price + half_spread."""
    spread_model = FixedSpreadModel()
    commission_model = PerLotCommissionModel()
    slippage_model = FixedSlippageModel()
    
    adjusted_entry, adjusted_exit, total_costs = apply_costs(
        entry_price=1.08500,
        exit_price=1.08400,
        symbol="EURUSD",
        volume=1.0,
        direction="sell",
        spread_model=spread_model,
        commission_model=commission_model,
        slippage_model=slippage_model,
    )
    
    # Sell: entry = 1.08500 - 0.00005 - 0.00005 = 1.08490
    assert adjusted_entry == pytest.approx(1.08490, rel=1e-6)
    # Exit: 1.08400 + 0.00005 = 1.08405
    assert adjusted_exit == pytest.approx(1.08405, rel=1e-6)
    # Total costs with 1.0 lot: commission = 3.50 * 2 = 7.00
    assert total_costs == pytest.approx(0.0001 + 0.00005 + 7.0, rel=1e-6)
