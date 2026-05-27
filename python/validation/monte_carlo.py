"""Monte Carlo simulation — trade-reshuffling bootstrap for strategy robustness.

Bootstraps trade sequences with replacement to generate distributions of
possible outcomes. Answers: "If trades happened in a different order, would
the strategy still work? What if those lucky big wins didn't happen?"

Per BACK-04: Tests strategy robustness across randomized trade sequences.
"""
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Optional

from ..config import MC_ITERATIONS, MC_CONFIDENCE_LEVEL

logger = logging.getLogger(__name__)


class MonteCarlo:
    """Trade-reshuffling bootstrap Monte Carlo simulation.
    
    For each iteration:
    1. Randomly sample trades WITH replacement from the original trade list
    2. Reconstruct an equity curve from the sampled trades
    3. Compute performance metrics on the reconstructed curve
    4. Aggregate statistics across all iterations
    """
    
    def __init__(
        self,
        iterations: int = MC_ITERATIONS,
        initial_equity: float = 10000.0,
        random_seed: Optional[int] = None,
    ):
        self.iterations = iterations
        self.initial_equity = initial_equity
        self.rng = np.random.RandomState(random_seed) if random_seed is not None else np.random.RandomState()
    
    def _reconstruct_equity(self, trades: list[dict]) -> list[tuple]:
        """Build an equity curve from a sequence of trades.
        
        Args:
            trades: List of trade dicts with profit_loss key
        
        Returns:
            List of (index, equity) pairs
        """
        equity = self.initial_equity
        curve = [(0, equity)]
        
        for i, trade in enumerate(trades):
            equity += trade["profit_loss"]
            curve.append((i + 1, equity))
        
        return curve
    
    def _compute_percentile(self, values: np.ndarray, pct: float) -> float:
        """Compute percentile of values."""
        return float(np.percentile(values, pct))
    
    def _compute_metric_stats(self, values: np.ndarray) -> dict:
        """Compute distribution statistics for a metric.
        
        Returns:
            dict with mean, median, pct_5, pct_25, pct_75, pct_95
        """
        return {
            "mean": round(float(np.mean(values)), 4),
            "median": round(float(np.median(values)), 4),
            "pct_5": round(self._compute_percentile(values, 5), 4),
            "pct_25": round(self._compute_percentile(values, 25), 4),
            "pct_75": round(self._compute_percentile(values, 75), 4),
            "pct_95": round(self._compute_percentile(values, 95), 4),
        }
    
    def run(self, trades: list[dict]) -> dict:
        """Run Monte Carlo simulation on a trade list.
        
        Args:
            trades: Original trade list from backtest. Each trade must have 'profit_loss'.
        
        Returns:
            dict with keys: iterations, final_equity, max_drawdown, sharpe_ratio,
            profit_factor, confidence_in_profitability
        """
        if not trades:
            return {
                "iterations": 0,
                "final_equity": {"mean": 0, "median": 0, "pct_5": 0, "pct_25": 0, "pct_75": 0, "pct_95": 0},
                "max_drawdown": {"mean": 0, "median": 0, "pct_5": 0, "pct_25": 0, "pct_75": 0, "pct_95": 0},
                "sharpe_ratio": {"mean": 0, "median": 0, "pct_5": 0, "pct_25": 0, "pct_75": 0, "pct_95": 0},
                "profit_factor": {"mean": 0, "median": 0, "pct_5": 0, "pct_25": 0, "pct_75": 0, "pct_95": 0},
                "confidence_in_profitability": 0.0,
            }
        
        n_trades = len(trades)
        final_equities = np.zeros(self.iterations)
        max_drawdowns = np.zeros(self.iterations)
        mc_sharpe_values = np.zeros(self.iterations)
        mc_pf_values = np.zeros(self.iterations)
        profitable = 0
        
        for i in range(self.iterations):
            # Bootstrap: sample trades WITH replacement
            indices = self.rng.randint(0, n_trades, size=n_trades)
            sampled_trades = [trades[idx] for idx in indices]
            
            # Reconstruct equity curve
            equity_curve = self._reconstruct_equity(sampled_trades)
            equity_values = np.array([e[1] for e in equity_curve])
            
            # Equity metrics
            final_equities[i] = equity_values[-1]
            
            # Max drawdown
            peak = np.maximum.accumulate(equity_values)
            drawdowns = (peak - equity_values) / peak
            max_drawdowns[i] = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
            
            # Profitability
            if equity_values[-1] > self.initial_equity:
                profitable += 1
            
            # Sharpe and PF from same bootstrap sample
            bt_returns = np.array([trades[idx]["profit_loss"] for idx in indices]) / self.initial_equity
            bt_mean = np.mean(bt_returns)
            bt_std = np.std(bt_returns)
            mc_sharpe_values[i] = bt_mean / bt_std * np.sqrt(252) if bt_std > 0 else 0
            
            bt_profits = sum(trades[idx]["profit_loss"] for idx in indices if trades[idx]["profit_loss"] > 0)
            bt_losses = abs(sum(trades[idx]["profit_loss"] for idx in indices if trades[idx]["profit_loss"] < 0))
            mc_pf_values[i] = bt_profits / bt_losses if bt_losses > 0 else float('inf')
        
        # CIP: Confidence in Profitability
        cip = profitable / self.iterations
        
        return {
            "iterations": self.iterations,
            "final_equity": self._compute_metric_stats(final_equities),
            "max_drawdown": self._compute_metric_stats(max_drawdowns),
            "sharpe_ratio": self._compute_metric_stats(mc_sharpe_values),
            "profit_factor": self._compute_metric_stats(mc_pf_values),
            "confidence_in_profitability": round(cip, 4),
        }
