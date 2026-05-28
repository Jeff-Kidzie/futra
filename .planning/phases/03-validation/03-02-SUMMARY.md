---
phase: 03-validation
plan: "02"
subsystem: validation
tags: [walk-forward, monte-carlo, paper-trading, backtesting, bootstrap]

# Dependency graph
requires:
  - phase: 03-validation
    plan: "01"
    provides: "Backtester class, compute_all_metrics(), cost models, config constants"
  - phase: 02-ai-engine
    plan: "01"
    provides: "AIEngine class with run_once() and evaluate_symbol()"
provides:
  - Anchored expanding-window walk-forward validation orchestrator (class WalkForward)
  - Trade-reshuffling bootstrap Monte Carlo simulation with CIP (class MonteCarlo)
  - AI engine scheduler for demo MT5 paper trading (class PaperTrader)
affects: [04-monitoring-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN cycle: tests written first (ModuleNotFoundError), then implementation, then regression check"
    - "Mock backtester pattern: MockBacktester() returns fixed trades + equity curve for testing validation components"
    - "Validation consumer pattern: all validation modules consume Backtester + metrics from 03-01, no direct MT5 dependency"

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
  - "Walk-forward uses anchored expanding windows with configurable in-sample years and OOS months"
  - "Monte Carlo bootstraps trades WITH replacement and computes CIP (Confidence in Profitability)"
  - "PaperTrader is intentionally thin — delegates entirely to AIEngine.run_once(); paper trading IS live trading on demo"
  - "All validation components testable without live MT5 connection (per D-11) using mock backtesters"

patterns-established:
  - "RED/GREEN cycle per task: commit test(03-02): ... → commit feat(03-02): ..."
  - "Mock backtester fixture pattern for validation testing: returns fixed trades + linear equity curve"
  - "Metric stats dict pattern: {mean, median, pct_5, pct_25, pct_75, pct_95}"

requirements-completed: [BACK-03, BACK-04, BACK-05]

# Metrics
duration: 22 tasks
completed: 2026-05-28
---

# Phase 03 Plan 02: Validation Consumer Layers Summary

**Walk-forward optimization (anchored expanding windows), Monte Carlo bootstrap simulation (trade reshuffling with CIP), and paper trading scheduler (AI engine delegation for demo MT5)**

## Performance

- **Duration:** 3 tasks (6 atomic commits)
- **Started:** 2026-05-28
- **Completed:** 2026-05-28
- **Tasks:** 3 (all TDD)
- **Files created:** 6

## Accomplishments
- Walk-forward validation splits 3-year data into 2 anchored expanding windows, runs backtests IS/OOS per window, computes aggregate Sharpe/profit-factor/drawdown, and determines pass/fail against configurable thresholds
- Monte Carlo simulation bootstraps trades WITH replacement across N iterations, produces metric distributions with 6-percentile stats, and computes Confidence in Profitability (CIP: % of simulations profitable)
- PaperTrader delegates to AIEngine.run_once() on a configurable schedule with cycle counting, graceful None-entry handling, and proper ValueError on missing engine
- All 22 new tests pass (8 walk-forward + 8 Monte Carlo + 6 paper trading), total suite: 147 passed

## Task Commits

Each TDD task produced RED → GREEN atomic commits:

1. **Task 1: Walk-forward validation** — `45a28af` (test/red), `a146637` (feat/green)
2. **Task 2: Monte Carlo simulation** — `be075b3` (test/red), `daac410` (feat/green)
3. **Task 3: Paper trading scheduler** — `a640e7e` (test/red), `b398bf4` (feat/green)

**Plan metadata:** To be committed after SUMMARY creation.

## Files Created
- `python/validation/walk_forward.py` — Anchored expanding-window walk-forward orchestrator (class WalkForward)
- `python/validation/monte_carlo.py` — Trade-reshuffling bootstrap Monte Carlo simulation (class MonteCarlo)
- `python/validation/paper_trading.py` — AI engine scheduler for demo MT5 paper trading (class PaperTrader)
- `python/tests/validation/test_walk_forward.py` — 8 tests: window generation, run() structure, date ranges, per-window fields, aggregate metrics, pass/fail criteria, low-trade warnings, empty data handling
- `python/tests/validation/test_monte_carlo.py` — 8 tests: output keys, percentile fields, CIP=100%/CIP>90%/CIP=0%, iteration count, reshuffling variability, empty trades
- `python/tests/validation/test_paper_trading.py` — 6 tests: init with/without engine, run_cycle delegation, empty results, None-mixed results, ValueError on missing engine

## Decisions Made
- Walk-forward uses `365.25 * in_sample_years` and `30.44 * oos_months` for approximate day counts (matches plan specification)
- Monte Carlo uses `np.where(peak > 0, peak, 1.0)` in drawdown calculation to avoid division-by-zero edge case
- Monte Carlo replaces `inf` profit_factor values with `1e6` before computing distribution stats (avoids stat computation issues with infinite values)
- Test 7 (reshuffling variability) uses variable trade values instead of identical trades — identical trades converge to same mean regardless of seed
- Added 6th paper trading test (empty engine result) beyond plan's 5 — covers run_cycle() returning empty list edge case

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_reshuffling_produces_variable_results assertion**
- **Found during:** Task 2 (Monte Carlo GREEN phase)
- **Issue:** Test used identical trades ($100 each, 50 trades) — bootstrapping with replacement always converges to `10000 + 50*100 = 15000.0` regardless of random seed, so `result1["final_equity"]["mean"] != result2["final_equity"]["mean"]` always failed
- **Fix:** Changed test to use variable trade values (`np.random.choice([100.0, 50.0, -20.0, 200.0, -80.0], size=50)`) so different seeds produce different bootstrap distributions
- **Files modified:** `python/tests/validation/test_monte_carlo.py`
- **Verification:** Test passes — two runs with seeds 42 and 99 produce different mean final equity
- **Committed in:** `daac410` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minor test design fix. Core implementation unchanged. No scope creep.

## Issues Encountered
None — all three TDD cycles completed cleanly on first GREEN attempt (except test 7 fix documented above).

## Threat Surface Scan

No new threat flags beyond the `<threat_model>` documented in the plan. All three modules operate within existing trust boundaries:
- WalkForward consumes Backtester + metrics (same trust boundary as 03-01)
- MonteCarlo processes trade lists (no network surface, no file I/O)
- PaperTrader wraps AIEngine (same trust boundary as 02-01)

## Known Stubs
None — all three modules are fully implemented with no placeholder code or hardcoded empty values.

## Next Phase Readiness
- Validation consumer layers complete — walk-forward, Monte Carlo, and paper trading all operational
- Ready for Phase 04 (Monitoring Dashboard) which will consume backtesting results and display trade history
- Phase 03 is now complete (all 2 plans executed)

---
*Phase: 03-validation*
*Completed: 2026-05-28*
