"""Walk-forward validation — anchored expanding-window strategy evaluation.

Splits historical data into overlapping windows: each window has an in-sample
training period and an out-of-sample validation period. The in-sample period
grows (anchored at the start), while the out-of-sample window slides forward.

Per BACK-03: Proves the strategy generalizes beyond training data.
Per PITFALLS.md #1: Strict IS/OOS separation prevents overfitting.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from ..config import WF_IN_SAMPLE_YEARS, WF_OUT_OF_SAMPLE_MONTHS, WF_MIN_OOS_TRADES
from .metrics import compute_all_metrics

logger = logging.getLogger(__name__)


class WalkForward:
    """Anchored expanding-window walk-forward validation.
    
    Each window has:
    - In-sample: from data start to (start + in_sample_period + k * oos_period)
    - Out-of-sample: the next oos_period after in-sample ends
    
    The in-sample grows (anchored at data start); out-of-sample slides forward.
    """
    
    def __init__(
        self,
        in_sample_years: float = WF_IN_SAMPLE_YEARS,
        out_of_sample_months: int = WF_OUT_OF_SAMPLE_MONTHS,
        min_oos_trades: int = WF_MIN_OOS_TRADES,
        min_sharpe: float = 0.5,
        min_profit_factor: float = 1.2,
        max_drawdown: float = 0.25,
    ):
        self.in_sample_years = in_sample_years
        self.out_of_sample_months = out_of_sample_months
        self.min_oos_trades = min_oos_trades
        self.min_sharpe = min_sharpe
        self.min_profit_factor = min_profit_factor
        self.max_drawdown = max_drawdown
    
    def _generate_windows(self, ohlcv_df: pd.DataFrame) -> list[dict]:
        """Generate anchored expanding windows from OHLCV data.
        
        Args:
            ohlcv_df: DataFrame with 'time' column (datetime)
        
        Returns:
            List of dicts: {"index": int, "is_start": datetime, "is_end": datetime,
                           "oos_start": datetime, "oos_end": datetime}
        """
        if ohlcv_df.empty or 'time' not in ohlcv_df.columns:
            return []
        
        start_date = ohlcv_df['time'].min()
        end_date = ohlcv_df['time'].max()
        
        if pd.isna(start_date) or pd.isna(end_date):
            return []
        
        in_sample_days = int(self.in_sample_years * 365.25)
        oos_days = int(self.out_of_sample_months * 30.44)
        
        windows = []
        window_index = 0
        is_end_date = start_date + timedelta(days=in_sample_days)
        
        while True:
            oos_start = is_end_date
            oos_end = oos_start + timedelta(days=oos_days)
            
            if oos_end > end_date:
                break  # Not enough data for another OOS window
            
            windows.append({
                "index": window_index,
                "is_start": start_date,
                "is_end": is_end_date,
                "oos_start": oos_start,
                "oos_end": oos_end,
            })
            
            window_index += 1
            is_end_date = oos_end  # Expanding: IS now includes previous OOS
        
        return windows
    
    def _filter_by_date(self, ohlcv_df: pd.DataFrame,
                        start: datetime, end: datetime) -> pd.DataFrame:
        """Filter DataFrame to rows between start and end dates."""
        mask = (ohlcv_df['time'] >= start) & (ohlcv_df['time'] < end)
        return ohlcv_df[mask].copy()
    
    def run(
        self,
        ohlcv_df: pd.DataFrame,
        symbol: str,
        backtester,           # Backtester instance
        regime_detector,      # RegimeDetector instance
        parameter_adapter,    # ParameterAdapter instance
        compute_features_fn,  # compute_features function
    ) -> dict:
        """Run walk-forward validation across all windows.
        
        Args:
            ohlcv_df: Full historical OHLCV DataFrame
            symbol: Trading symbol
            backtester: Backtester instance (reused across windows)
            regime_detector: RegimeDetector instance
            parameter_adapter: ParameterAdapter instance
            compute_features_fn: Feature computation function
        
        Returns:
            dict with keys: windows (list), aggregate (dict), passed (bool)
        """
        windows = self._generate_windows(ohlcv_df)
        
        if not windows:
            return {
                "windows": [],
                "aggregate": {},
                "passed": False,
                "error": "Insufficient data for walk-forward windows",
            }
        
        results = []
        for w in windows:
            is_df = self._filter_by_date(ohlcv_df, w["is_start"], w["is_end"])
            oos_df = self._filter_by_date(ohlcv_df, w["oos_start"], w["oos_end"])
            
            # Run backtest on in-sample
            is_result = backtester.run(
                is_df, symbol, regime_detector, parameter_adapter, compute_features_fn
            )
            is_metrics = compute_all_metrics(is_result["trades"], is_result["equity_curve"])
            
            # Run backtest on out-of-sample
            oos_result = backtester.run(
                oos_df, symbol, regime_detector, parameter_adapter, compute_features_fn
            )
            oos_metrics = compute_all_metrics(oos_result["trades"], oos_result["equity_curve"])
            
            # IS/OOS Sharpe ratio (overfitting indicator)
            is_sharpe = is_metrics.get("sharpe_ratio", 0) or 0
            oos_sharpe = oos_metrics.get("sharpe_ratio", 0) or 0
            is_oos_ratio = is_sharpe / oos_sharpe if oos_sharpe != 0 else float('inf')
            
            # Warning: insufficient OOS trades
            oos_trades = oos_metrics.get("total_trades", 0) or 0
            warning = None
            if oos_trades < self.min_oos_trades:
                warning = f"Only {oos_trades} OOS trades (min {self.min_oos_trades})"
            
            results.append({
                "window_index": w["index"],
                "is_start": w["is_start"],
                "is_end": w["is_end"],
                "oos_start": w["oos_start"],
                "oos_end": w["oos_end"],
                "is_metrics": is_metrics,
                "oos_metrics": oos_metrics,
                "is_oos_sharpe_ratio": round(is_oos_ratio, 4),
                "oos_trades": oos_trades,
                "warning": warning,
            })
        
        # Aggregate metrics across all OOS windows
        oos_sharpes = [r["oos_metrics"].get("sharpe_ratio", 0) or 0 for r in results]
        oos_pfs = [r["oos_metrics"].get("profit_factor", 0) or 0 for r in results
                   if r["oos_metrics"].get("profit_factor") is not None]
        oos_drawdowns = [r["oos_metrics"].get("max_drawdown", 0) or 0 for r in results]
        is_oos_ratios = [r["is_oos_sharpe_ratio"] for r in results
                         if r["is_oos_sharpe_ratio"] != float('inf')]
        
        mean_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0
        mean_oos_pf = sum(oos_pfs) / len(oos_pfs) if oos_pfs else 0
        worst_dd = max(oos_drawdowns) if oos_drawdowns else 1.0
        mean_is_oos = sum(is_oos_ratios) / len(is_oos_ratios) if is_oos_ratios else float('inf')
        
        aggregate = {
            "num_windows": len(results),
            "mean_oos_sharpe": round(mean_oos_sharpe, 4),
            "mean_oos_profit_factor": round(mean_oos_pf, 4),
            "worst_window_drawdown": round(worst_dd, 4),
            "mean_is_oos_sharpe_ratio": round(mean_is_oos, 4),
            "oos_sharpes": oos_sharpes,
            "oos_profit_factors": oos_pfs,
        }
        
        # Pass/fail criteria
        passed = (
            mean_oos_sharpe >= self.min_sharpe and
            mean_oos_pf >= self.min_profit_factor and
            worst_dd <= self.max_drawdown
        )
        
        return {
            "windows": results,
            "aggregate": aggregate,
            "passed": passed,
        }
