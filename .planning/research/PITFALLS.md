# Domain Pitfalls

**Domain:** Hybrid AI-powered automated trading system for MetaTrader 5 with web dashboard
**Researched:** 2026-05-23
**Context:** Developer new to trading, single personal account, minimal budget, hybrid MQL5 EA + Python AI + web dashboard

---

## Critical Pitfalls

Mistakes that cause capital loss, system failure, or require full rewrites.

### Pitfall 1: Overfitting AI Models to Historical Data

**What goes wrong:** The AI model produces spectacular backtest results but loses money in live trading. This is the #1 cause of failure in algorithmic trading — the model memorizes noise in historical data rather than learning genuine market patterns.

**Why it happens:** 
- Insufficient out-of-sample testing
- Iterating on strategy parameters until backtests look good (implicit optimization)
- Using too many features relative to data points
- Not accounting for market regime changes (bull/bear/sideways)
- Testing on the same data used to develop the strategy

**Consequences:** Unrealistic profit expectations → deploying with too much capital → catastrophic losses when market conditions diverge from training data.

**Prevention:**
- Strict walk-forward validation: train on period A, validate on period B, test on period C (never seen)
- Use at minimum: 60% train / 20% validation / 20% test splits
- Never optimize parameters to improve test-set performance
- Use paper trading on live data for 3+ months before real capital
- Track in-sample vs out-of-sample performance ratio — if in-sample is dramatically better, the model is overfit
- Implement regime detection: the AI should know when market conditions are outside its training distribution and reduce position sizes accordingly

**Detection:**
- Backtest Sharpe ratio > 2.0 is suspicious (most genuine strategies are 0.5-1.5)
- In-sample returns massively exceed out-of-sample
- Strategy only works on specific timeframes or assets it was tuned on
- Too many parameters relative to data
- Equity curve is "too smooth" — real trading has bumps

**Phase:** AI Model Development, Backtesting Framework

---

### Pitfall 2: Python-MT5 Connection Drops Silently

**What goes wrong:** The `MetaTrader5` Python package communicates with MT5 via inter-process communication (IPC). If MT5 closes, sleeps, updates, or loses connection to the broker, all Python API calls silently return `None` instead of raising an exception. The AI keeps sending "parameters" that are never received by the EA, or the AI reads stale/None data and makes catastrophic decisions.

**Why it happens:**
- MT5 terminal closes (auto-update, Windows restart, crash)
- MT5 loses broker connection (internet outage)
- MT5 goes to "sleep" (Windows power settings, screensaver)
- MT5 terminal locks or the user minimizes it in certain ways
- The Python process crashes and restarts without re-initializing
- The IPC pipe breaks silently — no exception raised, just `None` returns

**Consequences:** 
- EA runs with stale or no AI parameters, potentially trading blindly
- AI makes decisions on stale market data
- Positions may be opened without proper stop-losses
- Complete loss of system supervision

**Prevention:**
- **Wrap every MT5 API call** with explicit `None` checks and reconnection logic
- Implement a heartbeat protocol: Python sends a timestamp to the EA every N seconds; EA verifies recency
- Auto-reconnect with exponential backoff on `mt5.initialize()` failure
- Monitor `mt5.last_error()` after every failed call
- Run a separate watchdog process that monitors both Python and MT5
- Disable Windows sleep/hibernate on the trading machine
- Set MT5 to "keep-alive" and prevent it from closing programs on update
- Add explicit health-check endpoints to the web dashboard

**Detection:**
- `mt5.copy_rates_from()` returns `None`
- `mt5.positions_get()` returns `None`  
- `mt5.account_info()` returns `None`
- EA receives no heartbeat from Python for >threshold seconds
- Web dashboard shows stale timestamps

**Phase:** Data Pipeline (EA ↔ AI), Deployment

---

### Pitfall 3: Misunderstanding Lot Sizes, Leverage, and Margin

**What goes wrong:** Position sizing miscalculation leads to opening positions far larger than intended. In forex, 1 standard lot = 100,000 units of the base currency. Opening "1 lot" on EURUSD is a €100,000 position — with 1:100 leverage, that requires €1,000 margin. At 1:500 leverage, only €200 margin, but the P&L per pip is still $10/pip for a standard lot.

**Why it happens:**
- Developer confuses "lots" with "units" (1 lot ≠ 1 unit)
- Doesn't account for leverage in risk calculation (leverage amplifies both gains AND losses)
- Doesn't understand margin vs. free margin (cannot open new positions when margin is exhausted)
- Assumes pip values are the same across all symbols (they're not — USDJPY pip value ≈ $6.50/lot vs EURUSD $10/lot)
- Calculates risk as percentage of equity but uses account leverage instead of actual position risk
- Ignores the fact that different brokers have different lot step sizes (0.01, 0.1, 1.0)

**Consequences:**
- Account blown in a single trade (position 100x larger than intended)
- Margin call — broker forcefully closes positions at worst possible time
- Multiple correlated positions create hidden leverage far exceeding apparent exposure

**Prevention:**
- **Always use `order_calc_margin()` and `order_calc_profit()`** from the MT5 Python API before placing orders
- Use the `symbol_info` API to get `trade_lot_step`, `volume_min`, `volume_max` per symbol
- Implement position sizing as: risk_amount / (stop_loss_pips × pip_value) → then round to lot_step
- Cap maximum position size in the EA regardless of what the AI suggests
- For a new trader: start with micro lots (0.01) until the math is verified in live
- Calculate and display margin utilization before every trade
- Implement hard maximum-lots-per-symbol and maximum-total-exposure limits in the EA

**Detection:**
- Position notional value > X% of account (e.g., >50%)
- Margin level below 200%
- Single trade risking >2% of account equity
- Multiple positions on correlated pairs (EURUSD + GBPUSD are heavily correlated)

**Phase:** Risk Management, EA Development

---

### Pitfall 4: Unrealistic Backtesting Assumptions

**What goes wrong:** Backtest shows high profitability, but live trading loses money due to unrealistic assumptions embedded in the backtest engine.

**Why it happens:**
- **Fixed spread:** Backtests often use fixed spreads, but live spreads widen dramatically during news events and low liquidity
- **No slippage:** Real execution gets worse prices than backtest assumes, especially on market orders
- **Instant execution:** Backtests assume fills happen at the exact price; in reality, orders queue and experience latency
- **Commission/swap not modeled:** Ignoring broker commissions and overnight swap charges kills profitability
- **Tick interpolation:** MT5 Strategy Tester uses "Every tick" mode that generates synthetic ticks from M1 bars — not real tick data
- **Survivorship bias:** Only testing on symbols/periods that were profitable, skipping those that weren't
- **Data gaps:** Missing bars during broker downtime, holidays, or illiquid periods
- **Look-ahead bias:** Inadvertently using future data (e.g., using bar close price to decide at bar open)

**Consequences:** Strategy that appears to generate 20% annual returns in backtesting loses money in live trading because real execution costs, slippage, and spread widening eat the margin.

**Prevention:**
- Use tick data (not interpolated) for backtesting when possible
- Model variable spreads with spread multipliers (2x-5x during news events)
- Add realistic commission per trade (check your broker's fee schedule)
- Include swap/overnight costs for positions held >1 day
- Model slippage: assume 1-3 pips per trade depending on liquidity
- Test across multiple market regimes (trending, ranging, volatile, calm)
- Use walk-forward analysis: optimize on period A, test on period B
- Add "slippage buffer" to stop-losses (add 0.5-1 pip to allow for execution gaps)
- Verify backtests by comparing MT5 Strategy Tester results with Python-only backtests

**Detection:**
- Strategy is profitable in backtest but unprofitable after adding 1-2 pip slippage
- Profit concentrates in a few trades (fragile)
- Strategy only works on M1 timeframe with tight stops (spread dominates)
- Returns disappear when spread is doubled
- Strategy profitability differs significantly between "Every tick" and "1 minute OHLC" MT5 testing modes

**Phase:** Backtesting Framework

---

### Pitfall 5: No Kill Switch or Emergency Shut-Down Mechanism

**What goes wrong:** Something goes wrong (bug, AI malfunction, market crash) and there's no way to instantly stop all trading. The system keeps opening positions or moving stop-losses, compounding losses.

**Why it happens:**
- No concept of "emergency stop" was designed in from the start
- Kill switch requires manual intervention in MT5 (remove EA from chart), which requires physical access
- No maximum-drawdown circuit breaker
- No daily loss limit
- EA doesn't check for a "stop trading" signal from the AI
- No way to trigger kill switch via web dashboard remotely

**Consequences:** Uncontrolled losses during a bug or market event. With leverage, losses can exceed account balance (negative balance protection varies by broker/jurisdiction).

**Prevention:**
- **Design the kill switch FIRST, before any trading logic.** It should:
  - Close all open positions immediately
  - Cancel all pending orders
  - Prevent new positions from being opened
  - Be triggerable from: (a) the EA itself, (b) the AI process, (c) the web dashboard, (d) a simple file/command flag
- Implement max drawdown limits (e.g., stop trading if equity drops >10% from peak)
- Implement daily loss limits (e.g., stop trading if daily P&L < -3%)
- The EA should check for "trading enabled" flag on every tick BEFORE executing any trade
- The web dashboard should have a prominent "PAUSE TRADING" and "CLOSE ALL" button
- Test the kill switch in paper trading before any live trading

**Detection:**
- No way to stop the system without physical access to the MT5 machine
- Positions accumulate beyond intended limits
- No monitoring in place for drawdown thresholds

**Phase:** EA Development (Phase 1), Risk Management

---

## Moderate Pitfalls

### Pitfall 6: type_filling Broker Incompatibility

**What goes wrong:** `mt5.order_send()` fails with `TRADE_RETCODE_INVALID_FILLING` (error 10030) because the `type_filling` parameter doesn't match the broker's execution type. Different brokers support different filling policies: some require `ORDER_FILLING_FOK`, others `ORDER_FILLING_IOC`, others `ORDER_FILLING_RETURN`.

**Why it happens:** The MT5 `MqlTradeRequest` structure requires `type_filling` to match the symbol's `SYMBOL_TRADE_EXEMODE`. The example code in documentation uses `ORDER_FILLING_RETURN`, but many brokers (especially ECN/STP) don't support it.

**Prevention:**
- At startup, query `symbol_info(symbol).filling_mode` for each traded symbol
- Use the correct filling type based on the symbol, not a hardcoded value
- Always call `order_check()` before `order_send()` to validate the request
- Implement filling-type auto-detection in the EA/Web API layer

**Phase:** EA Development, Order Execution

---

### Pitfall 7: Symbol Not in Market Watch

**What goes wrong:** `mt5.symbol_info()` returns `None` or `mt5.copy_rates_from()` returns no data for a symbol, even though it exists. The cause: the symbol hasn't been added to MT5's Market Watch window.

**Why it happens:** The Python API can only access data for symbols that are in the Market Watch. MetaTrader does not load data for symbols that aren't "watched." This is a per-session setting — if MT5 restarts, symbols may need to be re-added.

**Prevention:**
- Call `mt5.symbol_select(symbol, True)` before accessing any symbol's data
- Do this in the initialization routine, not just on first use
- After any `mt5.initialize()` or reconnection, re-add all required symbols
- Verify `symbol_info` is not `None` after selection
- Store a list of required symbols in configuration and re-register them on every startup

**Detection:** `symbol_info()` returns `None` for a known-valid symbol name.

**Phase:** Data Pipeline, EA ↔ AI Communication

---

### Pitfall 8: Race Conditions Between AI and EA

**What goes wrong:** The AI sends updated parameters (e.g., new stop-loss level) but the EA reads stale parameters, or the EA opens a trade while the AI is still computing parameters. This is particularly dangerous when the AI modifies stop-loss targets on an existing position.

**Why it happens:** The hybrid architecture means two separate processes communicate asynchronously. There's no built-in transaction guarantee. File-based or pipe-based IPC doesn't have atomic read/write unless explicitly designed for it.

**Consequences:** 
- EA applies a stop-loss from a previous cycle while the AI has computed new, tighter one
- EA opens a position the AI intended to be a "do not trade" signal
- Multiple trades opened for the same signal (double-execution)

**Prevention:**
- Use a parameter protocol with version numbers/timestamps — EA only acts on "fresh" parameters
- Implement a command-response pattern: AI sends parameters, EA acknowledges
- Use file-based IPC with atomic writes (write to temp file, then rename — OS guarantees atomic rename)
- Add a "signal ID" — the EA deduplicates by checking if it already acted on this signal
- The EA should never act on the same signal twice; track processed signals
- Add a thin coordination layer (e.g., a simple file-based state machine or named pipe with locks)

**Phase:** Data Pipeline (EA ↔ AI), AI Model Development

---

### Pitfall 9: Look-Ahead Bias in Feature Engineering

**What goes wrong:** The AI model uses features that include information not available at the time of the trading decision. For example, using the current bar's close price to decide whether to trade at the bar's open — the close isn't known until the bar finishes.

**Why it happens:**
- Using close-to-close returns as features when the model predicts at bar open
- Using smoothed indicators (moving averages, etc.) that calculate on the full bar
- Training features on data that includes future information (e.g., next bar's volume)
- Not properly time-aligning features and labels
- Backtesting engine uses "open" price to fill, but strategy actually decides at close of previous bar

**Consequences:** Model appears incredibly profitable in backtest but is worthless in live trading because the "edge" came from information from the future.

**Prevention:**
- **Explicit time boundary:** Every feature must use only data available at time T. Decision at T can only use data from T-1 and earlier
- Label must be: "If I decide at time T, what is the return from T to T+N?"
- Never use the current bar's OHLC as features for a decision made at the current bar's open
- Use `shift(1)` in pandas to lag features by one period
- Audit feature pipeline: for each feature, verify it only uses past data
- In backtesting, always enter at the next bar's open after signal bar

**Detection:**
- Impossible profitability (Sharpe > 3, win rate > 80% with meaningful returns)
- Performance degrades dramatically when features are shifted by 1 bar
- Strategy works perfectly in backtest but immediately fails in paper trading

**Phase:** AI Model Development, Backtesting Framework

---

### Pitfall 10: Drawdown Spirals (Not Reducing Size After Losses)

**What goes wrong:** After a drawdown, the system continues trading at the same position size. If risking a fixed dollar amount per trade during a drawdown, each loss represents a larger percentage of the shrinking capital, creating a death spiral. With $10K, a $1K loss is 10%. With $9K, the next $1K loss is 11.1%. At $5K, it's 20%.

**Why it happens:**
- Fixed lot sizing regardless of account equity
- Risk management uses absolute dollar amounts, not percentages
- No Equity Curve trading — system doesn't pause during drawdowns
- Martingale tendencies baked into the strategy (increase size after loss to "recover")

**Consequences:** Account drawdown accelerates. A 20% drawdown becomes 40%, then 60%, then account destroyed. Recovery from large drawdowns requires disproportionately large gains (need +100% to recover from -50%).

**Prevention:**
- **Always size positions as a percentage of current equity** — as equity drops, position size automatically decreases
- Implement drawdown circuit breakers: reduce position size by 50% after 10% drawdown, stop trading after 20%
- The AI should have a "caution mode" that reduces exposure during drawdowns
- Never use Martingale or reverse-Martingale sizing
- Track equity curve and disable trading when equity curve is below its moving average

**Detection:**
- Position sizes stay constant as equity drops
- No drawdown threshold triggers exist
- System is "chasing losses" (increasing position size after losing trades)

**Phase:** Risk Management, AI Model Development

---

### Pitfall 11: MT5 Terminal Must Be Running for Python API

**What goes wrong:** The Python `MetaTrader5` package communicates via IPC with the MT5 terminal. The MT5 application GUI must be open and logged in. The Python API will not work without it. If the terminal closes, crashes, or Windows restarts, all Python-MT5 connectivity dies.

**Why it happens:** The `MetaTrader5` Python package is not a standalone API — it's a bridge to an already-running MT5 terminal process. This is a fundamental architectural constraint.

**Consequences:** System goes offline without warning. No monitoring, no trading, no data. The web dashboard shows stale data with no indication that the system is down.

**Prevention:**
- Configure Windows to never sleep/hibernate when the trading system is active
- Set MT5 to start on Windows boot (registry startup entry)
- Implement a watchdog that relaunches MT5 if it closes
- Add "last heartbeat" monitoring to the web dashboard — show clear "SYSTEM OFFLINE" when no recent data
- Consider running MT5 on a VPS (MQL5 VPS is cheap at ~$15/month and designed for this)
- Write a startup script that launches MT5, waits for login, then launches the Python AI process

**Detection:**
- `mt5.initialize()` returns `False`
- Web dashboard "last update" timestamp is stale (>1 minute old)
- No recent trade history updates

**Phase:** Deployment, Data Pipeline

---

### Pitfall 12: Web Dashboard Security Exposes Trading Account

**What goes wrong:** The web dashboard, designed for remote monitoring, exposes trading account information, positions, and potentially trading capabilities to unauthorized access. If the dashboard is internet-accessible and has an API for placing trades, a compromised dashboard means a compromised trading account.

**Why it happens:**
- Basic auth over HTTP (credentials sent in cleartext)
- API keys stored in frontend JavaScript
- No rate limiting on login attempts
- WebSocket connections without authentication
- Trading API endpoints (if they exist) without proper authorization
- Dashboard running on a VPS with default SSH credentials
- CORS misconfigured to allow any origin

**Consequences:** Full account compromise — attacker can open positions, close positions, drain the account through adverse trading.

**Prevention:**
- **Separation of concerns:** The initial dashboard is READ-ONLY (monitor only). No trade execution from the dashboard.
- Use HTTPS everywhere (TLS termination with nginx/Caddy)
- Implement proper authentication (JWT with short expiry, or session-based)
- Rate-limit login attempts
- WebSocket connections require authentication token
- Store API keys server-side only, never in frontend
- Use a VPN or SSH tunnel for initial development instead of exposing to the internet
- When trade execution API is eventually added, require 2FA and a separate confirmation step
- Run the dashboard behind a reverse proxy with proper security headers

**Detection:**
- Dashboard accessible without login
- API endpoints lack authentication
- Credentials stored in plain text or frontend code
- No HTTPS

**Phase:** Web Dashboard, Deployment

---

## Minor Pitfalls

### Pitfall 13: MT5 Strategy Tester vs Python Backtest Discrepancy

**What goes wrong:** The backtest results from the MT5 Strategy Tester differ from the Python backtest. Small differences compound over hundreds of trades, leading to different conclusions about strategy viability.

**Prevention:**
- Use the same time zone for both (MT5 builds bars in broker server time, Python may use UTC)
- Ensure both use the same spread assumptions
- Align time boundaries (both enter/exit at the same bar boundaries)
- Model commissions identically in both systems
- Cross-validate: run a simple strategy (buy and hold) in both and verify equity curves match
- Treat the MT5 Strategy Tester as the "source of truth" for EA performance since it can model tick-by-tick

**Phase:** Backtesting Framework

---

### Pitfall 14: Survivorship Bias in Symbol Selection

**What goes wrong:** Training the AI only on symbols that currently exist and are actively traded. Delisted symbols, renamed symbols, and symbols that became too illiquid to trade are missing from historical data.

**Prevention:**
- Be aware that MT5 historical data may not include all delisted symbols
- Cross-asset strategies (forex + indices + commodities) have less survivorship bias since the major indices and commodities rarely delist
- Document which symbols are included in training data and why
- Don't cherry-pick the best-performing symbols after seeing results

**Phase:** AI Model Development

---

### Pitfall 15: Symbol Name Mismatches Between EA and AI

**What goes wrong:** The EA uses symbol names like "EURUSD" but the AI uses "EUR/USD" or "eurusd" or the broker adds a suffix like "EURUSDm" or "EURUSD.raw". Symbol names must match exactly between the two systems.

**Prevention:**
- Define a canonical symbol format (e.g., exactly what the broker uses) and use it everywhere
- Create a symbol mapping configuration file that maps broker symbols to AI symbols
- Validate symbol names on both sides during initialization
- Use `symbol_info()` to verify the symbol exists at runtime

**Phase:** Data Pipeline, Configuration Management

---

### Pitfall 16: Swap/Rollover Costs Eroding Profitability

**What goes wrong:** Positions held overnight incur swap (rollover) charges that are not visible in day trading backtests. For strategies that hold positions for multiple days, swap can be the difference between profit and loss.

**Prevention:**
- Query the swap rate for each traded symbol via `symbol_info().swap_long` and `swap_long`/`swap_short`
- Include swap calculations in backtesting (especially for positions held >24 hours)
- Wednesday is "triple swap day" (covers weekend) — model this
- Some pairs have negative swaps in both directions — always check
- Display estimated daily swap cost on the dashboard

**Phase:** Backtesting Framework, Risk Management

---

### Pitfall 17: Stop Level Minimums Violated

**What goes wrong:** The broker rejects orders because stop-loss or take-profit levels are too close to the current price. Each symbol has a minimum `SYMBOL_TRADE_STOPS_LEVEL` and `SYMBOL_TRADE_FREEZE_LEVEL` that must be respected.

**Prevention:**
- Always query `symbol_info_integer(symbol, SYMBOL_TRADE_STOPS_LEVEL)` before setting SL/TP
- Add a small buffer (5-10 points) above the minimum stop level
- During high volatility (news events), stop levels may dynamically increase — check before each order
- In the EA, calculate minimum stop distance and reject AI parameters that violate it

**Phase:** EA Development, Order Execution

---

### Pitfall 18: MT5 Auto-Update Breaks the System

**What goes wrong:** MT5 automatically updates and restarts, causing the EA to stop, the Python connection to drop, and trading to halt.Updates may change MQL5 behavior or change the terminal's IPC behavior.

**Prevention:**
- In MT5, disable auto-updates: Tools → Options → Updates → uncheck auto-update
- If updates are mandatory, set them to occur only during non-trading hours (weekends)
- Implement startup routines: after any MT5 restart, the EA auto-attaches, Python reconnects, and the system validates positions
- Keep a startup configuration file so the system can restore state after restarts
- Monitor MT5 version changes in the Python watchdog

**Phase:** Deployment

---

### Pitfall 19: Decimal Precision Errors in Order Prices

**What goes wrong:** Order prices with incorrect decimal places are rejected by the broker. EURUSD has 5 decimal places (1.10010), USDJPY has 3 (110.010), XAUUSD has 2 (1950.50). Sending `1.1001` instead of `1.10010` or `110.01` instead of `110.010` causes `TRADE_RETCODE_INVALID_PRICE`.

**Prevention:**
- Always use `NormalizeDouble(price, symbol_info.digits)` in MQL5
- In Python, use the `symbol_info()` `_digits` field to determine precision
- Create a helper function that formats prices to the correct number of decimals
- Never hard-code the number of decimal places

**Phase:** EA Development, Order Execution

---

### Pitfall 20: Confusion Between Orders, Deals, and Positions

**What goes wrong:** MT5 has three distinct concepts: Orders (pending requests), Deals (completed transactions), and Positions (net result of deals). A beginner confuses "positions" with "orders" and checks the wrong collection, leading to duplicate trades or failing to close existing positions.

**Why it happens:** In MT5, a "Position" is the net holdings. A "Deal" is a completed transaction. An "Order" is a request that may or may not be completed. On netting accounts, multiple deals on the same symbol merge into a single position. On hedging accounts, each deal creates a separate position.

**Prevention:**
- Use `positions_get()` to check open positions (not `orders_get()` which is for pending orders)
- Use `history_deals_get()` for trade history (not `history_orders_get()`)
- When closing a position, you must specify the position ticket
- Understand your account type: netting (one position per symbol) vs hedging (multiple positions per symbol)
- The `magic` field in orders/deals is crucial for filtering only your EA's trades

**Phase:** EA Development, Data Pipeline

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| EA Development | Kill switch not designed first | Design kill switch before any trading logic; add "close all" and "pause" |
| EA Development | Wrong `type_filling` for broker | Query `filling_mode` per symbol at startup |
| EA Development | Decimal precision in order prices | Use `_digits` from `symbol_info()` |
| EA Development | Confusing orders/deals/positions | Write clear wrapper functions with documentation |
| Data Pipeline | Python-MT5 silent disconnections | Wrap every API call with `None` check + reconnect |
| Data Pipeline | Symbol not in Market Watch | Call `symbol_select()` on startup for all symbols |
| Data Pipeline | Race conditions EA ↔ AI | Use versioned parameters with timestamps |
| AI Model | Overfitting | Walk-forward validation, out-of-sample testing |
| AI Model | Look-ahead bias | Audit every feature for time leakage; shift features by 1 bar |
| AI Model | Regime change | Monitor model input distribution; reduce position size on distribution shift |
| Backtesting | Unrealistic spread/commission assumptions | Model variable spreads, commissions, slippage |
| Backtesting | Survivorship bias | Test across all available symbols, not just profitable ones |
| Backtesting | MT5 tick interpolation | Use real tick data for final validation |
| Risk Management | Position sizing math errors | Always use `order_calc_margin()` before placing orders |
| Risk Management | No drawdown circuit breakers | Hard-code maximum drawdown (10-20%) that stops all trading |
| Risk Management | Correlation risk across "diversified" pairs | Check correlation matrix before opening positions on similar pairs |
| Web Dashboard | Security exposure | Start with read-only dashboard; proper auth; HTTPS only |
| Web Dashboard | Stale data with no warning | Show "last updated" timestamp on every data element |
| Deployment | MT5 auto-update stops the system | Disable auto-updates; add watchdog restart procedures |
| Deployment | Windows power settings cause sleep | Configure power settings to never sleep |
| Deployment | No VPS — home internet unreliable | Budget for VPS ($10-20/month) before live trading |
| Trading Newbie | Lot size misunderstanding | Start with micro lots (0.01); use `order_calc_margin()` |
| Trading Newbie | Not understanding leverage vs. margin | Learn: margin = lot size × contract size / leverage; free margin = equity - used margin |
| Trading Newbie | Ignoring spread impact | On scalping strategies, spread can exceed profit target |
| Trading Newbie | Not understanding swap/overnight fees | Check swap rates before holding positions overnight |

---

## Developer-New-to-Trading Specific Warnings

These are unique to this project because the developer is new to trading. They are the most likely to cause real financial loss.

### ⚠️ Trading Is Not Like Software Engineering

Trading has fundamental differences from software development that newcomers often underestimate:

1. **Non-deterministic environment:** Your code can be perfect and you can still lose money. Bug-free code ≈ correct strategy are not the same thing.
2. **Real financial consequences:** A bug in a trading system costs real money instantly. There is no "rollback."
3. **Market hours matter:** Forex trades 24/5 but with varying liquidity. Sunday open and Friday close have wider spreads. News events create extreme volatility.
4. **The market can stay irrational longer than you can stay solvent:** Even a correct strategy can lose during drawdowns.
5. **Paper trading ≠ live trading:** Demo accounts use simulated execution with no slippage. Live accounts experience real slippage, rejections, and requotes.

### ⚠️ Leverage Is a Double-Edged Sword

- 1:100 leverage means 1% market move = 100% of your margin
- 1:500 leverage means 0.2% market move = 100% of your margin
- A "small" 50-pip move on EURUSD with 1 standard lot = $500 profit/loss
- **Always calculate maximum loss before opening any position**

### ⚠️ The Spread Is Your First Enemy

- EURUSD typical spread: 0.1-0.5 pips (liquid)
- GBPJPY typical spread: 1-5 pips (less liquid)
- During news, spreads can widen to 10-50+ pips
- If your strategy's average profit per trade is 5 pips and the spread is 2 pips, 40% of your expected profit is the spread
- **Net profit = gross profit - spread - commission - swap**

### ⚠️ Paper Trade for Minimum 3 Months

- Before risking real money, run the system on a demo account for at least 3 months
- 3 months covers multiple market conditions and at least one month-end/quarter-end
- Compare paper trading results to backtest results — significant divergence indicates a problem
- Only deploy real capital if paper trading performance is acceptable

---

## Sources

- **MQL5 Official Documentation** — Trade request structure, Python API, order types, symbol info (HIGH confidence)
- **MT5 Python MetaTrader5 package** — Official API reference, initialize/shutdown, order_send, handling None returns (HIGH confidence)
- **mt5linux package** — Confirmed Windows-only limitation of official package, IPC architecture, reconnection needs (HIGH confidence)
- **MyLibs for MetaTrader 5 (mt5-quant-lib)** — ATR-based trailing stops, drawdown control, lot correction factors — confirms common risk management patterns (MEDIUM confidence)
- **MT5 book (MQL5 Programming for Traders)** — CopyTicks tick data handling, gap handling, tick data API (HIGH confidence)
- **Algorithmic trading community knowledge** — Overfitting, look-ahead bias, survivorship bias, regime change, position sizing pitfalls (HIGH confidence — widely documented across QuantConnect, Quantopian archives, algorithmic trading forums)
- **Author domain expertise** — MT5 architecture constraints, broker-specific filling types, Windows deployment specifics (HIGH confidence)