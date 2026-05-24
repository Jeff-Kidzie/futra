---
phase: 01-foundation-safety
plan: 03
subsystem: risk-management
tags: [mql5, circuit-breaker, pending-orders, drawdown, daily-loss-cap, margin-validation, position-sizing]

# Dependency graph
requires:
  - phase: 01-01
    provides: EA core (Common.mqh types, Config.mqh defaults, Logger.mqh, OrderManager.mqh, PositionManager.mqh)
provides:
  - RiskManager.mqh module with 8 exported functions for risk control
  - PlacePendingOrder for all 6 pending order types (DATA-07)
  - CheckDrawdownLimit circuit breaker with peak-balance tracking (RISK-02)
  - CheckDailyLossLimit with midnight auto-reset (RISK-03)
  - CheckMaxPositionsPerSymbol position count enforcement (RISK-04)
  - ValidatePositionSize with OrderCalcMargin + 150% buffer (RISK-05)
  - IsTradingAllowed master risk gate — single entry point before any order
  - RecordClosedTradeProfit for daily loss accumulation
affects:
  - 01-03-risk-controls

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-trade risk gate: IsTradingAllowed() called in OnTick BEFORE any order logic, gates in priority order (drawdown → daily loss → position limits → margin)"

key-files:
  created:
    - ea/include/RiskManager.mqh - Risk control module (285 lines): PlacePendingOrder, CheckDrawdownLimit, CheckDailyLossLimit, CheckMaxPositionsPerSymbol, ValidatePositionSize, IsTradingAllowed, RecordClosedTradeProfit, ResetDailyLossTracking
    - tests/ea/test_risk_controls.py - Contract tests (39 tests): module exports, EA integration, drawdown breach log, daily loss cap log, max positions log, margin validation log, pending order log, risk gate integration, configurable inputs
  modified:
    - ea/FutraEA.mq5 - Added RiskManager include, OnInit risk state init, IsTradingAllowed gate in OnTick per-symbol loop

key-decisions:
  - "20% max drawdown from peak balance as circuit breaker threshold — conservative starting value per CONTEXT.md agent discretion"
  - "5% daily loss cap with midnight auto-reset — prevents runaway losses within a single trading day"
  - "1 max position per symbol — prevents over-concentration on any single instrument"
  - "150% margin buffer — requires 1.5x required margin available before placing orders"
  - "IsTradingAllowed gates in priority order: drawdown first (most catastrophic), then daily loss, position limits, margin"
  - "Pending orders use SL/TP based on requested entry price (not current market) — uses InpSafeDefaultSLPercent when percentages are 0"

patterns-established:
  - "Pre-trade risk gate: IsTradingAllowed() is the single entry point for all risk checks. EA calls it BEFORE any order logic. Gate order priority: circuit breakers (drawdown, daily loss) → limits (positions per symbol) → validation (margin)."
  - "Contract testing for risk log output: Python tests verify JSONL log format for each risk event (drawdown breach, daily loss cap, position limit, margin rejection) without requiring MT5 runtime."

requirements-completed:
  - DATA-07
  - RISK-02
  - RISK-03
  - RISK-04
  - RISK-05

# Metrics
duration: 15min
completed: 2026-05-24
---

# Phase 01 Plan 03: Risk Controls Summary

**Pending orders with all 6 types plus drawdown circuit breaker, daily loss cap, max positions per symbol, and margin-based position sizing validation — risk gates executing as pre-trade checks in EA OnTick before any order execution.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-24T13:18:40Z
- **Completed:** 2026-05-24T13:33:00Z
- **Tasks:** 1 (TDD cycle: RED → GREEN)
- **Files modified:** 3

## Accomplishments

- RiskManager.mqh module with 8 exported functions covering all risk requirements (RISK-02 through RISK-05, plus DATA-07 pending orders)
- IsTradingAllowed master gate integrated into EA OnTick loop — runs BEFORE any order logic, skips symbols that fail risk checks via `continue`
- All 39 risk control contract tests pass — verifying module exports, EA integration, log output formats, and configurable inputs
- Conservative defaults: 20% drawdown limit, 5% daily loss cap, 1 position per symbol, 150% margin buffer
- No regressions — all 145 EA tests pass with 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Risk control tests** - `dd92c6d` (test: 23 module tests fail, 16 contract tests pass)
2. **Task 1 (GREEN): Risk control implementation** - `96eefc3` (feat: all 39 tests pass)

## Files Created/Modified

- `ea/include/RiskManager.mqh` — Risk control module with PlacePendingOrder (6 types), CheckDrawdownLimit (ACCOUNT_EQUITY vs peak balance at 20%), CheckDailyLossLimit (midnight-reset, 5% cap), CheckMaxPositionsPerSymbol (1 per symbol), ValidatePositionSize (OrderCalcMargin + 150% buffer), IsTradingAllowed (master gate), RecordClosedTradeProfit, ResetDailyLossTracking
- `ea/FutraEA.mq5` — Added `#include "include/RiskManager.mqh"`, OnInit risk state init (`s_peakBalance = ACCOUNT_BALANCE`, `ResetDailyLossTracking()`), OnTick per-symbol loop: `if(!IsTradingAllowed(sym, volume)) continue;`
- `tests/ea/test_risk_controls.py` — 39 tests: 18 module export tests, 5 EA integration tests, 16 IPC contract tests (drawdown breach, daily loss cap, max positions, margin validation, pending order, risk gate, configurable inputs)

## Decisions Made

- 20% max drawdown from peak balance as circuit breaker threshold — conservative starting value per CONTEXT.md agent discretion
- 5% daily loss cap with midnight auto-reset — prevents runaway losses within a single trading day
- 1 max position per symbol — prevents over-concentration on any single instrument
- 150% margin buffer — requires 1.5x required margin available before placing orders
- IsTradingAllowed gates in priority order: drawdown first (most catastrophic), then daily loss, position limits, margin
- Pending orders use SL/TP based on requested entry price (not current market) — uses safe defaults from Config when percentages are 0

## Deviations from Plan

None — plan executed exactly as written with TDD discipline (RED → GREEN cycle).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 1 (Foundation + Safety) now complete. All 3 plans executed:
- 01-01: EA core (kill switch, market orders, position management, IPC reader, trade logging)
- 01-02: Data pipeline (MT5 connection, multi-asset data, IPC writer, file-based contract)
- 01-03: Risk controls (pending orders, circuit breakers, daily loss cap, position limits, margin validation)

Ready for Phase 2: AI Engine (regime detection, adaptive parameters, AI decision logging).

---

*Phase: 01-foundation-safety*
*Completed: 2026-05-24*
