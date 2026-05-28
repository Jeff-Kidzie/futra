---
phase: 03-validation
reviewed: 2026-05-28T12:00:00Z
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
  - python/tests/validation/__init__.py
  - python/tests/validation/conftest.py
  - python/tests/validation/test_costs.py
  - python/tests/validation/test_backtester.py
  - python/tests/validation/test_metrics.py
  - python/tests/validation/test_walk_forward.py
  - python/tests/validation/test_monte_carlo.py
  - python/tests/validation/test_paper_trading.py
  - python/config.py
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-28T12:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Reviewed the Phase 03 validation subsystem: cost models, backtesting engine, performance metrics, walk-forward validation, Monte Carlo simulation, and paper trading. The implementation is well-structured with good separation of concerns, thorough test coverage, and clean compositional cost models. The backtester correctly simulates bar-level SL/TP checking with a sensible tiebreaker for bars where both levels are hit.

One critical issue was found: `_compute_pnl` uses a hardcoded $10/pip value for all forex pairs, which produces incorrect P&L for non-USD-quote pairs like USDJPY, EURGBP, and GBPJPY. Six warnings cover mixed-unit total costs, fragile date handling, commission/loss accounting, and return type inconsistencies. Five informational items cover code style and documented simplifications.

---

## Critical Issues

### CR-01: Hardcoded $10/pip produces incorrect P&L for non-USD quote pairs

**File:** `python/validation/backtester.py:127`
**Issue:** `_compute_pnl` assigns `pip_value = 10.0` unconditionally for all forex pairs. This is only correct for pairs where USD is the quote currency (EURUSD, GBPUSD, AUDUSD, NZDUSD). For USDJPY, 1 pip per standard lot is ≈¥1,000 (roughly $8.33); for EURGBP it's in GBP; for GBPJPY the pip value depends on the GBPJPY rate. Since `DEFAULT_SYMBOLS` includes USDJPY, backtests on USDJPY will systematically misstate P&L. This violates the project convention: "Financial calculations use decimal precision appropriate to each symbol" (AGENTS.md).

**Fix:**
```python
# Replace the hardcoded line 127 with a pip-value lookup dict:
PIP_VALUE_PER_LOT = {
    "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0, "NZDUSD": 10.0,
    "USDJPY": 1000.0 / 110.0,  # Approximate: ¥1000 per pip ÷ USDJPY rate
    "USDCHF": 10.0 / 0.90,      # Approximate: CHF 10 ÷ USDCHF rate
    "USDCAD": 10.0 / 1.35,      # Approximate: CAD 10 ÷ USDCAD rate
    "EURGBP": 10.0,             # Approximate for now
    "EURJPY": 1000.0 / 130.0,
    "GBPJPY": 1000.0 / 150.0,
    "XAUUSD": 10.0 / 0.10,      # Gold: $1 per 0.01 move × 100 oz = $10 per 0.10
}

def _compute_pnl(self, pos: dict, exit_price: float) -> float:
    pip_value = PIP_VALUE_PER_LOT.get(pos["symbol"], 10.0)
    ...
```

---

## Warnings

### WR-01: `apply_costs()` returns total_costs in mixed units

**File:** `python/validation/costs.py:146`
**Issue:** `total_costs = spread + slippage_price + commission` adds spread/slippage (in price units) to commission (in account currency). These are incommensurable. For EURUSD, spread=0.0001 (~$1 per 0.01 lot) while commission=$0.07 — summing them produces a meaningless number. Though currently unused by callers (backtester discards it via `_, _, _`), any future consumer would get nonsense.

**Fix:** Either:
1. Convert spread/slippage to account currency: `spread_cost = spread / pip_size * pip_value * volume`, or
2. Return them separately: `return (adjusted_entry, adjusted_exit, spread_in_price, commission_in_currency)`, or
3. Remove `total_costs` from the return if it's not needed.

### WR-02: Fragile date detection via hasattr chain

**File:** `python/validation/backtester.py:188-194`
**Issue:** The daily-loss reset logic uses:
```python
bar_date = None
if hasattr(timestamp, 'date'):
    bar_date = timestamp.date()
elif hasattr(timestamp, 'strftime'):
    bar_date = timestamp
```
If `timestamp` is a `datetime` object, it has both `.date()` and `.strftime()`, so `bar_date` becomes a `datetime.date`. If it's a pandas `Timestamp`, `.date()` returns a `datetime.date`. The `elif` branch (strftime) would set `bar_date` to the original object — but this branch is unreachable for `datetime`/`Timestamp` objects. If timestamp comes from a non-standard type, `bar_date` could remain `None`, and the comparison `bar_date != self.current_day` (line 193) would compare `None` vs a date, resetting daily loss on every bar.

**Fix:** Use explicit type checking or a try/except:
```python
try:
    bar_date = timestamp.date() if hasattr(timestamp, 'date') else timestamp
except AttributeError:
    bar_date = timestamp  # fallback for non-date types
```

### WR-03: Commissions inflate daily_loss and trigger risk gate prematurely

**File:** `python/validation/backtester.py:263-264`
**Issue:** Entry commission is added to `self.daily_loss` (line 264):
```python
self.equity -= entry_commission
self.daily_loss += entry_commission
```
This means daily_loss tracks both actual trading losses AND commission costs. For strategies trading small lot sizes with relatively high minimum commissions, the daily loss gate triggers on commission costs alone — blocking further entries even when no real "loss" occurred. The exit P&L (line 317-318) already includes exit commission, so the total counted includes: entry_commission + |price_pnl - exit_commission|.

**Fix:** Either track commission separately from trading losses, or document this as intentional behavior with a configurable toggle. The EA's RiskManager in Phase 1 likely doesn't count commissions as losses, so this divergence from the EA's behavior could cause misleading backtest results.

### WR-04: `or 0` pattern swallows genuine zero Sharpe/Sortino values

**File:** `python/validation/walk_forward.py:156-157, 179-180`
**Issue:** 
```python
is_sharpe = is_metrics.get("sharpe_ratio", 0) or 0
oos_sharpe = oos_metrics.get("sharpe_ratio", 0) or 0
```
The `or 0` is intended to replace `None` (returned by `compute_all_metrics` when profit_factor is inf). However, `0.0` is also falsy, so a genuinely zero Sharpe ratio is also replaced by integer `0`. While the practical effect is nil (0.0 ≈ 0), this masks the distinction between "not computed / inf" and "computed as exactly zero." The same pattern repeats at line 179-180 for OOS sharpes and at 182 for drawdowns.

**Fix:** Use explicit None checks:
```python
is_sharpe = is_metrics.get("sharpe_ratio", 0)
is_sharpe = is_sharpe if is_sharpe is not None else 0
```
Or better, have `compute_all_metrics` return 0.0 instead of None for inf cases (matching the convention used by individual metric functions).

### WR-05: `time.sleep()` blocks graceful `stop()` for up to full interval

**File:** `python/validation/paper_trading.py:124`
**Issue:** The `start()` loop calls `time.sleep(self.interval_seconds)` (default 3600s). If another thread calls `stop()` during the sleep, the loop won't check `self._running` until the sleep completes — delaying shutdown by up to an hour. In production scenarios (deployment, restart, emergency stop), this is unacceptable.

**Fix:** Use a short-interval sleep with periodic flag check:
```python
# Sleep in small chunks, checking _running each time
check_interval = min(1.0, self.interval_seconds / 10)
elapsed = 0.0
while self._running and elapsed < self.interval_seconds:
    time.sleep(check_interval)
    elapsed += check_interval
```

### WR-06: `compute_all_metrics` has inconsistent return type (float | None)

**File:** `python/validation/metrics.py:229-233`
**Issue:** When profit_factor is `float('inf')`, the function returns `None` instead of a float:
```python
"profit_factor": round(pf, 4) if pf != float('inf') else None,
```
The type annotation on the function signature says `dict[str, float]`, but the actual return type is `dict[str, float | None]`. Callers like `walk_forward.py` need defensive `or 0` patterns (see WR-04) to handle these None values.

**Fix:** Return `float('inf')` directly (consistent with individual metric functions), or return a sentinel like `999999.0`, or update the type annotation to `dict[str, float | None]`. Returning `float('inf')` is the simplest and most consistent approach — callers can check `math.isinf()`.

---

## Info

### IN-01: Bare `except Exception` masks AI signal errors

**File:** `python/validation/backtester.py:286-287`
**Issue:** 
```python
except Exception as e:
    logger.warning(f"AI signal error at bar {i}: {e}")
```
Catches all exceptions including `KeyboardInterrupt`, `SystemExit`, and programming errors like `AttributeError`. While this keeps the backtester running (desirable for batch processing), it silently swallows errors that might indicate real bugs in the AI pipeline during development.

**Fix:** Narrow the exception scope to expected failures:
```python
except (ValueError, TypeError, KeyError) as e:
    logger.warning(f"AI signal error at bar {i}: {e}", exc_info=True)
```
Note: `exc_info=True` is critical for debugging — without it, only the message is logged.

### IN-02: Hardcoded direction `"buy"` limits backtest to long-only

**File:** `python/validation/backtester.py:245`
**Issue:** `direction = "buy"  # Always long for initial backtest` — the backtester cannot evaluate short strategies. For a validation subsystem that's meant to prove strategy robustness, this is a significant gap. The infrastructure exists (costs.py handles both directions, _check_sl_tp handles both), so adding short support should be straightforward.

**Fix:** Add a `direction` parameter to `Backtester.__init__` and `run()`, defaulting to `"buy"` for backward compatibility, and extend the AI signal logic to support regime-based direction decisions.

### IN-03: Sharpe approximation in Monte Carlo uses crude annualization

**File:** `python/validation/monte_carlo.py:126-129`
**Issue:** 
```python
bt_mean = np.mean(bt_returns)
bt_std = np.std(bt_returns)
mc_sharpe_values[i] = bt_mean / bt_std * np.sqrt(252) if bt_std > 0 else 0
```
Treats each bootstrap trade as a "daily" return and annualizes with sqrt(252). In reality, trades in the bootstrap could represent any frequency. This produces a Sharpe number that's not comparable to the backtester's bar-frequency Sharpe ratio. The comment already notes "approximate" — worth linking to the metrics module's `compute_sharpe_ratio` for consistency.

### IN-04: Calmar ratio assumes exactly 1 year of data

**File:** `python/validation/metrics.py:198`
**Issue:** `annualized_return = total_return  # Simplified — Phase 4 can add precise duration`. Without knowing the data duration, the Calmar ratio misrepresents annualized return vs peak-to-trough risk. A strategy tested over 3 months with 10% return and 5% drawdown would show Calmar = 2.0, versus the correctly annualized ~0.5.

**Fix:** Accept a `duration_years` parameter or compute it from the equity curve timestamps:
```python
def compute_calmar_ratio(equity_curve: list[tuple], duration_years: float = 1.0) -> float:
    ...
    annualized_return = total_return / duration_years
```

### IN-05: Unused `Optional` import in costs.py

**File:** `python/validation/costs.py:7`
**Issue:** `from typing import Optional` is imported but never used in the file. All type annotations use the `|` syntax (Python 3.10+).

**Fix:** Remove the unused import.

---

_Reviewed: 2026-05-28T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
