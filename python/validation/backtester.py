"""Bar-level backtesting engine — simulates EA trade execution with AI parameters.

Replays historical OHLCV data through the AI pipeline (features → regime → adapted params)
and simulates what the EA would have done: open positions at bar close with SL/TP,
close on SL/TP hits or max holding period, enforce risk gates.

Per D-11: Fully testable with mock DataFrames — no MT5 connection required.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
import numpy as np

from ..config import PIP_SIZE, DEFAULT_INITIAL_EQUITY
from .costs import (
    SpreadModel, CommissionModel, SlippageModel, SwapModel,
    FixedSpreadModel, PerLotCommissionModel, FixedSlippageModel, NoSwapModel,
    apply_costs,
)

logger = logging.getLogger(__name__)


class Backtester:
    """Bar-level simulation of EA trade execution with AI parameter adaptation.
    
    Simulates the EA's OnTick/OnBar logic:
    1. Check SL/TP on open positions (did price touch SL/TP this bar?)
    2. Close positions where SL/TP triggered
    3. Generate AI signal (features → regime → adapted params)
    4. Run risk gates (drawdown, daily loss, position count)
    5. Open new position if gates pass
    6. Record equity snapshot
    """
    
    def __init__(
        self,
        initial_equity: float = DEFAULT_INITIAL_EQUITY,
        max_drawdown_pct: float = 0.20,       # 20% max drawdown from peak
        daily_loss_cap_pct: float = 0.05,      # 5% daily loss cap
        max_positions_per_symbol: int = 1,     # 1 position per symbol max
        max_bars_held: int = 48,               # Max bars to hold a position (H1 -> 2 days)
        spread_model: SpreadModel | None = None,
        commission_model: CommissionModel | None = None,
        slippage_model: SlippageModel | None = None,
        swap_model: SwapModel | None = None,
    ):
        self.initial_equity = initial_equity
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_cap_pct = daily_loss_cap_pct
        self.max_positions_per_symbol = max_positions_per_symbol
        self.max_bars_held = max_bars_held
        
        self.spread_model = spread_model or FixedSpreadModel()
        self.commission_model = commission_model or PerLotCommissionModel()
        self.slippage_model = slippage_model or FixedSlippageModel()
        self.swap_model = swap_model or NoSwapModel()
        
        # Internal state — reset on each run()
        self._reset()
    
    def _reset(self):
        self.equity = self.initial_equity
        self.peak_equity = self.initial_equity
        self.daily_loss = 0.0
        self.current_day = None
        self.positions: list[dict] = []       # Open positions
        self.closed_trades: list[dict] = []    # Closed trades
        self.equity_curve: list[tuple] = []    # (timestamp, equity) pairs
    
    def _check_sl_tp(self, pos: dict, bar: pd.Series) -> Optional[float]:
        """Check if SL or TP was hit during this bar.
        
        Args:
            pos: Position dict with sl_price, tp_price, direction
            bar: OHLC bar Series with open, high, low, close
        
        Returns:
            Exit price if SL/TP hit, None if position stays open
        """
        sl_price = pos["sl_price"]
        tp_price = pos["tp_price"]
        direction = pos["direction"]
        
        sl_hit = False
        tp_hit = False
        
        if direction == "buy":
            # Long: SL below entry, TP above entry
            sl_hit = sl_price is not None and bar["low"] <= sl_price
            tp_hit = tp_price is not None and bar["high"] >= tp_price
        else:  # sell
            # Short: SL above entry, TP below entry
            sl_hit = sl_price is not None and bar["high"] >= sl_price
            tp_hit = tp_price is not None and bar["low"] <= tp_price
        
        if sl_hit and tp_hit:
            # Both hit — use bar direction to determine order
            # Down bar (close < open) -> SL hit first for longs, TP first for shorts
            if direction == "buy":
                return sl_price if bar["close"] < bar["open"] else tp_price
            else:
                return tp_price if bar["close"] < bar["open"] else sl_price
        elif sl_hit:
            return sl_price
        elif tp_hit:
            return tp_price
        
        return None
    
    def _compute_pnl(self, pos: dict, exit_price: float) -> float:
        """Compute profit/loss for a closed position in account currency."""
        entry_price = pos["entry_price"]
        lot_size = pos["lot_size"]
        direction = pos["direction"]
        
        pip_size = PIP_SIZE.get(pos["symbol"], 0.0001)
        
        if direction == "buy":
            pips = (exit_price - entry_price) / pip_size
        else:
            pips = (entry_price - exit_price) / pip_size
        
        # Standard lot = 100,000 units. P&L per pip per lot approx $10 for forex.
        pip_value = 10.0  # USD per pip per standard lot
        pnl = pips * pip_value * lot_size
        return round(pnl, 2)
    
    def _is_trading_allowed(self, symbol: str, volume: float) -> bool:
        """Simulate EA's IsTradingAllowed() risk gate.
        
        Mirrors ea/include/RiskManager.mqh IsTradingAllowed() logic:
        1. Drawdown check (equity vs peak equity)
        2. Daily loss check (cumulative daily loss vs cap)
        3. Max positions per symbol check
        """
        # Drawdown check
        drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if drawdown > self.max_drawdown_pct:
            return False
        
        # Daily loss check
        daily_loss_pct = abs(self.daily_loss) / self.initial_equity
        if daily_loss_pct > self.daily_loss_cap_pct:
            return False
        
        # Max positions per symbol
        symbol_positions = [p for p in self.positions if p["symbol"] == symbol]
        if len(symbol_positions) >= self.max_positions_per_symbol:
            return False
        
        return True
    
    def run(
        self,
        ohlcv_df: pd.DataFrame,
        symbol: str,
        regime_detector,
        parameter_adapter,
        compute_features_fn,
    ) -> dict:
        """Run backtest on historical OHLCV data.
        
        Args:
            ohlcv_df: DataFrame with columns time, open, high, low, close, tick_volume, spread
            symbol: Trading symbol (e.g., "EURUSD")
            regime_detector: RegimeDetector instance
            parameter_adapter: ParameterAdapter instance
            compute_features_fn: compute_features function
        
        Returns:
            dict with keys: trades, equity_curve, final_equity
        """
        self._reset()
        
        bars = ohlcv_df.reset_index(drop=True)
        min_warmup = 50  # Minimum bars needed for feature computation
        
        for i in range(len(bars)):
            bar = bars.iloc[i]
            timestamp = bar["time"] if "time" in bars.columns else datetime.now(timezone.utc)
            
            # Reset daily loss tracking on new day
            bar_date = timestamp.date() if hasattr(timestamp, 'date') else None
            if bar_date and bar_date != self.current_day:
                self.current_day = bar_date
                self.daily_loss = 0.0
            
            # 1. Process open positions — check SL/TP
            for pos in self.positions[:]:  # Copy list for safe removal
                exit_price = self._check_sl_tp(pos, bar)
                if exit_price:
                    # Close position
                    pnl = self._compute_pnl(pos, exit_price)
                    # Apply commission for exit side
                    exit_commission = self.commission_model.get_commission(
                        symbol, pos["lot_size"], pos["direction"])
                    pnl -= exit_commission
                    
                    self._close_position(pos, exit_price, pnl, timestamp, "sl_tp")
                
                # Check max holding period
                elif pos["bars_held"] >= self.max_bars_held:
                    exit_price = bar["close"]
                    pnl = self._compute_pnl(pos, exit_price)
                    exit_commission = self.commission_model.get_commission(
                        symbol, pos["lot_size"], pos["direction"])
                    pnl -= exit_commission
                    
                    self._close_position(pos, exit_price, pnl, timestamp, "max_hold")
            
            # 2. Generate AI signal (only after warmup)
            if i >= min_warmup:
                try:
                    df_slice = bars.iloc[:i+1]
                    features = compute_features_fn(df_slice)
                    regime, confidence = regime_detector.predict(features)
                    volatility = features.get("volatility_20", None)
                    atr = features.get("atr_14", None)
                    
                    adapted = parameter_adapter.adapt(
                        regime=regime,
                        confidence=confidence,
                        volatility=volatility,
                        atr_pips=atr,
                        equity=self.equity,
                    )
                    
                    sl_pips = adapted["sl_pips"]
                    tp_pips = adapted["tp_pips"]
                    lot_size = adapted["lot_size"]
                    
                    # 3. Risk gates
                    if self._is_trading_allowed(symbol, lot_size):
                        # 4. Open position at bar close + costs
                        entry_price_raw = bar["close"]
                        direction = "buy"  # Always long for initial backtest
                        
                        adjusted_entry, _, _ = apply_costs(
                            entry_price=entry_price_raw,
                            exit_price=entry_price_raw,  # Not used for entry calc
                            symbol=symbol,
                            volume=lot_size,
                            direction=direction,
                            spread_model=self.spread_model,
                            commission_model=self.commission_model,
                            slippage_model=self.slippage_model,
                            timestamp=timestamp,
                            ohlcv_df=bars.iloc[:i+1],
                        )
                        
                        # Apply entry commission
                        entry_commission = self.commission_model.get_commission(
                            symbol, lot_size, direction)
                        self.equity -= entry_commission
                        self.daily_loss += entry_commission
                        
                        pip_size = PIP_SIZE.get(symbol, 0.0001)
                        sl_price = adjusted_entry - sl_pips * pip_size
                        tp_price = adjusted_entry + tp_pips * pip_size
                        
                        pos = {
                            "symbol": symbol,
                            "direction": direction,
                            "entry_price": adjusted_entry,
                            "entry_time": timestamp,
                            "sl_price": sl_price,
                            "tp_price": tp_price,
                            "lot_size": lot_size,
                            "sl_pips": sl_pips,
                            "tp_pips": tp_pips,
                            "regime": regime,
                            "confidence": confidence,
                            "bars_held": 0,
                        }
                        self.positions.append(pos)
                        
                except Exception as e:
                    logger.warning(f"AI signal error at bar {i}: {e}")
            
            # 5. Update equity curve (always — even during warmup)
            # Equity = cash + realized P&L. No unrealized P&L tracking for simplicity.
            self.equity_curve.append((timestamp, self.equity))
            
            # 6. Increment bars_held for open positions
            for pos in self.positions:
                pos["bars_held"] += 1
        
        # Close any remaining open positions at last bar's close
        for pos in self.positions[:]:
            last_bar = bars.iloc[-1]
            exit_price = last_bar["close"]
            pnl = self._compute_pnl(pos, exit_price)
            self._close_position(pos, exit_price, pnl,
                                last_bar.get("time", None), "end_of_test")
        
        return {
            "trades": self.closed_trades,
            "equity_curve": self.equity_curve,
            "final_equity": self.equity,
        }
    
    def _close_position(self, pos, exit_price, pnl, timestamp, reason):
        """Close a position and record the trade."""
        self.equity += pnl
        if pnl < 0:
            self.daily_loss += abs(pnl)
        
        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        trade = {
            "symbol": pos["symbol"],
            "direction": pos["direction"],
            "entry_time": pos["entry_time"],
            "exit_time": timestamp,
            "entry_price": pos["entry_price"],
            "exit_price": exit_price,
            "sl_pips": pos["sl_pips"],
            "tp_pips": pos["tp_pips"],
            "lot_size": pos["lot_size"],
            "profit_loss": pnl,
            "regime": pos["regime"],
            "confidence": pos["confidence"],
            "exit_reason": reason,
        }
        self.closed_trades.append(trade)
        self.positions.remove(pos)
