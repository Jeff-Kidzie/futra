---
phase: 03-validation
plan: "02"
subsystem: validation
tags: [walk-forward, monte-carlo, paper-trading, backtesting, risk, scheduling]

# Dependency graph
requires:
  - phase: 02-ai-engine
    provides: AIEngine interface (evaluate_symbol, run_once)
  - phase: 03-01
    provides: Backtester.run(), compute_all_metrics(), cost models
provides:
  - WalkForward: anchored expanding-window strategy validation with IS/OOS separation
  - MonteCarlo: trade-reshuffling bootstrap simulation with confidence intervals
  - PaperTrader: AI engine scheduler for MT5 demo account paper trading
affects:
  - 04-dashboard (consumes validation reports and paper trading log format)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure-python numerical simulation (numpy only, no external financial libraries)
    - TDD for all validation components (RED → GREEN per module)
    - Mock backtester fixtures for testability without MT5 connection

key-files:
  created:
    - python/validation/walk_forward.py
    - python/validation/monte_carlo.py
    - python/validation/paper_trading.py
    - python/tests/validation/test_walk_forward.py
    - python/tests/validation/test_monte_carlo.py
    - python/tests/validation/test_paper_trading.py
  modified: []

key-decisions:
  - "Walk-forward uses anchored expanding windows (IS grows, OOS fixed 6mo) rather than sliding windows — more historical data per window as validation progresses"
  - "Monte Carlo bootstraps trades WITH replacement (preserves total trade count per iteration) and also produces Sharpe/PF distributions from bootstrapped samples"
  - "PaperTrader is intentionally thin — it just schedules AIEngine.run_once(); the EA already handles demo execution; paper trading is configuration not new code"
  - "Monte Carlo pass-through: No explicit 'passed' flag — the caller interprets CIP and metric distributions against their own thresholds"

requirements-completed:
  - BACK-03
  - BACK-04
  - BACK-05

# Metrics
duration: 4min
completed: 2026-05-27
---

# Phase 3 Plan 02: Walk-Forward, Monte Carlo & Paper Trading Summary

**Walk-forward validation (anchored expanding windows with IS/OOS separation), Monte Carlo trade-reshuffling bootstrap (confidence intervals + CIP), and PaperTrader scheduler (delegates to AIEngine.run_once() for MT5 demo account execution) — all fully testable with mock data, no MT5 connection required.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-27T05:54:47Z
- **Completed:** 2026-05-27T05:58:51Z
- **Tasks:** 3
- **Files modified:** 6 (882 lines added)

## Accomplishments

- **Walk-forward validation** — WalkForward class splits historical OHLCV data into anchored expanding windows (IS grows, OOS slides forward at 6mo intervals). Each window runs backtester on IS and OOS separately, computing all 8 performance metrics per window. Aggregate report includes mean OOS Sharpe, mean OOS profit factor, worst-window drawdown, and IS/OOS Sharpe ratio (overfitting indicator). Pass/fail threshold enforcement with configurable criteria (min Sharpe, min profit factor, max drawdown). Handles empty data and insufficient OOS trades gracefully.
- **Monte Carlo simulation** — MonteCarlo class bootstraps trade sequences WITH replacement across N iterations (default 2000). Computes distribution statistics (mean, median, 5th/25th/75th/95th percentiles) for final equity, max drawdown, Sharpe ratio, and profit factor. Key metric: Confidence in Profitability (CIP) — % of simulations ending profitable. Deterministic with random_seed, variable results across different seeds. Handles empty trades gracefully.
- **Paper trading mode** — PaperTrader class wraps AIEngine and delegates to run_once() on a configurable schedule. Start/stop loop for continuous evaluation. ValueError raised when run_cycle() called without engine (defers engine creation to caller). Handles None entries in engine results gracefully. Cycle counter tracked via cycle_count property.

## Task Commits

Each task was committed atomically with TDD discipline (test → feat):

1. **Task 1: Walk-forward validation**
   - `acb7136` (test): add failing tests for walk-forward validation (9 tests)
   - `ccc519b` (feat): implement walk-forward validation orchestrator

2. **Task 2: Monte Carlo simulation**
   - `f9b6f21` (test): add failing tests for Monte Carlo simulation (8 tests)
   - `7322e7f` (feat): implement Monte Carlo simulation

3. **Task 3: Paper trading mode**
   - `748823d` (test): add failing tests for paper trading mode (5 tests)
   - `44519db` (feat): implement paper trading mode

## Files Created/Modified

- `python/validation/walk_forward.py` - WalkForward class: anchored expanding-window strategy validation with IS/OOS separation, pass/fail thresholds (206 lines)
- `python/validation/monte_carlo.py` - MonteCarlo class: trade-reshuffling bootstrap with distribution stats and CIP (158 lines)
- `python/validation/paper_trading.py` - PaperTrader class: AIEngine scheduler for MT5 demo paper trading (146 lines)
- `python/tests/validation/test_walk_forward.py` - 9 unit tests for walk-forward validation (193 lines)
- `python/tests/validation/test_monte_carlo.py` - 8 unit tests for Monte Carlo simulation (101 lines)
- `python/tests/validation/test_paper_trading.py` - 5 unit tests for paper trading mode (78 lines)

## Decisions Made

- **Anchored expanding windows:** The walk-forward uses IS periods that grow by incorporating previous OOS periods (anchored at data start), rather than sliding fixed-length windows. This maximizes training data per window as validation progresses at the cost of each window having different IS data length — acceptable because OOS is always the same length and IS metrics are not compared across windows.
- **Monte Carlo pass-through semantics:** Unlike WalkForward which has an explicit pass/fail determination, MonteCarlo returns distribution statistics without an opinion on pass/fail. The caller (dashboard or user) interprets CIP and percentile ranges against their own risk tolerance — this provides more flexibility for consumption.
- **PaperTrader as thin scheduler:** The paper trader is intentionally minimal — it delegates all evaluation logic to AIEngine.run_once(). The EA (Phase 1) already handles trade execution on whatever MT5 account it's attached to (demo or live). Paper trading is achieved by running the AI engine while MT5 is logged into a demo account — it's configuration, not new code.
- **TDD pattern for all validation modules:** Each of the 3 modules follows RED → GREEN TDD discipline — tests written first, confirmed failing, then implementation makes them pass.

## Deviations from Plan

None - plan executed exactly as written.

### TDD Gate Compliance

| Task | RED (test) | GREEN (feat) | Status |
|------|-----------|-------------|--------|
| 1. Walk-forward | `acb7136` | `ccc519b` | Pass |
| 2. Monte Carlo | `f9b6f21` | `7322e7f` | Pass |
| 3. Paper Trading | `748823d` | `44519db` | Pass |

Each test commit was verified to fail before implementation was added. No gate violations.

## Issues Encountered

- **numpy identity vs value comparison in test 9:** `np.False_` is not Python `False` — the identity check `is False` failed. Fixed by using `== True`/`== False` for numpy boolean comparison.
- **Linear equity curve → zero Sharpe variance:** The GoodBacktester mock in test 9 needed noisy (not linear) equity curves to produce non-zero Sharpe variance for realistic pass/fail threshold testing.

## User Setup Required

None — all validation components are pure Python testable without external services. Paper trading requires MT5 demo account setup at deployment time.

## Next Phase Readiness

- Validation suite complete: cost models, backtester, metrics, walk-forward, Monte Carlo, paper trading
- **Phase 3 validation complete** — ready for Phase 4 (Monitoring Dashboard)
- 63 tests passing across all validation components (41 Wave 1 + 22 Wave 2)
- All components testable without live MT5 connection (per D-11)

## Verification

```
python -m pytest python/tests/validation/ -v           → 63 passed
Walk-forward verification: 2 windows, mock data         → OK
Monte Carlo verification: CIP=100%, equity stats valid  → OK
Paper trader verification: boots without engine         → OK
```

---

*Phase: 03-validation*
*Completed: 2026-05-27*
