---
phase: 03-validation
plan: "01"
subsystem: validation
tags: [backtesting, metrics, costs, sharpe, sortino, drawdown, forex, trading]

# Dependency graph
requires:
  - phase: 01-foundation-safety
    provides: "config.py constants (IPC_DIR, DEFAULT_SYMBOLS), data_pipeline.py fetch_historical_ohlcv() signature"
  - phase: 02-ai-engine
    provides: "AI interfaces: compute_features(), RegimeDetector.predict(), ParameterAdapter.adapt()"
provides:
  - Backtester class for bar-level EA trade execution simulation with AI integration
  - Cost models (spread, commission, slippage, swap) for realistic trade simulation
  - Performance metrics (Sharpe, Sortino, drawdown, profit factor, win rate, avg win/loss, total return, Calmar)
  - Validation config constants (PIP_SIZE, DEFAULT_SPREAD_PIPS, walk-forward params, etc.)
affects:
  - 03-02 (walk-forward, Monte Carlo, paper trading)
  - 04-monitoring (dashboard performance views)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD: 3-cycle RED-GREEN for each module (6 atomic commits)"
    - "Pure functions for metrics — no I/O, fully deterministic"
    - "Composable cost models — mix-and-match spread/commission/slippage per symbol"
    - "Bar-level EA simulation mirroring RiskManager.mqh gate logic"
    - "Mock-based testing — no MT5 connection required per D-11"

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
  - "Custom bar-level simulator over backtrader/vectorbt — directly mirrors EA logic, no framework overhead"
  - "Cost models composable via abstract base classes — SpreadModel, CommissionModel, SlippageModel, SwapModel"
  - "Risk gates mirror RiskManager.mqh exactly: drawdown (20%), daily loss (5%), max positions per symbol (1)"
  - "Metrics compute pure functions with numpy — no external financial library dependency"
  - "Profit factor and Calmar ratio return None (not inf) in compute_all_metrics() for clean JSON serialization"

patterns-established:
  - "TDD: RED (failing test commit) → GREEN (implementation commit) → no REFACTOR needed (clean on first pass)"
  - "MockDetector/MockAdapter pattern for testing backtester without real AI modules"
  - "conftest.py fixtures for sample OHLCV DataFrames with realistic spread data"

requirements-completed: [BACK-01, BACK-02]

# Metrics
duration: 15min
completed: 2026-05-28
---

# Phase 3 Plan 01: Backtesting Engine Foundation Summary

**Bar-level backtesting engine with realistic cost models (spread/commission/slippage), AI pipeline integration, risk gate enforcement, and 9 financial performance metrics — all testable without MT5 (44 tests passing)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-28T01:30:00Z
- **Completed:** 2026-05-28T01:45:00Z
- **Tasks:** 3 (all TDD)
- **Files modified:** 10
- **Total tests:** 44 passing (17 costs + 12 backtester + 15 metrics)

## Accomplishments

- **Cost models** (python/validation/costs.py): FixedSpreadModel, HistoricalSpreadModel, PerLotCommissionModel, FixedSlippageModel, NoSwapModel + apply_costs() composition. Spread from config or OHLCV DataFrame. Commission at $7/lot round-turn. Slippage 0.5 pips majors, 1.0 minors. All 17 tests pass.
- **Backtesting engine** (python/validation/backtester.py): Bar-level EA simulation replaying OHLCV through AI pipeline. SL/TP detection from bar high/low with both-hit bar-direction tiebreaker. Risk gates: drawdown (20%), daily loss cap (5%), max positions per symbol (1), max bars held (48). Equity curve tracked per bar. 12 tests pass including flat market, uptrend, SL/TP, risk gates, and historical spread.
- **Performance metrics** (python/validation/metrics.py): 9 pure functions — Sharpe, Sortino, max drawdown, profit factor, win rate, avg win/loss, total return, Calmar, compute_all_metrics(). All verified against known financial calculations. 15 tests pass including edge cases (zero losses → inf PF, empty trades → zeros).
- **Validation config** (python/config.py): PIP_SIZE per symbol, DEFAULT_SPREAD_PIPS, COMMISSION_PER_LOT, SLIPPAGE_PIPS_MAJORS/MINORS, WF_IN_SAMPLE_YEARS, WF_OUT_OF_SAMPLE_MONTHS, WF_MIN_OOS_TRADES, MC_ITERATIONS, MC_CONFIDENCE_LEVEL, PAPER_TRADING_INTERVAL_SECONDS, MT5_DEMO_LOGIN/PASSWORD/SERVER.
- **Verified end-to-end:** Backtester runs with mock OHLCV + mock AI → produces trades + equity curve → metrics compute correctly → prints "OK — backtester runs without MT5"

## Task Commits

Each TDD task produced 2 atomic commits (RED → GREEN):

1. **Task 1: Validation configuration + cost models** 
   - `f2b2a0d` (test) — RED: 7 failing tests for cost models
   - `dbb601b` (feat) — GREEN: config.py additions + costs.py (17 tests pass)

2. **Task 2: Backtesting engine — bar-level EA simulation**
   - `66570fe` (test) — RED: 12 failing tests for backtester
   - `b732b6b` (feat) — GREEN: backtester.py (12 tests pass)

3. **Task 3: Performance metrics — Sharpe, Sortino, drawdown, profit factor**
   - `0d807f5` (test) — RED: 13 failing tests for metrics
   - `5991473` (feat) — GREEN: metrics.py (15 tests pass)

**Plan metadata:** [pending final commit]

## Files Created/Modified

**Created:**
- `python/validation/__init__.py` — Package init
- `python/validation/costs.py` — 5 cost model classes + apply_costs() (147 lines)
- `python/validation/backtester.py` — Backtester class with risk gates (340 lines)
- `python/validation/metrics.py` — 9 performance metric functions (235 lines)
- `python/tests/validation/__init__.py` — Test package init
- `python/tests/validation/conftest.py` — sample_ohlcv_dataframe_with_spread fixture
- `python/tests/validation/test_costs.py` — 17 tests for cost models
- `python/tests/validation/test_backtester.py` — 12 tests for backtester
- `python/tests/validation/test_metrics.py` — 15 tests for metrics

**Modified:**
- `python/config.py` — Added 40 lines of validation configuration constants

## Decisions Made

- **Custom simulator over backtrader/vectorbt:** Directly mirrors EA's RiskManager.mqh gate logic — more maintainable, transparent, testable per 03-RESEARCH.md findings
- **Cost model composability:** Abstract base classes (SpreadModel, CommissionModel, etc.) allow per-symbol mix-and-match without coupling
- **Risk gate mirroring:** Python _is_trading_allowed() follows EA's IsTradingAllowed() gate order exactly: drawdown → daily loss → position count
- **Metrics return None vs inf:** compute_all_metrics() returns None for infinite values (profit factor with zero losses, Calmar with zero drawdown) — clean JSON serialization for Phase 4 dashboard
- **No REFACTOR commits needed:** All TDD implementations were clean on first GREEN pass — minimal, test-driven code with no duplication

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Flat market test used random-walk data instead of truly flat prices**
- **Found during:** Task 2 (Backtester — GREEN phase)
- **Issue:** `test_flat_market_zero_or_negative_pnl` used `sample_ohlcv` fixture with `np.cumsum(np.random.randn(n) * 0.0002)` which created random walk drift resulting in positive P&L ($1.56) instead of non-positive
- **Fix:** Replaced fixture-dependent test with truly flat DataFrame (all bars at same price 1.085, no drift)
- **Files modified:** `python/tests/validation/test_backtester.py`
- **Committed in:** `b732b6b` (part of Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Test data fix only — no implementation changes needed. All 44 tests now pass correctly.

## Issues Encountered

None — all tasks executed cleanly. TDD cycle worked as designed: RED confirmed → GREEN passed on first implementation attempt.

## User Setup Required

None — no external service configuration required. All components use defaults from config.py with environment variable overrides available for customization.

## Next Phase Readiness

- Backtesting engine ready for walk-forward optimization (Plan 03-02)
- Cost models ready for Monte Carlo simulation and paper trading
- Metrics ready for Phase 4 dashboard consumption
- Requirements BACK-01 and BACK-02 satisfied
- 44 tests provide regression safety for Phase 4 integration

---

*Phase: 03-validation*
*Completed: 2026-05-28*
