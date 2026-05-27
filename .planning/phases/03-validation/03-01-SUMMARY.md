---
phase: 03-validation
plan: "01"
subsystem: validation
tags: [backtesting, cost-models, metrics, sharpe, sortino, drawdown, profit-factor, spread, commission, slippage]

# Dependency graph
requires:
  - phase: 02-ai-engine
    provides: RegimeDetector, ParameterAdapter, compute_features
  - phase: 01-foundation-safety
    provides: config.py patterns, data_pipeline OHLCV format
provides:
  - Cost models: FixedSpreadModel, HistoricalSpreadModel, PerLotCommissionModel, FixedSlippageModel, NoSwapModel
  - apply_costs() entry/exit price adjustment with spread/commission/slippage
  - Backtester: bar-level EA trade execution simulation with SL/TP, risk gates, equity curve
  - Performance metrics: Sharpe, Sortino, max drawdown, profit factor, win rate, avg win/loss, total return, Calmar
affects:
  - 03-02-PLAN.md (Walk-Forward, Monte Carlo, Paper Trading — consumes Backtester.run() and compute_all_metrics())
  - 04-dashboard (consumes metrics reports and backtest results)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Bar-level EA simulation replays OHLCV through AI pipeline (features → regime → adapted params)
    - Composable cost model hierarchy with base classes for extensibility
    - Pure-function metrics with no IO, fully deterministic from trades + equity curve
    - Risk gates mirror EA's RiskManager.mqh (drawdown, daily loss, position limit)

key-files:
  created:
    - python/validation/__init__.py
    - python/validation/costs.py
    - python/validation/backtester.py
    - python/validation/metrics.py
    - python/tests/validation/__init__.py
    - python/tests/validation/conftest.py
    - python/tests/validation/test_costs.py
    - python/tests/validation/test_backtester.py
    - python/tests/validation/test_metrics.py
  modified:
    - python/config.py

key-decisions:
  - "Cost model composability via abstract base classes (SpreadModel, CommissionModel, SlippageModel, SwapModel) with multiple implementations"
  - "Backtester always goes long ('buy') in initial version — short selling deferred"
  - "Equity curve tracks realized P&L only (no unrealized P&L from open positions)"
  - "SL/TP both-hit tiebreaker uses bar open-to-close direction (down bar → SL first for longs)"
  - "Commission charged per side (entry + exit), matching typical retail broker pattern"
  - "Metrics use numpy only — no external financial library dependency"

requirements-completed:
  - BACK-01
  - BACK-02

# Metrics
duration: 10min
completed: 2026-05-27
---

# Phase 3 Plan 01: Cost Models, Backtesting Engine & Performance Metrics Summary

**Bar-level EA simulation engine with realistic cost models (spread, commission, slippage) and 8 financial performance metrics (Sharpe, Sortino, drawdown, profit factor, win rate, avg win/loss, total return, Calmar) — all testable with mock OHLCV data, no MT5 connection.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-27T05:41:33Z
- **Completed:** 2026-05-27T05:52:16Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- **Cost models** — FixedSpreadModel (constant spread from config), HistoricalSpreadModel (reads MT5 spread column from OHLCV DataFrame), PerLotCommissionModel ($7/lot round-turn), FixedSlippageModel (0.5 pips majors, 1.0 minors), NoSwapModel (swap disabled) — all composable via abstract base classes
- **apply_costs()** — Adjusts entry/exit prices for spread (half each side), commission (per side), and slippage (entry only). Handles buy and sell directions symmetrically
- **Backtesting engine** — Backtester class replays historical OHLCV bars through the AI pipeline (features → regime detection → parameter adaptation). Simulates EA logic: SL/TP hit detection from bar high/low, both-hit tiebreaker using bar direction, max holding period, risk gates (drawdown from peak equity, daily loss cap at midnight reset, max positions per symbol)
- **Performance metrics** — 8 pure functions computing Sharpe ratio (annualized with rf=4%), Sortino ratio (downside deviation only), max drawdown (rolling peak method), profit factor (gross profit / gross loss), win rate, average win/loss ratio, total return, and Calmar ratio. All aggregated in compute_all_metrics()
- **Validation config** — 16 new constants in config.py: DEFAULT_INITIAL_EQUITY, DEFAULT_SPREAD_PIPS, COMMISSION_PER_LOT, SLIPPAGE_PIPS_MAJORS/MINORS, PIP_SIZE, walk-forward params, Monte Carlo params, paper trading params
- **41 tests passing** — All components fully testable with mock DataFrames (no MT5 connection required per D-11)

## Task Commits

Each task was committed atomically with TDD discipline (test → feat):

1. **Task 1: Cost models & validation config**
   - `298859c` (test): add failing tests for cost models and validation config
   - `c4d815e` (feat): implement cost models and validation config

2. **Task 2: Backtesting engine**
   - `53e22c2` (test): add failing tests for backtesting engine
   - `da07cff` (feat): implement backtesting engine

3. **Task 3: Performance metrics**
   - `a6a9e20` (test): add failing tests for performance metrics
   - `65a10a3` (feat): implement performance metrics

**Plan metadata:** (after SUMMARY.md)

## Files Created/Modified

- `python/config.py` - Added 16 validation constants (backtesting, costs, walk-forward, Monte Carlo, paper trading)
- `python/validation/__init__.py` - Validation module entry point
- `python/validation/costs.py` - Cost model classes and apply_costs() function (304 lines)
- `python/validation/backtester.py` - Backtester class with run(), risk gates, SL/TP logic (330 lines)
- `python/validation/metrics.py` - 8 performance metric functions + compute_all_metrics() (234 lines)
- `python/tests/validation/__init__.py` - Empty test module init
- `python/tests/validation/conftest.py` - Sample OHLCV DataFrame fixtures with spread column
- `python/tests/validation/test_costs.py` - 15 tests for cost models and apply_costs()
- `python/tests/validation/test_backtester.py` - 12 tests for backtesting engine
- `python/tests/validation/test_metrics.py` - 14 tests for performance metrics

## Decisions Made

- **Cost model composability:** Abstract base classes (SpreadModel, CommissionModel, SlippageModel, SwapModel) with independent implementations allow mixing real/historical spread with default commission/slippage models
- **Long-only backtesting:** Backtester always opens buy positions — short selling is deferred to a later enhancement. The cost model already supports sell direction via apply_costs()
- **Realized P&L only:** Equity curve reflects realized P&L from closed trades + commission deductions. No mark-to-market on open positions (simplification for bar-level simulation)
- **Both-hit tiebreaker:** When price crosses both SL and TP in a single bar, the bar direction (open-to-close) determines which hit first — SL for down bars, TP for up bars (conservative for longs)
- **Commission per side:** Applied at entry (deducted from equity immediately) and exit (deducted from P&L), matching typical retail broker execution
- **STD for Sortino:** Downside deviation uses numpy.std() (population std), consistent with the Sharpe implementation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pandas 3.x deprecated `freq="H"` frequency alias**
- **Found during:** Task 1 (RED phase — test collection)
- **Issue:** `pd.date_range(freq="H")` raised ValueError in pandas 3.14 — the uppercase "H" alias was removed, lowercase "h" required
- **Fix:** Changed `freq="H"` to `freq="h"` in conftest.py fixtures
- **Files modified:** `python/tests/validation/conftest.py`
- **Verification:** All tests pass
- **Committed in:** c4d815e (Task 1 feat commit)

**2. [Rule 2 - Missing Edge Cases] Extended cost model tests with additional edge cases**
- **Found during:** Task 1 (implementing tests)
- **Issue:** Core behavior tests only had 7 tests. Added 8 edge case tests for robustness: HistoricalSpreadModel empty DataFrame, specific timestamp lookup, commission scaling with volume, commission same both sides, all majors slippage, sell direction costs, zero-cost scenario
- **Fix:** Added extra test methods to the test_costs.py file
- **Files modified:** `python/tests/validation/test_costs.py`
- **Verification:** 15 tests pass instead of required 7
- **Committed in:** 298859c (Task 1 test commit)

**3. [Rule 1 - Bug] Flat market test falsely passed with positive P&L**
- **Found during:** Task 2 (test_flat_market_negative_pnl)
- **Issue:** Random walk in flat_ohlcv fixture produced net positive drift for seed 42, making total P&L positive despite costs
- **Fix:** Replaced test to use perfectly constant prices with larger lot size, ensuring costs always dominate. Fixed assertion to check final_equity < initial_equity instead of total_pnl <= 0
- **Files modified:** `python/tests/validation/test_backtester.py`
- **Verification:** Test passes reliably now
- **Committed in:** da07cff (Task 2 feat commit, via subsequent amendment)

**4. [Rule 1 - Bug] Max bars held test had no max_hold trades**
- **Found during:** Task 2 (test_max_bars_held_enforced)
- **Issue:** Bar low (1.080) exactly equaled SL price (1.080), causing immediate SL hit instead of holding to max_bars_held
- **Fix:** Adjusted bar low to 1.0848 (above SL), ensuring max_hold triggers before SL
- **Files modified:** `python/tests/validation/test_backtester.py`
- **Verification:** max_hold trades found, test passes
- **Committed in:** da07cff (Task 2 feat commit, via subsequent amendment)

---

**Total deviations:** 4 auto-fixed (2 bugs, 1 missing edge cases, 1 blocking)
**Impact on plan:** All fixes necessary for correctness and test reliability. No scope creep.

## TDD Gate Compliance

All three tasks followed proper RED → GREEN commit sequence:

| Task | RED (test) | GREEN (feat) | Status |
|------|-----------|-------------|--------|
| 1. Cost models | `298859c` | `c4d815e` | Pass |
| 2. Backtester | `53e22c2` | `da07cff` | Pass |
| 3. Metrics | `a6a9e20` | `65a10a3` | Pass |

Each test commit was verified to fail before implementation was added. No gate violations.

## Issues Encountered

- Pandas 3.x removed uppercase frequency alias `"H"` — required lowercase `"h"`. Fixed during Task 1 RED phase.
- Flat market test needed careful design — random walks can produce positive drift despite costs. Used constant prices with controlled low/high ranges for deterministic behavior.

## User Setup Required

None — all components are pure Python testable without external services.

## Next Phase Readiness

- Cost models, backtester, and metrics are complete and ready for **Plan 03-02: Walk-Forward Validation, Monte Carlo Simulation & Paper Trading**
- Backtester.run() returns trades list + equity curve (consumed by WalkForward and MonteCarlo)
- compute_all_metrics() provides the performance report format (consumed by WalkForward aggregation)
- Cost model classes are ready for use in walk-forward and paper trading contexts
- All 41 tests pass, confirming correctness of the foundation

---

*Phase: 03-validation*
*Completed: 2026-05-27*
