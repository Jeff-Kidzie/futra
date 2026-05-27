---
phase: 03-validation
reviewed: 2026-05-27T12:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - python/validation/__init__.py
  - python/validation/costs.py
  - python/validation/backtester.py
  - python/validation/metrics.py
  - python/validation/walk_forward.py
  - python/validation/monte_carlo.py
  - python/validation/paper_trading.py
  - python/config.py
  - python/tests/validation/__init__.py
  - python/tests/validation/conftest.py
  - python/tests/validation/test_costs.py
  - python/tests/validation/test_backtester.py
  - python/tests/validation/test_metrics.py
  - python/tests/validation/test_walk_forward.py
  - python/tests/validation/test_monte_carlo.py
  - python/tests/validation/test_paper_trading.py
findings:
  critical: 2
  warning: 5
  info: 2
  total: 9
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-27T12:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Reviewed the complete validation subsystem: cost models, backtesting engine, performance metrics, walk-forward validation, Monte Carlo simulation, paper trading scheduler, and all associated tests plus config.

The code is well-structured with clear separation of concerns and good test coverage. However, two **BLOCKER** issues were found: (1) the Sortino ratio uses an incorrect downside deviation formula that will produce misleading financial metrics, and (2) the backtester fails to charge exit commission on end-of-test position closes, inflating reported P&L. Five warnings cover dimensional inconsistency in cost reporting, an off-by-one in max holding period enforcement, dead code and incoherent bootstrap sampling in Monte Carlo, and a truthiness check on a float return value.

## Critical Issues

### CR-01: Sortino ratio uses incorrect downside deviation formula

**File:** `python/validation/metrics.py:84-88`
**Issue:** The Sortino ratio computes downside deviation as `np.std(returns[returns < 0])` — the standard deviation of only the negative returns. This is **not** the correct downside deviation formula. The standard definition is:

```
downside_deviation = sqrt(mean(min(0, r - target)^2))
```

computed over **all** returns, not just the negative subset. The current implementation has two errors:
1. It excludes zero and positive returns from the calculation entirely, which understates the denominator when negative returns are sparse.
2. It computes standard deviation (centered on the mean of negative returns) rather than deviation from zero (the target).

This produces a Sortino ratio that is unreliable and potentially wildly inflated. For a strategy with 95% winning bars and 5% small losses, the std of that small loss subset will be tiny, producing an artificially huge Sortino. This metric will be used to evaluate strategy viability — incorrect values could lead to deploying a losing strategy.

**Fix:**
```python
def compute_sortino_ratio(
    equity_curve: list[tuple],
    risk_free_rate: float = 0.04,
    trading_periods_per_year: int = 252,
) -> float:
    equity_values = _extract_equity_values(equity_curve)
    if len(equity_values) < 3:
        return 0.0

    returns = _daily_returns(equity_values)
    if len(returns) == 0:
        return 0.0

    rf_daily = risk_free_rate / trading_periods_per_year
    excess = np.mean(returns) - rf_daily

    # Correct downside deviation: sqrt(mean(min(0, r)^2)) over ALL returns
    downside_diffs = np.minimum(returns, 0)
    downside_deviation = np.sqrt(np.mean(downside_diffs ** 2))

    if downside_deviation == 0:
        return 0.0 if excess <= 0 else float('inf')

    annual_factor = np.sqrt(trading_periods_per_year)
    return (excess / downside_deviation) * annual_factor
```

### CR-02: End-of-test positions closed without exit commission

**File:** `python/validation/backtester.py:291-296`
**Issue:** When the backtest ends and remaining open positions are force-closed, exit commission is **not** deducted from P&L. Compare with SL/TP exits (lines 196-199) and max-hold exits (lines 207-209), which both deduct exit commission:

```python
# SL/TP exit (line 196-199) — charges commission:
exit_commission = self.commission_model.get_commission(...)
pnl -= exit_commission

# End-of-test exit (line 291-296) — NO commission:
pnl = self._compute_pnl(pos, exit_price)
self._close_position(pos, exit_price, pnl, ...)
```

This inflates the final equity for any backtest that ends with open positions. With the default $7/lot round-turn commission, each unclosed position gets a free $3.50/lot exit. Over many backtest runs (walk-forward, Monte Carlo), this systematically biases results upward.

**Fix:**
```python
# Close any remaining open positions at last bar's close
for pos in self.positions[:]:
    last_bar = bars.iloc[-1]
    exit_price = last_bar["close"]
    pnl = self._compute_pnl(pos, exit_price)
    exit_commission = self.commission_model.get_commission(
        pos["symbol"], pos["lot_size"], pos["direction"])
    pnl -= exit_commission
    self._close_position(pos, exit_price, pnl,
                        last_bar.get("time", None), "end_of_test")
```

## Warnings

### WR-01: `total_costs` mixes incompatible units (price + account currency)

**File:** `python/validation/costs.py:146`
**Issue:** `apply_costs()` returns `total_costs = spread + slippage_price + commission`, where `spread` and `slippage_price` are in **price units** (e.g., 0.00015 for EURUSD) and `commission` is in **account currency** (e.g., $7.00). Adding 0.00015 + $7.00 = $7.00015 is dimensionally meaningless. Any consumer of this value would get a nonsensical number.

The backtester currently discards `total_costs` (only uses `adjusted_entry`), so this doesn't cause incorrect behavior today. But the function's contract promises a meaningful `total_costs` return, and the test at `test_costs.py:187` validates the meaningless sum.

**Fix:** Either convert all costs to account currency (multiply spread/slippage by pip_value * lot_size) or return them separately:
```python
total_costs_price = spread + slippage_price  # in price units
total_costs_currency = commission             # in account currency
return (adjusted_entry, adjusted_exit, total_costs_price, total_costs_currency)
```

### WR-02: Off-by-one in max_bars_held enforcement

**File:** `python/validation/backtester.py:204,287-288`
**Issue:** A position opened during bar `i` has `bars_held=0`, which is then incremented to 1 at the end of the same bar iteration (line 288). On subsequent bars, `bars_held` is checked at line 204 before incrementing. With `max_bars_held=3`:

| Bar | bars_held at check | Action | bars_held after increment |
|-----|-------------------|--------|--------------------------|
| i | — | opened | 1 |
| i+1 | 1 | held | 2 |
| i+2 | 2 | held | 3 |
| i+3 | 3 ≥ 3 → close | closed | — |

The position exists during 4 bar iterations (i through i+3), not 3. The parameter name `max_bars_held` implies the position should be held for at most that many bars.

**Fix:** Either change the check to `pos["bars_held"] > self.max_bars_held` (so it closes on bar i+3 when bars_held=3 > 3 is false, closes at i+4 when bars_held=4 > 3 is true — wait, that makes it worse). The cleanest fix is to not increment `bars_held` on the opening bar:
```python
# 6. Increment bars_held for open positions (skip positions opened this bar)
for pos in self.positions:
    if pos["bars_held"] > 0 or pos["entry_time"] != timestamp:
        pos["bars_held"] += 1
```
Or simply accept the current behavior and rename the parameter to clarify semantics.

### WR-03: Monte Carlo uses two independent bootstrap loops with different samples

**File:** `python/validation/monte_carlo.py:101-120, 140-149`
**Issue:** The `run()` method executes two separate bootstrap loops. The first (lines 101-120) generates samples for `final_equity` and `max_drawdown`. The second (lines 140-149) generates **new, independent** samples for `sharpe_ratio` and `profit_factor`. Because the two loops draw different random indices, the Sharpe/PF distributions are not from the same scenarios as the equity/drawdown distributions. This makes the output incoherent — the 5th percentile Sharpe doesn't correspond to the 5th percentile equity outcome.

Additionally, this doubles the computational cost unnecessarily.

**Fix:** Merge into a single loop, computing all metrics per bootstrap sample:
```python
for i in range(self.iterations):
    indices = self.rng.randint(0, n_trades, size=n_trades)
    sampled_trades = [trades[idx] for idx in indices]

    # Equity curve metrics
    equity_curve = self._reconstruct_equity(sampled_trades)
    equity_values = np.array([e[1] for e in equity_curve])
    final_equities[i] = equity_values[-1]

    peak = np.maximum.accumulate(equity_values)
    drawdowns = (peak - equity_values) / peak
    max_drawdowns[i] = np.max(drawdowns) if len(drawdowns) > 0 else 0.0

    if equity_values[-1] > self.initial_equity:
        profitable += 1

    # Sharpe and PF from same sample
    bt_returns = np.array([trades[idx]["profit_loss"] for idx in indices]) / self.initial_equity
    bt_mean = np.mean(bt_returns)
    bt_std = np.std(bt_returns)
    mc_sharpe_values[i] = bt_mean / bt_std * np.sqrt(252) if bt_std > 0 else 0

    bt_profits = sum(trades[idx]["profit_loss"] for idx in indices if trades[idx]["profit_loss"] > 0)
    bt_losses = abs(sum(trades[idx]["profit_loss"] for idx in indices if trades[idx]["profit_loss"] < 0))
    mc_pf_values[i] = bt_profits / bt_losses if bt_losses > 0 else float('inf')
```

### WR-04: Dead code — `mc_sharpes` and `mc_pf` computed but never used

**File:** `python/validation/monte_carlo.py:126-134`
**Issue:** Lines 126-134 compute `mc_sharpes` (a single Sharpe value from original trades) and `mc_pf` (a single profit factor from original trades). These variables are never referenced again — the actual distributions are computed in the second loop at lines 137-149. This is dead code that adds confusion.

**Fix:** Remove lines 126-134 entirely:
```python
# Delete these lines:
# returns = np.array([t["profit_loss"] for t in trades])
# mean_return = np.mean(returns) / self.initial_equity ...
# std_return = np.std(returns) / self.initial_equity ...
# mc_sharpes = mean_return / std_return * np.sqrt(252) ...
# profits = sum(t["profit_loss"] for t in trades if ...)
# losses = abs(sum(t["profit_loss"] for t in trades if ...))
# mc_pf = profits / losses if losses > 0 else float('inf')
```

### WR-05: Truthiness check on float return value from `_check_sl_tp`

**File:** `python/validation/backtester.py:193`
**Issue:** The check `if exit_price:` uses Python truthiness on a float. If `_check_sl_tp` ever returns `0.0` (a valid price for some instruments), this would evaluate to `False` and the position would not be closed. While forex prices won't be 0.0, this is a latent bug that would manifest if the system trades instruments that can reach very low prices, or if a bug elsewhere produces a 0.0 price.

**Fix:**
```python
exit_price = self._check_sl_tp(pos, bar)
if exit_price is not None:
    # Close position
```

## Info

### IN-01: Sharpe/Sortino use population std (ddof=0) instead of sample std

**File:** `python/validation/metrics.py:50,57,88`
**Issue:** `np.std(returns)` defaults to `ddof=0` (population standard deviation). The conventional Sharpe and Sortino ratio formulas use sample standard deviation (`ddof=1`). With small sample sizes, population std underestimates volatility, overstating the ratios. For large datasets (>252 points), the difference is negligible.

**Fix:** Use `np.std(returns, ddof=1)` for sample standard deviation.

### IN-02: Monte Carlo Sharpe annualization assumes 1 trade = 1 trading day

**File:** `python/validation/monte_carlo.py:145`
**Issue:** `mc_sharpe_values[i] = bt_mean / bt_std * np.sqrt(252)` annualizes using 252 trading days, treating each trade as one day. If the backtest generates multiple trades per day (hourly bars) or fewer than one trade per day, the annualization factor is wrong. The comment at line 125 acknowledges this approximation.

**Fix:** Accept a `trades_per_year` parameter or derive it from the trade timestamps to make the annualization accurate.

---

_Reviewed: 2026-05-27T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
