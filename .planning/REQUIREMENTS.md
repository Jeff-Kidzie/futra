# Requirements: Futra

**Defined:** 2026-05-23
**Core Value:** Consistent profit with manageable drawdowns — the system must deliver steady returns while keeping risk under control

## v1 Requirements

### Data Pipeline & Core

- [ ] **DATA-01**: System connects to MT5 via Python MetaTrader5 package and retrieves historical and real-time market data
- [ ] **DATA-02**: System supports multi-asset data access (forex pairs, indices, commodities) with per-symbol configuration
- [ ] **DATA-03**: System provides real-time OHLCV data subscription across multiple timeframes (M15, H1, H4, D1)
- [ ] **DATA-04**: Market order execution (buy/sell) via EA with proper order filling type detection per symbol
- [ ] **DATA-05**: Stop-loss and take-profit set on every order with configurable defaults
- [ ] **DATA-06**: Position management: open, close, and modify positions including SL/TP adjustments
- [ ] **DATA-07**: Pending order support (buy limit, sell limit, buy stop, sell stop, buy stop limit, sell stop limit)
- [ ] **DATA-08**: All trade results and errors are logged with retcode, comment, and context for debugging
- [ ] **DATA-09**: File-based IPC channel (DWX Connect pattern) between MQL5 EA and Python for parameter passing
- [ ] **DATA-10**: MT5 connection resilience with auto-reconnect and None-handling for the MT5 Python API

### Risk Management

- [ ] **RISK-01**: Kill switch: emergency stop that immediately halts all trading and optionally closes all positions
- [ ] **RISK-02**: Maximum drawdown circuit breaker: stop trading when account drawdown exceeds configured threshold
- [ ] **RISK-03**: Daily loss cap: stop trading for the day when realized losses exceed configured limit
- [ ] **RISK-04**: Maximum open positions per symbol to prevent over-concentration
- [ ] **RISK-05**: Position sizing validation using MT5 order_calc_margin() to ensure sufficient margin before placing orders
- [ ] **RISK-06**: AI-adaptive position sizing based on account equity, recent win rate, volatility, and regime

### AI Engine

- [ ] **AI-01**: Regime detection model classifies market state (trending, ranging, volatile, quiet) with confidence score per symbol per timeframe
- [ ] **AI-02**: Adaptive parameter engine adjusts SL/TP levels and position sizing based on detected regime and volatility
- [ ] **AI-03**: EA uses hardcoded safe defaults when AI parameters are unavailable (Python crash, IPC failure)
- [ ] **AI-04**: AI decision log records every parameter decision: regime detected, confidence, chosen parameters, and reasoning
- [ ] **AI-05**: Strategy parameter export/import as JSON/YAML for versioning and A/B testing different models

### Backtesting & Validation

- [ ] **BACK-01**: Backtesting engine replays historical data through the AI + EA pipeline with realistic spread and commission modeling
- [ ] **BACK-02**: Performance analytics: Sharpe ratio, Sortino ratio, max drawdown, profit factor, win rate, average win/loss
- [ ] **BACK-03**: Walk-forward optimization using in-sample training and out-of-sample validation windows
- [ ] **BACK-04**: Monte Carlo simulation tests strategy robustness across randomized trade sequences
- [ ] **BACK-05**: Paper trading mode on MT5 demo account with real-time signal generation but no live orders

### Web Dashboard

- [ ] **DASH-01**: Dashboard shows current positions, account status (balance, equity, margin), and real-time P&L
- [ ] **DASH-02**: Trade history with deal details (entry/exit price, profit, duration, symbol, direction)
- [ ] **DASH-03**: AI decision log display showing regime, confidence, parameters chosen, and reasoning per trade
- [ ] **DASH-04**: Equity curve and drawdown charting on dashboard
- [ ] **DASH-05**: Push notification alerts for critical events (drawdown threshold breached, AI model errors, trade execution failures)
- [ ] **DASH-06**: Dashboard accessible from anywhere via internet (not localhost only)
- [ ] **DASH-07**: Authentication and HTTPS for web dashboard access

## v2 Requirements

### Notifications

- **NOTF-01**: Email notification channel for critical alerts
- **NOTF-02**: Telegram bot notification channel for critical alerts
- **NOTF-03**: Configurable alert thresholds and notification preferences

### Advanced Dashboard

- **DASH-08**: Trade journal with manual annotations alongside AI decisions
- **DASH-09**: Strategy parameter management UI (create, edit, version configs)
- **DASH-10**: Monthly returns heatmap and advanced performance visualizations
- **DASH-11**: Manual trading controls from web dashboard (deferred — monitoring-only first)

### Advanced AI

- **AI-06**: Deep learning regime detection (PyTorch) replacing or supplementing classical ML
- **AI-07**: Reinforcement learning exploration for parameter optimization (research only, not production)
- **AI-08**: Multi-symbol correlation analysis for cross-asset regime detection

## Out of Scope

| Feature | Reason |
|---------|--------|
| Crypto trading | Out of scope per PROJECT.md — focus on forex, indices, commodities only |
| Multi-tenant / SaaS | Single personal account only — multi-tenant adds massive complexity with zero benefit |
| High-frequency trading (HFT) | Not targeting sub-millisecond execution; requires different architecture |
| Real-time candlestick charting on dashboard | MT5 already provides full charting; building it is months of work, deferred indefinitely |
| Predictive price direction model | PROJECT.md key decision: adapt parameters, not predict direction |
| Custom broker integration | MT5 handles all broker connectivity |
| Social / copy trading | Single account, no followers, no signal distribution |
| Mobile native app | Web dashboard with responsive design covers mobile, PWA if needed later |
| Level 2 / order book data | Only useful for HFT strategies, which are out of scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 2 | Pending |
| DATA-08 | Phase 1 | Pending |
| DATA-09 | Phase 1 | Pending |
| DATA-10 | Phase 1 | Pending |
| RISK-01 | Phase 1 | Pending |
| RISK-02 | Phase 2 | Pending |
| RISK-03 | Phase 2 | Pending |
| RISK-04 | Phase 2 | Pending |
| RISK-05 | Phase 1 | Pending |
| RISK-06 | Phase 3 | Pending |
| AI-01 | Phase 3 | Pending |
| AI-02 | Phase 3 | Pending |
| AI-03 | Phase 1 | Pending |
| AI-04 | Phase 3 | Pending |
| AI-05 | Phase 3 | Pending |
| BACK-01 | Phase 4 | Pending |
| BACK-02 | Phase 4 | Pending |
| BACK-03 | Phase 4 | Pending |
| BACK-04 | Phase 4 | Pending |
| BACK-05 | Phase 4 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| DASH-06 | Phase 5 | Pending |
| DASH-07 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-23*
*Last updated: 2026-05-23 after initial definition*