# Roadmap: Futra

## Overview

Futra starts with a safe, self-contained trading foundation on MT5 — kill switch first, conservative defaults always — then layers in market data flows, AI-driven regime detection and adaptive parameters, rigorous backtesting and paper trading validation, and finally a web dashboard for remote monitoring. Each phase delivers one complete, verifiable capability, and no live capital touches the system until Phase 3 proves it works historically and on demo.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation + Safety** - EA executes trades on MT5 with kill switch, safe defaults, data pipeline, and risk circuit breakers
- [x] **Phase 2: AI Engine** - Regime detection adapts SL/TP and position sizing based on market conditions (completed 2026-05-26)
- [ ] **Phase 3: Validation** - Backtesting and paper trading prove the system works before live capital
- [ ] **Phase 4: Monitoring Dashboard** - Trading activity and AI decisions visible from anywhere via authenticated web dashboard

## Phase Details

### Phase 1: Foundation + Safety
**Goal**: The trading system connects to MT5, executes trades safely with emergency shutdown, and maintains reliable communication between EA and Python — it works even if the AI layer crashes
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, DATA-09, DATA-10, RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, AI-03
**Success Criteria** (what must be TRUE):
  1. EA executes market and pending orders on MT5 with SL/TP on every order and logs all results
  2. Kill switch immediately halts all trading and optionally closes all positions
  3. EA uses hardcoded safe defaults and continues trading when Python crashes or IPC fails
  4. Python reads historical and real-time OHLCV data from MT5 across multiple symbols and timeframes
  5. Circuit breakers stop trading when drawdown or daily loss exceeds configured thresholds
**Plans**: 3 plans in 2 waves

**Wave 1** (parallel — no shared files):
- [x] 01-01-PLAN.md — EA core: kill switch, market orders, position management, SL/TP, trade logging, safe defaults
- [x] 01-02-PLAN.md — Data pipeline: MT5 Python connection, multi-asset data, real-time OHLCV, file-based IPC, connection resilience

**Wave 2** *(blocked on Wave 1 completion)*:
- [x] 01-03-PLAN.md — Risk controls: pending orders, drawdown circuit breaker, daily loss cap, max positions per symbol, position sizing validation

Cross-cutting constraints:
- IPC file format contract (kill_switch.json, {SYMBOL}_params.json) defined in 01-01, consumed by 01-02
- EA OnTick structure defined in 01-01, extended by 01-03 with RiskManager gate
- All tests use mock MT5 data — no live MT5 connection required (D-11)

### Phase 2: AI Engine
**Goal**: AI detects market regimes and adapts trading parameters, with position sizing adjusted by regime and volatility
**Depends on**: Phase 1
**Requirements**: AI-01, AI-02, AI-04, AI-05, RISK-06
**Success Criteria** (what must be TRUE):
  1. AI classifies market regime (trending, ranging, volatile, quiet) per symbol per timeframe with confidence scores
  2. AI adjusts SL/TP levels and position sizing based on detected regime and volatility
  3. Every AI parameter decision is logged with regime, confidence, parameters chosen, and reasoning
  4. Strategy parameters can be exported and imported as JSON/YAML for versioning and A/B testing
**Plans**: 2 plans in 2 waves

**Wave 1**:
- [x] 02-01-PLAN.md — Regime detection model, adaptive SL/TP and position sizing, AI engine orchestration (features, regime detector, parameter adapter, engine)

**Wave 2** *(blocked on Wave 1 completion)*:
- [x] 02-02-PLAN.md — Decision logging and strategy management (JSONL logger, strategy JSON export/import, engine integration)

### Phase 3: Validation
**Goal**: The trading system is rigorously validated through backtesting and paper trading before any live capital is risked
**Depends on**: Phase 2
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05
**Success Criteria** (what must be TRUE):
  1. Backtesting engine replays historical data through the AI+EA pipeline with realistic spread, commission, and slippage modeling
  2. Performance analytics reports Sharpe ratio, Sortino ratio, max drawdown, profit factor, win rate, and average win/loss
  3. Walk-forward validation confirms strategy generalizes with out-of-sample testing
  4. Paper trading runs on MT5 demo account with real-time signal generation but no live orders
**Plans**: 2 plans in 2 waves

**Wave 1**:
- [x] 03-01-PLAN.md — Cost models, backtesting engine (bar-level EA simulation), and performance metrics (Sharpe, Sortino, drawdown, profit factor)

**Wave 2** *(blocked on Wave 1 completion)*:
- [ ] 03-02-PLAN.md — Walk-forward validation, Monte Carlo simulation, and paper trading mode

Cross-cutting constraints:
- Backtester interface (Backtester.run()) defined in 03-01, consumed by 03-02 (WalkForward, MonteCarlo)
- Metrics interface (compute_all_metrics()) defined in 03-01, consumed by 03-02
- Cost model classes (FixedSpreadModel, PerLotCommissionModel, FixedSlippageModel) defined in 03-01, consumed by 03-01 backtester
- PaperTrader depends on AIEngine from Phase 2 — requires Phase 2 completion before paper trading execution

### Phase 4: Monitoring Dashboard
**Goal**: Trading activity and AI decisions are visible from anywhere through an authenticated web dashboard with real-time updates and push alerts
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):
  1. Dashboard shows current positions, account balance/equity/margin, and real-time P&L
  2. User can browse trade history with entry/exit prices, profit, duration, symbol, and direction
  3. AI decision log displays regime, confidence, parameters chosen, and reasoning per trade
  4. Equity curve and drawdown charts visualize account performance over time
  5. Dashboard is accessible from anywhere via internet with authentication and HTTPS
**Plans**: 3 plans in 3 waves

**Wave 1**:
- [ ] 04-01-PLAN.md — FastAPI dashboard backend: auth, REST API, WebSocket, alert monitoring, SQLite database

**Wave 2** *(blocked on Wave 1 completion)*:
- [ ] 04-02-PLAN.md — SvelteKit dashboard frontend: project config, 7 pages, charts, shadcn-svelte components

**Wave 3** *(blocked on Wave 1 + Wave 2 completion)*:
- [ ] 04-03-PLAN.md — Production deployment: Caddy HTTPS reverse proxy, Windows VPS startup scripts, firewall, .env.example

Cross-cutting constraints:
- API contract (REST endpoints + WebSocket protocol) defined in 04-01, consumed by 04-02 (API client + stores) and 04-03 (Caddy reverse proxy)
- Frontend build output (frontend/build/) defined in 04-02, consumed by 04-03 (StaticFiles mount)
- Auth token format (Bearer token in Authorization header) defined in 04-01, consumed by 04-02 (api.ts fetch wrapper) and 04-03 (Caddy security headers)
- Caddy reverse proxy (04-03) routes all traffic to FastAPI — both 04-01 and 04-02 must be complete before deployment

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Safety | 3/3 | Complete | 2026-05-24 |
| 2. AI Engine | 2/2 | Complete   | 2026-05-26 |
| 3. Validation | 1/2 | In Progress|  |
| 4. Monitoring Dashboard | 0/3 | Not started | - |