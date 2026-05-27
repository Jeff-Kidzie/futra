"""Tests for cost models: spread, commission, slippage, swap, and apply_costs().

All tests are pure Python — no MT5 connection required.
"""
import pytest
import pandas as pd
import numpy as np
from python.validation.costs import (
    FixedSpreadModel, HistoricalSpreadModel,
    PerLotCommissionModel, FixedSlippageModel,
    NoSwapModel, apply_costs,
    SpreadModel, CommissionModel, SlippageModel, SwapModel,
)
from python.config import (
    DEFAULT_SPREAD_PIPS, COMMISSION_PER_LOT,
    SLIPPAGE_PIPS_MAJORS, SLIPPAGE_PIPS_MINORS,
    PIP_SIZE,
    DEFAULT_INITIAL_EQUITY,
    WF_IN_SAMPLE_YEARS, WF_OUT_OF_SAMPLE_MONTHS,
    MC_ITERATIONS, MC_CONFIDENCE_LEVEL,
    PAPER_TRADING_INTERVAL_SECONDS,
)


# --- Test 1: FixedSpreadModel ---

class TestFixedSpreadModel:
    def test_eurusd_returns_one_pip(self):
        """FixedSpreadModel.get_spread('EURUSD') returns 1.0 pip in price units.
        
        1 pip = 0.0001 for EURUSD.
        """
        model = FixedSpreadModel({"EURUSD": 1.0})
        result = model.get_spread("EURUSD")
        assert result == 1.0 * 0.0001  # 1 pip * pip size


# --- Test 2: HistoricalSpreadModel ---

class TestHistoricalSpreadModel:
    def test_reads_spread_from_dataframe(self, sample_ohlcv_dataframe_with_spread):
        """HistoricalSpreadModel reads spread from DataFrame's 'spread' column
        and converts from points to price units.
        """
        model = HistoricalSpreadModel(points_to_price=0.00001)
        df = sample_ohlcv_dataframe_with_spread
        result = model.get_spread("EURUSD", ohlcv_df=df)
        # Mean of spread column * points_to_price
        expected = float(df["spread"].mean()) * 0.00001
        assert result == pytest.approx(expected, abs=1e-10)
    
    def test_returns_zero_for_empty_df(self):
        """HistoricalSpreadModel returns 0.0 for empty DataFrame."""
        model = HistoricalSpreadModel()
        result = model.get_spread("EURUSD", ohlcv_df=pd.DataFrame())
        assert result == 0.0
    
    def test_reads_specific_timestamp(self, sample_ohlcv_dataframe_with_spread):
        """HistoricalSpreadModel reads spread at a specific timestamp."""
        model = HistoricalSpreadModel(points_to_price=0.00001)
        df = sample_ohlcv_dataframe_with_spread
        specific_time = df["time"].iloc[50]
        result = model.get_spread("EURUSD", timestamp=specific_time, ohlcv_df=df)
        expected = float(df.iloc[50]["spread"]) * 0.00001
        assert result == pytest.approx(expected, abs=1e-10)


# --- Test 3: PerLotCommissionModel ---

class TestPerLotCommissionModel:
    def test_default_commission_per_lot_round_turn(self):
        """PerLotCommissionModel.get_commission() returns $3.50 for 1 lot EURUSD
        (half of $7 round-turn per side).
        """
        model = PerLotCommissionModel(7.0)
        result = model.get_commission("EURUSD", 1.0, "buy")
        assert result == 3.50  # $7 / 2 per side
    
    def test_commission_scales_with_volume(self):
        """Commission scales linearly with volume."""
        model = PerLotCommissionModel(7.0)
        result_half = model.get_commission("EURUSD", 0.5, "sell")
        assert result_half == 1.75  # $3.50 * 0.5
    
    def test_commission_same_both_sides(self):
        """Commission is the same for buy and sell."""
        model = PerLotCommissionModel(7.0)
        buy_comm = model.get_commission("EURUSD", 1.0, "buy")
        sell_comm = model.get_commission("EURUSD", 1.0, "sell")
        assert buy_comm == sell_comm


# --- Test 4: FixedSlippageModel ---

class TestFixedSlippageModel:
    def test_majors_default_slippage(self):
        """FixedSlippageModel.get_slippage_pips('EURUSD') returns 0.5 pips."""
        model = FixedSlippageModel(0.5, 1.0)
        result = model.get_slippage_pips("EURUSD")
        assert result == 0.5
    
    def test_minors_default_slippage(self):
        """FixedSlippageModel.get_slippage_pips('USDZAR') returns 1.0 pips."""
        model = FixedSlippageModel(0.5, 1.0)
        result = model.get_slippage_pips("USDZAR")
        assert result == 1.0
    
    def test_all_majors_have_tight_slippage(self):
        """All major currency pairs get 0.5 pip slippage."""
        model = FixedSlippageModel(0.5, 1.0)
        majors = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
        for symbol in majors:
            assert model.get_slippage_pips(symbol) == 0.5


# --- Test 5: NoSwapModel ---

class TestNoSwapModel:
    def test_no_swap_returns_zero(self):
        """NoSwapModel.get_swap() always returns 0.0."""
        model = NoSwapModel()
        result = model.get_swap("EURUSD", 1.0, 5)
        assert result == 0.0


# --- Test 6: Config constants ---

class TestConfigConstants:
    def test_all_validation_constants_exist(self):
        """config.py contains all validation constants."""
        # Backtesting
        assert DEFAULT_INITIAL_EQUITY == 10000.0
        # Spread config
        assert DEFAULT_SPREAD_PIPS["EURUSD"] == 1.0
        assert COMMISSION_PER_LOT == 7.0
        assert SLIPPAGE_PIPS_MAJORS == 0.5
        assert SLIPPAGE_PIPS_MINORS == 1.0
        # Pip sizes
        assert PIP_SIZE["EURUSD"] == 0.0001
        assert PIP_SIZE["USDJPY"] == 0.01
        assert PIP_SIZE["XAUUSD"] == 0.10
        # Walk-forward
        assert WF_IN_SAMPLE_YEARS == 2
        assert WF_OUT_OF_SAMPLE_MONTHS == 6
        # Monte Carlo
        assert MC_ITERATIONS == 2000
        assert MC_CONFIDENCE_LEVEL == 0.95
        # Paper trading
        assert PAPER_TRADING_INTERVAL_SECONDS == 3600


# --- Test 7: apply_costs ---

class TestApplyCosts:
    def test_apply_costs_buy_direction(self):
        """apply_costs() with buy direction:
        Entry: price + half_spread + slippage
        Exit: price - half_spread
        total_costs_price: spread + slippage in price units
        total_costs_currency: commission in account currency
        """
        entry = 1.08000
        exit_price = 1.08500
        symbol = "EURUSD"
        volume = 1.0
        
        adj_entry, adj_exit, total_costs_price, total_costs_currency = apply_costs(
            entry_price=entry,
            exit_price=exit_price,
            symbol=symbol,
            volume=volume,
            direction="buy",
            spread_model=FixedSpreadModel({"EURUSD": 1.0}),
            commission_model=PerLotCommissionModel(7.0),
            slippage_model=FixedSlippageModel(0.5, 1.0),
        )
        
        # Spread: 1.0 pips * 0.0001 = 0.0001 price
        # Half spread: 0.00005
        # Slippage: 0.5 pips * 0.0001 = 0.00005 price
        # Adj entry buy: 1.08000 + 0.00005 + 0.00005 = 1.08010
        # Adj exit buy: 1.08500 - 0.00005 = 1.08495
        # Commission: 7.0 / 2 * 1.0 * 2 (both sides) = 7.0
        # total_costs_price: 0.0001 + 0.00005 = 0.00015 (price units)
        # total_costs_currency: 7.0 (account currency)
        
        assert adj_entry == pytest.approx(1.08010, abs=1e-10)
        assert adj_exit == pytest.approx(1.08495, abs=1e-10)
        assert total_costs_price == pytest.approx(0.0001 + 0.00005, abs=1e-10)
        assert total_costs_currency == pytest.approx(7.0, abs=1e-10)
    
    def test_apply_costs_sell_direction(self):
        """apply_costs() with sell direction:
        Entry (sell short): price - half_spread - slippage
        Exit (buy back): price + half_spread
        """
        entry = 1.08500
        exit_price = 1.08000
        symbol = "EURUSD"
        volume = 1.0
        
        adj_entry, adj_exit, total_costs_price, total_costs_currency = apply_costs(
            entry_price=entry,
            exit_price=exit_price,
            symbol=symbol,
            volume=volume,
            direction="sell",
            spread_model=FixedSpreadModel({"EURUSD": 1.0}),
            commission_model=PerLotCommissionModel(7.0),
            slippage_model=FixedSlippageModel(0.5, 1.0),
        )
        
        # Spread: 1.0 pips * 0.0001 = 0.0001 price
        # Half spread: 0.00005
        # Slippage: 0.5 pips * 0.0001 = 0.00005 price
        # Adj entry sell: 1.08500 - 0.00005 - 0.00005 = 1.08490
        # Adj exit sell: 1.08000 + 0.00005 = 1.08005
        
        assert adj_entry == pytest.approx(1.08490, abs=1e-10)
        assert adj_exit == pytest.approx(1.08005, abs=1e-10)

    def test_apply_costs_zero_costs(self):
        """With zero spread, commission, and slippage, prices are unchanged."""
        adj_entry, adj_exit, total_costs_price, total_costs_currency = apply_costs(
            entry_price=1.08000,
            exit_price=1.08500,
            symbol="EURUSD",
            volume=1.0,
            direction="buy",
            spread_model=FixedSpreadModel({"EURUSD": 0.0}),
            commission_model=PerLotCommissionModel(0.0),
            slippage_model=FixedSlippageModel(0.0, 0.0),
        )
        
        assert adj_entry == pytest.approx(1.08000, abs=1e-10)
        assert adj_exit == pytest.approx(1.08500, abs=1e-10)
        assert total_costs_price == pytest.approx(0.0, abs=1e-10)
        assert total_costs_currency == pytest.approx(0.0, abs=1e-10)
