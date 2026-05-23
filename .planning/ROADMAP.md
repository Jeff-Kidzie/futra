# Roadmap: Futra

## Overview

Futra starts with a safe, self-contained trading foundation on MT5 — kill switch first, conservative defaults always — then layers in market data flows, AI-driven regime detection and adaptive parameters, rigorous backtesting and paper trading validation, and finally a web dashboard for remote monitoring. Each phase delivers one complete, verifiable capability, and no live capital touches the system until Phase 3 proves it works historically and on demo.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation + Safety** - EA executes trades on MT5 with kill switch, safe defaults, data pipeline, and risk circuit breakers
- [ ] **Phase 2: AI Engine** - Regime detection adapts SL/TP and position sizing based on market conditions
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
**Plans**: 3 plans

Plans:
- [ ] 01-01: EA core — kill switch, market orders, position management, SL/TP, trade logging, safe defaults
- [ ] 01-02: Data pipeline — MT5 Python connection, multi-asset data, real-time OHLCV, file-based IPC, connection resilience
- [ ] 01-03: Risk controls — pending orders, drawdown circuit breaker, daily loss cap, max positions per symbol, position sizing validation

### Phase 2: AI Engine
**Goal**: AI detects market regimes and adapts trading parameters, with position sizing adjusted by regime and volatility
**Depends on**: Phase 1
**Requirements**: AI-01, AI-02, AI-04, AI-05, RISK-06
**Success Criteria** (what must be TRUE):
  1. AI classifies market regime (trending, ranging, volatile, quiet) per symbol per timeframe with confidence scores
  2. AI adjusts SL/TP levels and position sizing based on detected regime and volatility
  3. Every AI parameter decision is logged with regime, confidence, parameters chosen, and reasoning
  4. Strategy parameters can be exported and imported as JSON/YAML for versioning and A/B testing
**Plans**: 2 plans

Plans:
- [ ] 02-01: Regime detection model — classify market state per symbol/timeframe with confidence, adaptive SL/TP and position sizing
- [ ] 02-02: Decision logging and strategy management — log every AI decision, export/import strategy configs

### Phase 3: Validation
**Goal**: The trading system is rigorously validated through backtesting and paper trading before any live capital is risked
**Depends on**: Phase 2
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05
**Success Criteria** (what must be TRUE):
  1. Backtesting engine replays historical data through the AI+EA pipeline with realistic spread, commission, and slippage modeling
  2. Performance analytics reports Sharpe ratio, Sortino ratio, max drawdown, profit factor, win rate, and average win/loss
  3. Walk-forward validation confirms strategy generalizes with out-of-sample testing
  4. Paper trading runs on MT5 demo account with real-time signal generation but no live orders
**Plans**: 2 plans

Plans:
- [ ] 03-01: Backtesting engine and analytics — historical replay with realistic costs, performance metrics
- [ ] 03-02: Walk-forward validation, Monte Carlo simulation, and paper trading mode

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
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [ ] 04-01: Dashboard backend and frontend views — positions, trade history, AI decisions, equity curve, drawdown charts
- [ ] 04-02: Push notifications, internet accessibility, authentication, and HTTPS

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Safety | 0/3 | Not started | - |
| 2. AI Engine | 0/2 | Not started | - |
| 3. Validation | 0/2 | Not started | - |
| 4. Monitoring Dashboard | 0/2 | Not started | - |