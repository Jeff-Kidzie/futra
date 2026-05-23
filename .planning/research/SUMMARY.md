# Project Research Summary

**Project:** Futra
**Domain:** Hybrid AI-powered automated trading system for MetaTrader 5 with web dashboard
**Researched:** 2026-05-23
**Confidence:** HIGH

## Executive Summary

Futra is a hybrid AI trading system where an MQL5 Expert Advisor handles trade execution inside MetaTrader 5, and a Python AI service provides adaptive trading parameters (stop-loss, take-profit, position sizing) based on market regime detection. The system is designed for a single personal account, targeting M15+ timeframe swing/position trading on forex, indices, and commodities. Experts in this domain typically use a "DWX Connect" pattern — file-based IPC between the EA and Python — with the EA as the autonomous execution authority and Python as the intelligence layer.

The recommended approach is to build the EA first with hardcoded safe defaults and a kill switch (before any trading logic), then layer in the data pipeline, AI engine, backtesting, and dashboard incrementally. File-based IPC is preferred over ZeroMQ for simplicity (no MQL5 DLL compilation required), with ZeroMQ as a potential upgrade path if sub-millisecond latency is ever needed. SQLite is preferred over PostgreSQL for cost and simplicity (single-user system), with a documented upgrade path. The EA must always be able to trade independently with conservative defaults even if the entire Python stack crashes.

The critical risks are: (1) overfitting AI models to historical data — the #1 cause of failure in algorithmic trading, mitigated by strict walk-forward validation and months of paper trading; (2) MT5 Python API silently returning `None` on disconnection, requiring explicit checks on every call; (3) position sizing math errors that can blow the account with leverage — mitigated by always using `order_calc_margin()` and starting with micro lots; (4) no kill switch — the system must have emergency shutdown before any trading logic is written. The developer is new to trading, making risk controls and proper paper trading non-negotiable before live capital.

## Key Findings

### Recommended Stack

The stack centers on Python 3.12+ for the AI/service layer, MQL5 (non-negotiable) for the EA, and SvelteKit for the dashboard. FastAPI provides the web API with WebSocket support. SQLite handles persistent storage for a single-user system. PyTorch or scikit-learn powers the regime detection and parameter adaptation models, with scikit-learn preferred for initial development (faster iteration, easier debugging, smaller deployment footprint).

**Core technologies:**
- **MQL5 (MT5 built-in):** Expert Advisor execution — non-negotiable, only way to run code inside MT5
- **Python 3.12+:** AI engine, data pipeline, API server — MT5 package requires Windows
- **MetaTrader5 Python package:** Data access and order API — official connector, synchronous, Windows-only
- **File-based IPC (DWX Connect pattern):** EA ↔ Python communication — simpler than ZeroMQ, no DLL compilation, proven at scale (DWX), sufficient for M15+ timeframes
- **FastAPI + Uvicorn:** Web API backend — async-first, auto-docs, WebSocket support
- **SvelteKit 2.x + Tailwind:** Dashboard frontend — smallest bundle, fastest learning curve for single developer
- **SQLite (with WAL mode):** Persistent data store — sufficient for single user, simpler than PostgreSQL, documented upgrade path
- **scikit-learn (primary) / PyTorch (advanced):** ML models — start with sklearn for regime detection, add PyTorch if deep learning is needed later
- **TA-Lib:** Technical indicators — 150+ indicators, Cython-based performance, now has Windows wheels

**Resolved conflict — ZeroMQ vs. File-based IPC:** STACK.md recommends ZeroMQ for battle-tested real-time communication. ARCHITECTURE.md recommends file-based IPC (DWX Connect pattern) as simpler and proven for M15+ timeframes. **Resolution: Start with file-based IPC.** It eliminates the need to compile MQL5 ZeroMQ bindings (a significant setup barrier for a developer new to trading), works with MT5's sandboxed file access, and the Bridge module architecture isolates the IPC strategy so it can be swapped to ZeroMQ later without affecting other components.

**Resolved conflict — PostgreSQL vs. SQLite:** STACK.md recommends PostgreSQL for concurrent writes. ARCHITECTURE.md recommends SQLite for single-user simplicity. **Resolution: Start with SQLite.** This is a single-user personal system. SQLite with WAL mode handles the read/write pattern fine. PostgreSQL upgrade is a documented migration path if concurrent writes become a bottleneck (unlikely for one user).

### Expected Features

**Must have (table stakes):**
- Market order execution (buy/sell) with SL/TP on every order — non-negotiable for risk management
- Position management (open, close, modify) — essential for managing trades
- Paper trading / demo mode — mandatory before real capital for a new trader
- Basic risk controls (max drawdown, daily loss cap, position size limits) — must exist before any live trading
- Backtesting against historical data — must validate strategy before risking capital
- Kill switch / emergency close-all — design FIRST, before trading logic
- Dashboard showing positions, P&L, and account status — minimum monitoring capability
- Error handling and trade result logging — trades fail, must handle gracefully
- MT5 None-handling on every Python API call — silent failures are the norm

**Should have (competitive):**
- AI regime detection + adaptive SL/TP/position sizing — the core differentiator of Futra
- AI decision log on dashboard — transparency into WHY parameters were chosen
- Multi-timeframe analysis — M15, H1, H4, D1 simultaneously for regime detection
- Walk-forward optimization — validates that backtest results aren't overfit
- Performance analytics (Sharpe, Sortino, profit factor) — professional metrics
- Notification system (Telegram/email) for critical alerts

**Defer (v2+):**
- Monte Carlo simulation — nice-to-have validation, not blocking MVP
- Full web trading platform — monitoring-only dashboard first, trade execution from dashboard later
- Reinforcement learning — explicitly deferred; use interpretable statistical methods instead
- Real-time charting from scratch — use MT5 for charts, dashboard for monitoring
- Mobile native app — PWA approach if needed later

### Architecture Approach

The system uses a hybrid MQL5 EA + Python AI architecture with a Bridge module that isolates all inter-process communication. The EA runs 24/5 inside MT5 as the autonomous execution authority with hardcoded safe defaults. Python provides the intelligence layer (regime detection, parameter adaptation) and communicates with the EA via shared JSON files in MT5's `MQL5/Files/` directory — the same pattern used by the production-proven DWX Connect. The FastAPI backend serves both REST and WebSocket endpoints for the SvelteKit dashboard, with SQLite for persistent storage. The architecture follows five core patterns: file-based IPC bridge, MT5 Python API for data access, async service loop for AI evaluation, WebSocket push for live dashboard updates, and fail-safe EA with conservative defaults.

**Major components:**
1. **MQL5 Expert Advisor** — trade execution, position management, tick monitoring, risk enforcement (last line of defense), hardcoded safe defaults, kill switch
2. **Python Bridge Module** — file-based IPC with EA, MT5 Python API data access, event handling, coordinates between EA and AI
3. **AI Engine** — regime detection, parameter adaptation (SL/TP/position sizing), feature engineering, risk-aware parameter generation
4. **FastAPI Backend** — REST API + WebSocket server for dashboard, serves AI decisions, trade data, performance metrics
5. **SQLite Database** — persistent storage for trade history, AI decisions, performance metrics, audit trail (WAL mode for concurrent reads)
6. **SvelteKit Dashboard** — monitoring interface for positions, P&L, AI decisions, risk status, performance charts

### Critical Pitfalls

1. **No kill switch before trading logic** — Design the emergency shutdown (close all, cancel orders, prevent new trades) FIRST, before any trading logic. The EA must check a "trading enabled" flag on every tick. Triggerable from EA, AI, dashboard, and file flag.
2. **MT5 Python API silently returns None** — Every single `mt5.*` call can return `None` without raising an exception when MT5 disconnects. Wrap every call with explicit None checks and reconnection logic. This is the #2 cause of silent system failure.
3. **Overfitting AI models** — The #1 cause of failure in algorithmic trading. Strict walk-forward validation (60/20/20 split), never optimize on test data, paper trade for 3+ months before live capital. If backtest Sharpe > 2.0, it's suspicious.
4. **Position sizing math errors with leverage** — 1 lot on EURUSD = €100,000 position. Always use `order_calc_margin()` before placing orders. Start with micro lots (0.01). Implement hard maximum position sizes in the EA regardless of AI suggestions.
5. **Python-driven trade execution (anti-pattern)** — Never use `order_send()` as the primary execution path. The EA drives all trade execution inside MT5. Python provides intelligence, not execution. If Python crashes, the EA must continue managing positions with safe defaults.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: EA Core + Kill Switch
**Rationale:** The EA is the foundation everything else depends on, and the kill switch must exist before any trading logic. The EA must be able to run standalone with conservative defaults. This phase also addresses the most critical pitfall (no kill switch).
**Delivers:** MQL5 EA with kill switch, hardcoded safe defaults, basic order execution (market/pending), position management, SL/TP on every order, file reader for AI parameters, conservative default trading
**Addresses:** Kill switch, position sizing safety, type_filling broker compatibility, decimal precision, orders vs. deals vs. positions
**Avoids:** Pitfall 5 (no kill switch), Pitfall 3 (position sizing), Pitfall 6 (type_filling), Pitfall 19 (decimal precision), Pitfall 20 (orders/deals/positions confusion)

### Phase 2: Data Pipeline + Python Bridge
**Rationale:** The AI engine needs market data. The bridge module needs to exist before the AI can send parameters. This phase establishes the communication layer between EA and Python.
**Delivers:** MT5 Python API connector with None-handling and reconnection, file-based IPC bridge (read/write shared JSON files), feature engineering module (indicators, volatility, regime features), SQLite schema and initial data storage
**Addresses:** File-based IPC, MT5 None-handling, symbol selection, Market Watch registration
**Avoids:** Pitfall 2 (silent MT5 disconnections), Pitfall 7 (symbol not in Market Watch), Pitfall 8 (race conditions EA↔AI), Pitfall 11 (MT5 terminal must be running)
**Uses:** Python 3.12+, MetaTrader5 package, TA-Lib, pandas, SQLite

### Phase 3: AI Parameter Engine + Risk Management
**Rationale:** With data flowing and the EA ready to receive parameters, build the core value proposition: regime-adaptive trading parameters. Risk management must be in the Python layer as well as the EA.
**Delivers:** Regime detection model (start with sklearn — random forest or gradient boosting), parameter adaptation logic (SL/TP/position sizing based on regime), Python-side risk management (drawdown limits, daily loss cap, position size validation), decision logging to database, continuous AI evaluation loop
**Addresses:** AI regime detection, adaptive SL/TP, risk management hardening
**Avoids:** Pitfall 1 (overfitting — start with interpretable models, not deep learning), Pitfall 9 (look-ahead bias in features), Pitfall 10 (drawdown spirals — equity-based position sizing)
**Uses:** scikit-learn, pandas, numpy, SQLAlchemy async

### Phase 4: Backtesting + Paper Trading
**Rationale:** Before any live trading, the system must be validated. This is non-negotiable for a developer new to trading. Backtesting requires the data pipeline and AI models. Paper trading requires the full EA + AI system running on a demo account.
**Delivers:** Historical data replay engine, performance analytics (Sharpe, Sortino, max drawdown, profit factor, win rate), walk-forward validation, paper trading mode on MT5 demo account, realistic spread/commission/slippage modeling
**Addresses:** Backtesting, paper trading, validation before live capital
**Avoids:** Pitfall 4 (unrealistic backtesting assumptions — model spread, slippage, commissions), Pitfall 1 (overfitting — walk-forward validation), Pitfall 13 (MT5 vs Python backtest discrepancy), Pitfall 16 (swap costs)
**Uses:** MT5 Python API (historical data), pandas, sklearn metrics

### Phase 5: Web Dashboard (Monitoring)
**Rationale:** With the full system running (EA + AI + backtesting), build the monitoring interface. This depends on all previous phases having data to display.
**Delivers:** FastAPI backend (REST API + WebSocket), SvelteKit dashboard SPA, position/account/equity views, AI decision log, performance charts (equity curve, drawdown), risk status widget, authentication (JWT), read-only design (no trade execution from dashboard)
**Addresses:** Dashboard, monitoring, transparency
**Avoids:** Pitfall 12 (dashboard security — start read-only, proper auth, HTTPS)
**Uses:** FastAPI, Uvicorn, SvelteKit, Tailwind CSS, TradingView Lightweight Charts, SQLite

### Phase 6: Hardening + Notifications
**Rationale:** After the system is running end-to-end with monitoring, harden the risk management, add alerting, and polish deployment. This is the phase before considering any live trading.
**Delivers:** Emergency circuit breakers (EA + Python dual enforcement), drawdown monitoring with auto-stop, alert notifications (Telegram/email for critical events), comprehensive logging and audit trail, deployment scripts and watchdog, MT5 auto-restart procedures
**Addresses:** Production hardening, deployment reliability, alerting
**Avoids:** Pitfall 18 (MT5 auto-update), Pitfall 11 (MT5 must be running — watchdog)

### Phase Ordering Rationale

- **Kill switch first (Phase 1):** The single most important safety mechanism. Trading code without a kill switch is an accident waiting to happen, especially for a developer new to trading.
- **Data pipeline before AI (Phase 2 before 3):** The AI engine depends on market data and a communication channel to the EA. No data = no AI.
- **Backtesting before live (Phase 4 before any live trading):** Non-negotiable for a new trader. Walk-forward validation and paper trading for 3+ months.
- **Dashboard after AI (Phase 5 after 3):** The dashboard needs AI decision data to be useful. Building it first would require mocking data extensively.
- **Hardening last (Phase 6):** Risk management exists from Phase 1 (EA kill switch) and Phase 3 (Python risk layer). Phase 6 adds production hardening and monitoring.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Data Pipeline):** File-based IPC requires understanding MT5's `MQL5/Files/` directory structure, atomic write patterns on NTFS, and the exact DWX Connect protocol format. Needs spike validation.
- **Phase 3 (AI Engine):** Regime detection model selection (HMM vs. sklearn clustering vs. statistical methods) needs research. Overfitting prevention (walk-forward validation) needs careful design.
- **Phase 4 (Backtesting):** Realistic spread/commission/slippage modeling requires broker-specific data. MT5 Strategy Tester vs. custom Python backtester alignment needs validation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (EA Core):** Well-documented MQL5 patterns. Kill switch and safe defaults are straightforward.
- **Phase 5 (Web Dashboard):** Standard FastAPI + SvelteKit patterns. Well-documented libraries.
- **Phase 6 (Hardening):** Deployment and monitoring patterns are standard.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified on PyPI with latest versions. MetaTrader5 package confirmed Windows-only. TA-Lib Windows wheels confirmed. |
| Features | HIGH | Feature landscape derived from official MT5 Python API docs, MQL5 reference, and PROJECT.md constraints. Dependency chain is clear. |
| Architecture | HIGH | File-based IPC pattern is proven (DWX Connect in production). MT5 Python API capabilities confirmed. Architecture research had strong source agreement. |
| Pitfalls | HIGH | Pitfalls derived from official MT5 docs, MQL5 reference, algorithmic trading community knowledge. Developer-new-to-trading warnings are universally documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **MQL5 EA file reading pattern:** The exact JSON parsing approach in MQL5 needs validation. MQL5 doesn't have native JSON parsing — need to verify available libraries (mql5-json or manual parsing). Should be resolved in Phase 1 spike.
- **Broker-specific filling types:** `type_filling` must be auto-detected per symbol per broker. Implementation needs to query `symbol_info(symbol).filling_mode` at startup. Should be addressed in Phase 1.
- **Regime detection model selection:** Research didn't definitively choose between HMM, sklearn clustering, gradient boosting, or statistical methods. Phase 3 planning should evaluate options with walk-forward validation on actual data.
- **MT5 VPS deployment specifics:** Running 24/5 on a VPS requires Windows (for MT5), auto-startup scripts, and monitoring. Deployment procedures need to be documented and tested in Phase 6.
- **SQLite to PostgreSQL migration path:** If concurrent writes become a bottleneck (unlikely for single user), need a documented migration path from SQLite to PostgreSQL. SQLAlchemy ORM makes this manageable since both use the same schema.

## Sources

### Primary (HIGH confidence)
- MT5 Python API official documentation (mql5.com) — data access, order management, account info
- MQL5 official documentation (mql5.com) — EA structure, trade operations, file operations
- PyPI MetaTrader5 package — verified latest version 5.0.5735, Windows-only
- PyPI FastAPI, uvicorn, pyzmq, TA-Lib — verified latest versions
- DWX Connect (github.com/darwinex/dwxconnect) — file-based IPC pattern, proven production use
- PROJECT.md constraints and key decisions — project scope, anti-features, trading approach

### Secondary (MEDIUM confidence)
- DWX ZeroMQ Connector (github.com/darwinex/dwx-zeromq-connector) — archived, superseded by DWX Connect
- Context7 PyTorch documentation — verified versions, API patterns
- SvelteKit/Svelte ecosystem documentation — community resources
- Algorithmic trading community knowledge (QuantConnect, Quantopian archives) — overfitting, backtesting pitfalls, position sizing
- backtesting.py library (8.4k stars) — backtesting framework reference

### Tertiary (LOW confidence — needs validation)
- MQL5 ZeroMQ bindings (mql5-lib) — specific repos change frequently, needs verification during implementation
- Specific SvelteKit component libraries (skeleton-ui, Flowbite Svelte) — version compatibility needs checking at implementation time
- MT5 Strategy Tester tick data fidelity — needs validation against real tick data

---
*Research completed: 2026-05-23*
*Ready for roadmap: yes*