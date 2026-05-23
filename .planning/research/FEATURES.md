# Feature Landscape

**Domain:** Hybrid AI-powered automated trading system for MetaTrader 5 with web dashboard
**Researched:** 2026-05-23

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Market order execution (buy/sell)** | Core function of any trading bot — can't trade without it | Low | MT5 supports via `TRADE_ACTION_DEAL` with buy/sell order types. Python `order_send()` and MQL5 `OrderSend()` both available. |
| **Stop-loss & take-profit on every order** | Basic risk management — no serious trader would run a bot without SL | Low | MQL5 `MqlTradeRequest` has native `sl` and `tp` fields. Must be set per order. |
| **Position management (open, close, modify)** | Essential for managing open trades — close profits, cut losses | Medium | MQL5 has `PositionGetTicket`, `PositionGetDouble`, `PositionSelectByTicket`. Python MT5 has `positions_get()`, `positions_total()`. Hedging vs netting account support needed. |
| **Pending order support** | Limit, stop, stop-limit orders are standard trading tools | Medium | MT5 supports 6 pending order types: BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, BUY_STOP_LIMIT, SELL_STOP_LIMIT via `TRADE_ACTION_PENDING`. |
| **Real-time P&L tracking** | Need to know if the bot is making or losing money at a glance | Medium | MT5 `account_info()` returns balance, equity, profit, margin. Must poll via Python API or subscribe via EA events. |
| **Trade history with deal details** | Required for performance analysis, tax reporting, and debugging | Medium | MT5 Python API: `history_deals_get()`, `history_orders_get()` with date range filtering. MQL5: `HistoryDealGetDouble`, `HistoryOrderGetString`. |
| **Backtesting against historical data** | Must validate strategy before risking real capital — non-negotiable for a new trader | High | MT5 built-in Strategy Tester is limited to MQL5. For Python AI models, need custom backtester (backtesting.py or custom). MT5 Python API provides `copy_rates_from()`, `copy_ticks_from()` for historical data. |
| **Paper trading / demo mode** | Must forward-test with fake money before going live — critical for a new trader | Medium | MT5 supports demo accounts natively. The Python API `login()` can connect to demo accounts. EA must support dry-run mode that doesn't send real orders. |
| **Basic risk controls (max drawdown, daily loss cap)** | Without hard risk limits a bug or bad model can blow up the account | Medium | Must be implemented as safety checks in both EA (last line of defense) and Python AI (parameter logic). MT5 has no built-in drawdown limits — this is custom logic. |
| **Dashboard showing positions & account status** | Monitoring is the minimum viable dashboard — need to see what the bot is doing | Medium | Requires web API serving real-time position/account data. MT5 Python API provides `positions_get()`, `account_info()`. Must poll periodically. |
| **Error handling & trade result logging** | Trades fail (requotes, insufficient margin, market closed) — must handle gracefully | Medium | MQL5 `OrderSend()` returns `MqlTradeResult` with `retcode` and `comment`. Python `order_send()` returns `NamedTuple` with `retcode`. All failures must be logged. |
| **Symbol/multi-asset support** | PROJECT.md requires forex pairs, indices, and commodities | Medium | MT5 supports all these via `symbols_get()`, `symbol_info()`. Each symbol has different `SYMBOL_TRADE_EXEMODE`, `SYMBOL_POINT`, `SYMBOL_DIGITS`, etc. Must handle per-symbol configuration. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI-adaptive stop-loss & take-profit** | Dynamic SL/TP based on volatility, ATR, or regime — adapts to market conditions rather than fixed pips | High | The core differentiator of Futra. Python AI suggests optimal SL/TP levels per symbol and regime. EA receives these via IPC (named pipes or shared files) and applies them. Must fall back to conservative defaults if AI is unavailable. |
| **AI regime detection** | Market regime (trending, ranging, volatile, quiet) classification drives parameter adaptation | High | Classify current market state using ML (e.g., hidden Markov models, or simpler statistical methods). Regime drives which parameter sets the AI selects. Output: discrete regime label + confidence score. |
| **AI-adaptive position sizing** | Position sizing based on account equity, recent win rate, volatility — not just fixed lot size | High | Kelly criterion, fixed fractional, or risk-per-trade models enriched with AI regime awareness. Must respect broker margin requirements (MT5 `order_calc_margin()`). |
| **AI decision log on dashboard** | Transparency into WHY the AI chose parameters — builds trust and enables debugging | Medium | Log each AI parameter decision: regime, confidence, chosen SL/TP/lot, reasoning. Store in SQLite or JSON alongside trade records. Dashboard shows this per trade. |
| **Walk-forward optimization** | Validates that backtest results aren't overfit — uses out-of-sample data | High | Split historical data into training/validation windows. Train model on in-sample, validate on out-of-sample. Rolling window approach. Essential for trusting AI model. |
| **Monte Carlo simulation** | Tests strategy robustness across randomized trade sequences | High | Resample trade order, randomize entry prices within slippage range, run thousands of iterations to get confidence intervals on drawdown and return. |
| **Notification system (alerts)** | Push notifications for critical events (drawdown threshold, AI model errors, trade execution failures) | Medium | Email, Telegram, or webhook notifications. Essential for peace of mind when running live. MT5 has built-in `SendNotification()` for push, but the AI side needs its own alerting (Python-side checks). |
| **Strategy parameter export/import** | Save, version, and reload AI parameter configurations | Low | JSON/YAML config files for AI model parameters. Allows A/B testing different regime models without code changes. |
| **Equity curve & drawdown charting** | Visual performance metrics on dashboard — far more insightful than raw trade logs | Medium | Plot equity over time, drawdown chart, monthly returns heatmap. Can use lightweight chart libs (Chart.js, lightweight-charts) on web dashboard. |
| **Performance analytics (Sharpe, Sortino, win rate, profit factor)** | Professional metrics beyond basic P&L — serious traders expect these | Medium | Sharpe ratio, Sortino ratio, max drawdown, profit factor, average win/loss ratio, expectancy. All computable from trade history. Backtrader analyzers provide these out of the box as reference implementation. |
| **Multi-timeframe analysis** | AI can look at M15, H1, H4, D1 simultaneously for better regime detection | Medium | MT5 Python API supports `copy_rates_from()` with any timeframe enum (`TIMEFRAME_M1` through `TIMEFRAME_MN1`). EA can subscribe to multiple timeframes via `iCustom` or indicator handles. |
| **Trade journal with annotations** | Manual notes alongside AI decisions — improves learning for new trader | Low | Simple text notes attached to trades. Dashboard has a comment field per trade. Helpful for developer learning. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Multi-tenant / SaaS architecture** | PROJECT.md explicitly scopes to single personal account — multi-tenant adds massive complexity (auth, tenant isolation, billing) with zero benefit for personal use | Build single-user system. If SaaS is ever needed, it's a complete rearchitect, not an extension. |
| **Crypto trading** | Out of scope per PROJECT.md — different exchange APIs, 24/7 markets, no MT5 support for crypto | Focus on forex, indices, commodities via MT5 only |
| **High-frequency trading (HFT)** | Not the target — HFT requires co-location, microsecond latency, and C++ in-memory systems | Target swing/position trading on M15+ timeframes where AI adaptation matters |
| **Real-time charting/candlestick rendering** | Massive scope — MT5 already provides full charting. Building charting from scratch is months of work | Use MT5 for chart analysis. Dashboard shows P&L/equity curves, not live candles. Charts deferred to future milestones. |
| **Manual trading from web dashboard** | Complex order routing, no clear benefit over MT5 desktop — the whole point is automated AI trading | Dashboard is monitoring-only in early milestones. Trading happens through EA only. |
| **Social/copy trading features** | Single personal account — no followers, no signal distribution | Focus on own account performance |
| **Predictive price direction model** | PROJECT.md key decision: "Adapting strategy parameters is more robust than predicting price direction" — predicting prices is a losing game for most approaches | Adapt SL/TP/position sizing parameters based on regime, don't predict "will price go up or down" |
| **Custom broker integration** | MT5 already handles broker connectivity — building OFX/FIX protocol support is venture-scale work | Use MT5 as sole broker interface. Python MT5 API covers all needed operations. |
| **Fancy ML model serving infrastructure** | Over-engineering for a personal project — no need for Kubernetes model serving, feature stores, or data lakes | Start with lightweight Python processes reading market data and producing parameters. Simple is robust. |
| **Mobile native app** | Out of scope per PROJECT.md — web dashboard with responsive design covers mobile | Progressive web app (PWA) approach if mobile access becomes important |
| **Reinforcement learning for trading** | RL for trading is notoriously unstable, overfits easily, and is extremely hard to validate — black-box decisions | Use interpretable statistical methods for regime detection and parameter adaptation. Models you can explain and debug. |
| **Real-time order book / Level 2 data** | Only useful for HFT strategies, which are out of scope; adds complexity for data pipeline | Focus on OHLCV candle data for regime detection |

## Feature Dependencies

```
MT5 Data Pipeline (foundation)
├── Historical data access (copy_rates_from)
├── Real-time tick/bar subscription
└── Account/position polling
    │
    ▼
EA Core Execution (depends on Data Pipeline)
├── Order execution (market, pending)
├── Position management (open, modify SL/TP, close)
├── Error handling & logging
└── IPC listener for AI parameters
    │
    ▼
AI Parameter Engine (depends on Data Pipeline)
├── Feature engineering (indicators, volatility, regime features)
├── Regime detection model
├── Parameter adaptation logic (SL/TP, position sizing)
└── Decision logging
    │
    ▼
Risk Management Layer (depends on EA + AI)
├── Max drawdown circuit breaker
├── Daily loss cap
├── Position size limits
├── Max open positions per symbol
└── Emergency close-all
    │
    ▼
Backtesting Framework (depends on AI + Risk)
├── Historical replay engine
├── Performance analytics (Sharpe, Sortino, drawdown)
├── Walk-forward optimization
└── Monte Carlo simulation
    │
    ▼
Paper Trading Mode (depends on EA + AI + Risk)
├── Demo account execution
├── Dry-run mode (no real orders)
└── Performance comparison vs backtest
    │
    ▼
Web Dashboard (depends on all above)
├── Account overview & P&L
├── Position list
├── Trade history
├── AI decision log
├── Performance charts (equity curve, drawdown)
├── Alerts configuration
└── Strategy parameter management
```

## MVP Recommendation

Prioritize:

1. **Data Pipeline + EA Core** — Can't do anything without MT5 connectivity and basic trade execution
2. **Risk Management Hard Limits** — Safety first for a new trader; max drawdown and daily loss cap are non-negotiable
3. **AI Regime Detection + Adaptive Parameters** — The core value proposition; a simple regime detector with adaptive SL/TP
4. **Backtesting** — Must validate before any live deployment
5. **Paper Trading** — Forward validation before risking real capital
6. **Web Dashboard (monitoring)** — See what the system is doing; positions, P&L, AI decisions

Defer:

- **Walk-forward optimization**: Important but can come after basic backtesting works (Medium priority, Phase 2)
- **Monte Carlo simulation**: Nice-to-have validation, not blocking MVP (Low priority, Phase 2+)
- **Notification system**: Email/Telegram alerts are convenient but not required for initial testing (Medium priority, Phase 2)
- **Trade journal with annotations**: Low complexity but also low priority — can add after dashboard basics (Low priority, Phase 2+)
- **Full web trading platform**: Explicitly deferred per PROJECT.md — evolves later

## Sources

- MT5 Python API documentation (mql5.com) — official, HIGH confidence
- MQL5 trade request structures and order types (mql5.com) — official, HIGH confidence
- Backtrader documentation (backtrader.com) — official, HIGH confidence
- backtesting.py library (8.4k stars, github.com/kernc/backtesting.py) — community, MEDIUM confidence
- QuantConnect Lean (19.1k stars, github.com/QuantConnect/Lean) — community, MEDIUM confidence
- PROJECT.md constraints and key decisions — project-specific, HIGH confidence