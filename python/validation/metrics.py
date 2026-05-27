"""Financial performance metrics for backtesting results.

All functions are pure: take trades list and equity curve → return metric value.
No external dependencies beyond numpy. No MT5 connection required.

Per BACK-02: Sharpe ratio, Sortino ratio, max drawdown, profit factor,
win rate, average win/loss, total return, Calmar ratio.
"""
import numpy as np
from typing import Optional


def _extract_equity_values(equity_curve: list[tuple]) -> np.ndarray:
    """Extract equity values from (timestamp, equity) pairs."""
    return np.array([e[1] for e in equity_curve], dtype=float)


def _daily_returns(equity_values: np.ndarray) -> np.ndarray:
    """Compute daily returns from equity curve.
    
    Returns normalized to annual using sqrt(252) convention.
    """
    if len(equity_values) < 2:
        return np.array([])
    return np.diff(equity_values) / equity_values[:-1]


def compute_sharpe_ratio(
    equity_curve: list[tuple],
    risk_free_rate: float = 0.04,
    trading_periods_per_year: int = 252,
) -> float:
    """Annualized Sharpe ratio.
    
    Sharpe = (mean(daily_return) - rf_daily) / std(daily_return) * sqrt(periods_per_year)
    
    Args:
        equity_curve: List of (timestamp, equity) pairs
        risk_free_rate: Annual risk-free rate (default: 4%)
        trading_periods_per_year: Number of trading periods per year (default: 252 for daily)
    
    Returns:
        Sharpe ratio. 0.0 if insufficient data or zero volatility.
    """
    equity_values = _extract_equity_values(equity_curve)
    if len(equity_values) < 3:
        return 0.0
    
    returns = _daily_returns(equity_values)
    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0
    
    rf_daily = risk_free_rate / trading_periods_per_year
    excess = np.mean(returns) - rf_daily
    annual_factor = np.sqrt(trading_periods_per_year)
    
    return (excess / np.std(returns)) * annual_factor


def compute_sortino_ratio(
    equity_curve: list[tuple],
    risk_free_rate: float = 0.04,
    trading_periods_per_year: int = 252,
) -> float:
    """Annualized Sortino ratio — uses downside deviation instead of total volatility.
    
    Sortino = (mean(daily_return) - rf_daily) / downside_std * sqrt(periods_per_year)
    
    Returns:
        Sortino ratio. 0.0 if insufficient data or zero downside volatility.
    """
    equity_values = _extract_equity_values(equity_curve)
    if len(equity_values) < 3:
        return 0.0
    
    returns = _daily_returns(equity_values)
    if len(returns) == 0:
        return 0.0
    
    rf_daily = risk_free_rate / trading_periods_per_year
    excess = np.mean(returns) - rf_daily
    
    # Downside deviation: only returns below 0 (or below target)
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0 or np.std(downside_returns) == 0:
        return 0.0 if excess <= 0 else float('inf')
    
    downside_std = np.std(downside_returns)
    annual_factor = np.sqrt(trading_periods_per_year)
    
    return (excess / downside_std) * annual_factor


def compute_max_drawdown(equity_curve: list[tuple]) -> float:
    """Maximum drawdown as a percentage.
    
    MDD = max((peak - trough) / peak) for all peak-to-trough periods.
    
    Returns:
        Max drawdown as decimal (e.g., 0.15 = 15%). 0.0 if empty equity curve.
    """
    equity_values = _extract_equity_values(equity_curve)
    if len(equity_values) == 0:
        return 0.0
    
    peak = np.maximum.accumulate(equity_values)
    drawdowns = (peak - equity_values) / peak
    
    return float(np.max(drawdowns))


def compute_profit_factor(trades: list[dict]) -> float:
    """Profit factor = gross profit / |gross loss|.
    
    Returns:
        Profit factor. float('inf') if no losses (all wins). 0.0 if no trades.
    """
    if not trades:
        return 0.0
    
    profits = [t["profit_loss"] for t in trades if t["profit_loss"] > 0]
    losses = [abs(t["profit_loss"]) for t in trades if t["profit_loss"] < 0]
    
    if sum(losses) == 0:
        return float('inf') if sum(profits) > 0 else 0.0
    
    return sum(profits) / sum(losses)


def compute_win_rate(trades: list[dict]) -> float:
    """Win rate = winning trades / total trades.
    
    Returns:
        Win rate as decimal (e.g., 0.45 = 45%). 0.0 if no trades.
    """
    if not trades:
        return 0.0
    
    wins = sum(1 for t in trades if t["profit_loss"] > 0)
    return wins / len(trades)


def compute_avg_win_loss(trades: list[dict]) -> float:
    """Average win / average loss ratio.
    
    Returns:
        Ratio of mean(win_size) / |mean(loss_size)|.
        float('inf') if no losses. 0.0 if no wins. 0.0 if no trades.
    """
    if not trades:
        return 0.0
    
    wins = [t["profit_loss"] for t in trades if t["profit_loss"] > 0]
    losses = [abs(t["profit_loss"]) for t in trades if t["profit_loss"] < 0]
    
    if not wins:
        return 0.0
    if not losses:
        return float('inf') if wins else 0.0
    
    return np.mean(wins) / np.mean(losses)


def compute_total_return(equity_curve: list[tuple]) -> float:
    """Total return as a percentage.
    
    Returns:
        Total return as decimal (e.g., 0.15 = 15%). 0.0 if empty equity curve.
    """
    if not equity_curve:
        return 0.0
    
    start_equity = equity_curve[0][1]
    end_equity = equity_curve[-1][1]
    
    if start_equity == 0:
        return 0.0
    
    return (end_equity - start_equity) / start_equity


def compute_calmar_ratio(equity_curve: list[tuple]) -> float:
    """Calmar ratio = annualized return / max drawdown.
    
    Returns:
        Calmar ratio. 0.0 if max drawdown is 0 (no decline) or insufficient data.
        float('inf') if positive return with zero drawdown (unrealistic).
    """
    total_return = compute_total_return(equity_curve)
    max_dd = compute_max_drawdown(equity_curve)
    
    if max_dd == 0:
        return float('inf') if total_return > 0 else 0.0
    
    # Annualize return: approximate from total return
    # Assume equity_curve ~ 1 year of data if not specified
    annualized_return = total_return  # Simplified — Phase 4 can add precise duration
    
    return annualized_return / max_dd


def compute_all_metrics(
    trades: list[dict],
    equity_curve: list[tuple],
    risk_free_rate: float = 0.04,
    trading_periods_per_year: int = 252,
) -> dict[str, float]:
    """Compute all performance metrics in one pass.
    
    Args:
        trades: List of trade dicts with profit_loss key
        equity_curve: List of (timestamp, equity) pairs
        risk_free_rate: Annual risk-free rate (default: 4%)
        trading_periods_per_year: Periods per year for annualization (default: 252 daily)
    
    Returns:
        Dict with keys: sharpe_ratio, sortino_ratio, max_drawdown, profit_factor,
        win_rate, avg_win_loss, total_return, calmar_ratio, total_trades
    """
    pf = compute_profit_factor(trades)
    awl = compute_avg_win_loss(trades)
    cr = compute_calmar_ratio(equity_curve)
    
    return {
        "sharpe_ratio": round(compute_sharpe_ratio(equity_curve, risk_free_rate, trading_periods_per_year), 4),
        "sortino_ratio": round(compute_sortino_ratio(equity_curve, risk_free_rate, trading_periods_per_year), 4),
        "max_drawdown": round(compute_max_drawdown(equity_curve), 4),
        "profit_factor": None if pf == float('inf') else round(pf, 4),
        "win_rate": round(compute_win_rate(trades), 4),
        "avg_win_loss": None if awl == float('inf') else round(awl, 4),
        "total_return": round(compute_total_return(equity_curve), 4),
        "calmar_ratio": None if cr == float('inf') else round(cr, 4),
        "total_trades": len(trades),
    }
