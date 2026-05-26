# Validation Phase Research

**Phase:** 03-validation
**Researched:** 2026-05-26
**Confidence:** HIGH

## Research Question

How should Phase 3 validate the AI+EA trading system through backtesting, walk-forward analysis, Monte Carlo simulation, and paper trading before live capital is risked?

## Standard Architecture

### Backtesting: Python Simulation, Not MT5 Strategy Tester

The EA (MQL5) cannot run outside MT5. The MT5 Strategy Tester is slow, non-programmable from Python, and cannot integrate with our AI pipeline (features → regime → adapted parameters). The standard approach for hybrid systems is to **simulate the EA's trade logic in Python** using the same AI pipeline and historical data.

**What we simulate:**
- AI parameter generation (features → RegimeDetector → ParameterAdapter)
- EA trade execution logic (at bar close: check risk gates, open/close positions at bar prices)
- Order filling with realistic constraints (spread, commission, slippage)
- Position management (SL/TP hits on intra-bar high/low)
- Risk gate enforcement (drawdown, daily loss, position limits)
- Trade logging (same JSONL format as live EA)

**What we DON'T simulate:**
- Actual MT5 order routing (no broker involved)
- Tick-level execution (bar OHLC is sufficient for H1/D1 strategies)
- Real-time order book dynamics

**Why not backtrader/vectorbt/zipline?** These are general-purpose backtesting frameworks that add abstraction layers, learning curves, and dependency overhead. Our strategy is simple — AI produces SL/TP/lot parameters at bar intervals, EA executes at next bar. A lean custom simulator (300-400 lines) directly modeling the EA logic is:
- More maintainable (same codebase, same patterns)
- More transparent (no framework magic — we see exactly what's happening)
- More testable (pure Python, no external engine dependencies)
- Better aligned with the existing TDD pattern

### Broker Realism: Spread, Commission, Slippage

Realistic cost modeling is essential — a strategy that's profitable without costs is useless.

**Spread model:**
- Use average spread from historical data when available (MT5 returns spread in OHLCV bars via `copy_rates_from_pos` — the `spread` column)
- Fallback: configurable fixed spread per symbol (EURUSD=1.0 pip, GBPUSD=1.5 pips, USDJPY=1.5 pips)
- Applied at entry AND exit (double-count — you pay spread to open AND close)

**Commission model:**
- Configurable per-symbol in account currency units
- Default: EURUSD=$7/lot round-turn (typical retail broker), GBPUSD=$7, USDJPY=$7
- Applied at entry + exit (commission is charged per side by most brokers)

**Slippage model:**
- Fixed slippage in pips (configurable per symbol, default 0.5 pips for majors, 1.0 for minors)
- Applied at entry only (market orders incur slippage; limit orders fill at limit price or better)
- Can be upgraded to random slippage sampled from a distribution in future

**Swap/rollover:**
- Overnight positions incur swap charges (configurable, default off for initial validation)
- Add later when holding periods exceed 1 day

### Bar-Level Simulation Logic

For each bar in the historical OHLCV data:

1. **Process open positions:** Check if SL/TP was hit during this bar (SL hit if low ≤ SL_price; TP hit if high ≥ TP_price). If both triggered, use bar open-to-close direction to determine which hit first (simplification: SL triggers first in a down bar, TP first in an up bar).
2. **Generate AI signal:** Run features → regime → adapted parameters at bar close. Uses the same `AIEngine.evaluate_symbol()` pipeline but with historical data, not live MT5.
3. **Check risk gates:** Simulate `IsTradingAllowed()` — drawdown check (current equity vs peak), daily loss check, position count per symbol, margin check.
4. **Open new position:** If risk gates pass and no existing position for symbol, open at bar close price + spread + slippage with adapted SL/TP.
5. **Record state:** Log trade events in JSONL format matching live format. Update equity curve.

### Performance Metrics

All metrics computed from trade history using numpy — no specialized library needed.

| Metric | Formula | What it means |
|--------|---------|---------------|
| **Sharpe Ratio** | (μ_returns - rf) / σ_returns × √252 | Risk-adjusted return. > 1.0 is good, > 2.0 is excellent (but suspicious — see Pitfall 1) |
| **Sortino Ratio** | (μ_returns - rf) / σ_downside × √252 | Like Sharpe but only penalizes downside volatility. Better for trading strategies. |
| **Max Drawdown** | max(peak - trough) / peak | Worst peak-to-trough decline. < 20% is conservative, > 40% is aggressive. |
| **Profit Factor** | Σ gross_profits / |Σ gross_losses| | Profit per unit of loss. > 1.5 is good, < 1.0 loses money. |
| **Win Rate** | wins / total_trades | Percentage of winning trades. 40-60% is typical for trend-following. |
| **Avg Win/Loss** | mean(win_sizes) / |mean(loss_sizes)| | How much bigger wins are than losses. > 1.5 is good with lower win rate. |
| **Total Return** | (final_equity - initial) / initial × 100 | Simple percentage return over the test period. |
| **Total Trades** | count of all closed trades | Sample size — too few trades (< 30) makes metrics unreliable. |
| **Calmar Ratio** | annualized_return / max_drawdown | Return per unit of worst-case pain. > 0.5 is decent. |

All metrics computed in pure Python/numpy — no external financial library dependency. The formulas are well-established and simple enough to implement correctly with unit tests.

### Walk-Forward Validation

Standard walk-forward methodology with configurable window sizes:

```
Historical data timeline:  |═══════════════════════════|
                           
Window 1:   [in-sample: 2 years][out-of-sample: 6 months]
Window 2:        [in-sample: 2 years + 6mo][out-of-sample: 6 months]
Window 3:             [in-sample: 2 years + 12mo][out-of-sample: 6 months]
...
```

**Approach: Anchored walk-forward (expanding window)**
- In-sample period grows: each window adds the previous out-of-sample period to the training data
- Out-of-sample period is fixed: always the next 6 months of unseen data
- Each window: optimize RegimeDetector thresholds on in-sample → run on out-of-sample → record metrics
- Per PITFALLS.md #1: never optimize against out-of-sample results

**What "optimizing" means for our threshold-based detector:**
- Grid search over RegimeDetector thresholds (adx_trend, adx_low, vol_high, vol_low, bb_width, bb_low, trend_ratio)
- Or: keep default thresholds and validate that they generalize (Phase 2 already chose conservative defaults)
- For Phase 3: simpler approach — run the default strategy across all windows, compute out-of-sample metrics for each, report aggregate. Grid search can come later.

**Output per window:**
- In-sample metrics (training period)
- Out-of-sample metrics (validation period)
- In-sample/out-of-sample ratio (key overfitting indicator — if IS/OOS > 2.0, strategy is overfit)

**Aggregate walk-forward report:**
- Mean out-of-sample Sharpe across all windows
- Mean out-of-sample profit factor
- Worst-window max drawdown
- IS/OOS Sharpe ratio across windows
- Pass/fail: strategy passes if mean OOS Sharpe > 0.5 AND mean OOS profit factor > 1.2 AND worst-window drawdown < 25%

### Monte Carlo Simulation

Tests strategy robustness by randomizing trade sequences. Answers: "If trades happened in a different order, would the strategy still work?"

**Approach: Trade-reshuffling bootstrap**
1. Take the list of trades from the backtest (each trade has: entry_time, exit_time, symbol, profit_loss, regime, etc.)
2. For N iterations (default 2000):
   - Randomly sample trades WITH replacement to create a synthetic trade sequence
   - Reconstruct the equity curve from this sequence
   - Compute metrics (final equity, max drawdown, Sharpe, profit factor)
3. Report distribution statistics: mean, median, 5th percentile, 95th percentile for each metric

**Why reshuffle AND bootstrap?** Trade reshuffling tells you if trade ORDER matters (does a string of losses at the start kill you?). Bootstrapping tells you if the TRADE SAMPLE is robust (what if those lucky big wins didn't happen?). Combined: robust Monte Carlo.

**Output:**
- Confidence intervals: "95% of simulations had Sharpe between X and Y"
- Worst-case: 5th percentile metrics (conservative, realistic)
- Drawdown-at-risk: 95th percentile max drawdown
- Recommended position sizing: what lot size would survive the worst 5% of simulations?

### Paper Trading Mode

Paper trading runs the EXACT same AI pipeline as production but on an MT5 demo account. The EA executes real orders — they just happen on virtual money.

**Architecture:**
```
[AI Engine] (same code as production)
     │ write_symbol_params() 
     ▼
[IPC Files] (Futra/{SYMBOL}_params.json)
     │ EA reads every tick
     ▼
[MT5 Demo Account] (separate MT5 instance, different login)
     │ EA executes orders (real execution, demo money)
     ▼
[Trade Log] (same JSONL format)
     │ backtester reads same format
     ▼
[Performance Dashboard] (Phase 4)
```

**Key differences from backtesting:**
- Real-time data, not historical
- Real spread dynamics (not modeled)
- Real order execution latency
- MT5 must be running with demo account logged in
- EA runs actual MQL5 code (not Python simulation)

**What we need to build:**
- `python/paper_trading.py` — PaperTrader class that wraps AIEngine.evaluate_symbol() and runs it on a schedule
- `python/config.py` additions — `MT5_DEMO_LOGIN`, `MT5_DEMO_PASSWORD`, `MT5_DEMO_SERVER` env vars
- EA configuration — EA is already account-agnostic; it trades whatever account MT5 is logged into. User just opens a separate MT5 instance with demo credentials.

**Paper trading is NOT:**
- A Python simulation (that's backtesting)
- A restricted mode that blocks orders (EA does real order sending — just to demo account)
- A separate codebase (same EA, same Python, different MT5 account)

## Validation Architecture

```
python/validation/
├── __init__.py
├── backtester.py        # Bar-level simulation engine (simulates EA trading logic)
├── metrics.py           # Performance analytics (Sharpe, Sortino, drawdown, profit factor, etc.)
├── walk_forward.py      # Walk-forward optimization orchestrator
├── monte_carlo.py       # Monte Carlo trade-reshuffling simulation
├── paper_trading.py     # Paper trading loop (AI engine on demo MT5 account)
└── costs.py             # Spread, commission, slippage, swap models

python/tests/validation/
├── __init__.py
├── conftest.py          # Mock fixtures (sample OHLCV data, mock trades)
├── test_backtester.py   # Backtester unit tests
├── test_metrics.py      # Metrics computation tests
├── test_walk_forward.py # Walk-forward tests
├── test_monte_carlo.py  # Monte Carlo tests
├── test_costs.py        # Cost model tests
└── test_paper_trading.py # Paper trader tests

python/config.py         # Add backtesting and validation config
```

## Features

### Feature: Cost Model (`costs.py`)

**Purpose:** Configurable, composable cost models for spread, commission, slippage, and swap.

**Behavior:**
- `SpreadModel`: Returns spread in price units for a symbol at a given time. Two implementations: `FixedSpreadModel` (constant spread from config) and `HistoricalSpreadModel` (reads spread column from OHLCV DataFrame).
- `CommissionModel`: Returns commission cost for a given trade (symbol, volume, direction). Configurable per-symbol. Default `PerLotCommissionModel`: $7/lot round-turn.
- `SlippageModel`: Returns slippage pips for a given symbol. `FixedSlippageModel` with configurable defaults (0.5 pips majors, 1.0 minors).
- `SwapModel`: Returns overnight swap cost per lot. Disabled by default (`NoSwapModel` returning 0).

**Edge cases:** None of these models require MT5 connection — all simulation-only.

### Feature: Backtesting Engine (`backtester.py`)

**Purpose:** Replays historical OHLCV data through the AI+simulated-EA pipeline, producing trade history and equity curves.

**Key design decision:** The backtester does NOT import or depend on the MT5 connector. It works entirely from DataFrames — historical data loaded once, then replayed bar-by-bar. This makes it fully testable with mock data.

**Simulation loop per bar:**
1. Update equity (unrealized P&L from open positions)
2. Check SL/TP on open positions (did price touch SL/TP this bar?)
3. Close positions where SL/TP triggered; record profit/loss
4. Apply swap to positions held overnight
5. Generate AI signal (features → regime → adapted params)
6. Run risk gates (drawdown, daily loss, position count)
7. Open new position at bar close + spread + slippage if gates pass
8. Record equity snapshot for equity curve

**Inputs:**
- OHLCV DataFrame (from data_pipeline.fetch_historical_ohlcv, or mock)
- RegimeDetector instance (from AI engine)
- ParameterAdapter instance (from AI engine)
- Cost models (spread, commission, slippage)
- Risk parameters (max drawdown, daily loss cap, max positions per symbol)
- Initial equity (default: $10,000)

**Outputs:**
- Trade list: list of dict with entry_time, exit_time, symbol, direction, entry_price, exit_price, sl_pips, tp_pips, lot_size, profit_loss, regime, confidence
- Equity curve: list of (time, equity) pairs
- Metrics report: computed by metrics.py

### Feature: Performance Metrics (`metrics.py`)

**Purpose:** Compute standard financial performance metrics from trade history and equity curve.

**Pure functions:** All functions take trades list + equity_curve list → return metric value. No state, no IO, fully testable.

**Functions:**
- `compute_sharpe_ratio(equity_curve, risk_free_rate=0.04)` → float
- `compute_sortino_ratio(equity_curve, risk_free_rate=0.04)` → float
- `compute_max_drawdown(equity_curve)` → float (percentage)
- `compute_profit_factor(trades)` → float
- `compute_win_rate(trades)` → float
- `compute_avg_win_loss(trades)` → float
- `compute_total_return(equity_curve)` → float (percentage)
- `compute_calmar_ratio(equity_curve)` → float
- `compute_all_metrics(trades, equity_curve)` → dict (all of the above)

**Formulas (implemented in pure numpy):**

```python
# Sharpe: annualized excess return / annualized volatility
daily_returns = np.diff(equity_values) / equity_values[:-1]
excess = np.mean(daily_returns) - risk_free_rate / 252
sharpe = excess / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0.0

# Sortino: uses downside deviation only
downside = daily_returns[daily_returns < 0]
sortino = excess / np.std(downside) * np.sqrt(252) if len(downside) > 0 and np.std(downside) > 0 else 0.0

# Max Drawdown
peak = np.maximum.accumulate(equity_values)
drawdown = (peak - equity_values) / peak
max_dd = np.max(drawdown)

# Profit Factor
profits = [t['profit_loss'] for t in trades if t['profit_loss'] > 0]
losses = [abs(t['profit_loss']) for t in trades if t['profit_loss'] < 0]
pf = sum(profits) / sum(losses) if sum(losses) > 0 else float('inf')
```

### Feature: Walk-Forward Validation (`walk_forward.py`)

**Purpose:** Run backtests across anchored expanding windows and aggregate results.

**Process:**
1. Split historical data into windows: first 2 years in-sample → next 6 months out-of-sample → slide
2. For each window: run backtest on in-sample (optional threshold optimization) → record IS metrics → run backtest on out-of-sample → record OOS metrics
3. Aggregate: compute mean OOS Sharpe, mean OOS profit factor, IS/OOS ratio

**Configurable parameters:**
- `in_sample_years`: 2 (default)
- `out_of_sample_months`: 6 (default)
- `timeframe`: "D1" (default — walk-forward on daily bars)
- `min_oos_trades`: 10 (minimum trades in OOS period for it to count)

**Pass/fail criteria (configurable):**
- Mean OOS Sharpe > 0.5
- Mean OOS profit factor > 1.2
- Worst-window max drawdown < 25%
- IS/OOS Sharpe ratio < 3.0 (if IS Sharpe is 3x OOS, strong overfitting signal)

### Feature: Monte Carlo (`monte_carlo.py`)

**Purpose:** Assess strategy robustness by bootstrapping trade sequences.

**Process:**
1. Take trade list from backtest
2. For N iterations (default 2000): sample trades with replacement, reconstruct equity curve, compute metrics
3. Return distribution statistics: mean, median, percentiles (5th, 25th, 75th, 95th)

**Key metric: Confidence in Profitability (CIP)**
- Percentage of Monte Carlo simulations that ended with positive total return
- CIP > 95% = high confidence the strategy is profitable

**Output:**
```
Monte Carlo Results (2000 iterations):
  Final Equity:   mean=$12,450  median=$12,200  [5th=$9,800  95th=$15,100]
  Max Drawdown:   mean=18.2%    median=17.5%    [5th=12.1%   95th=26.8%]
  Sharpe:         mean=1.15     median=1.12     [5th=0.72    95th=1.58]
  Profit Factor:  mean=1.45     median=1.42     [5th=1.18    95th=1.72]
  CIP:            87.3% (1746/2000 simulations profitable)
```

### Feature: Paper Trading (`paper_trading.py`)

**Purpose:** Run AI engine on a schedule against a live MT5 demo account.

**Architecture:** This is the SIMPLEST module — it literally just:
1. Wraps `AIEngine.evaluate_symbol()` (from Phase 2)
2. Runs it on a configurable schedule (every H1 bar close, every D1 bar close)
3. The AIEngine already writes IPC params files that the EA reads
4. The EA (on demo MT5) already reads those params and executes trades
5. That's it — paper trading IS live trading, just on a demo account

**What paper_trading.py does:**
```python
class PaperTrader:
    def __init__(self, engine: AIEngine, symbols: list[str], schedule: str = "H1"):
        self.engine = engine
        self.symbols = symbols
        self.schedule = schedule
    
    def run_cycle(self):
        """One evaluation cycle — runs AI engine across all symbols."""
        return self.engine.run_once()  # delegates to Phase 2 AIEngine
    
    def start(self):
        """Run on a loop with configurable schedule interval."""
        # Simple approach: run once, wait until next bar close, repeat
        # OR: be called by an external scheduler (cron/task scheduler)
```

**The EA already handles execution:** The MQL5 EA reads `{SYMBOL}_params.json` from the IPC directory. If the EA is attached to a demo MT5 chart, it will execute trades on the demo account. Paper trading mode is configuration, not code.

**User setup required:**
- Open a second MT5 instance logged into demo account
- Attach FutraEA to charts on that instance
- Set `FUTRA_IPC_DIR` to point to the demo MT5's `MQL5/Files/Futra/` directory
- Run PaperTrader with that IPC dir

## Dependencies & Data Flow

```
Historical OHLCV Data (DataFrame)
        │
        ▼
[costs.py] ← applies spread, commission, slippage to prices
        │
        ▼
[backtester.py] ← simulates EA trade execution at bar level
        │                    │
        │                    ▼
        │            [AI Engine] ← features → regime → adapted params
        │            (from Phase 2)
        │                    │
        ▼                    ▼
[trades list]  [equity_curve]
        │                    │
        ▼                    ▼
[metrics.py] ← computes Sharpe, Sortino, drawdown, profit factor, etc.
        │
        ▼
[walk_forward.py] ← splits data into IS/OOS windows, runs backtests
        │
        ▼
[monte_carlo.py] ← bootstraps trades, computes confidence intervals
        │
        ▼
[paper_trading.py] ← runs AIEngine on demo MT5 (real-time, real execution)
```

## Mock Testing Strategy

Per D-11: all components must be testable without live MT5 connection.

**Mock data:**
- `conftest.py` fixtures provide sample OHLCV DataFrames with realistic price data (EURUSD 1.08-1.10 range, 500 bars)
- Sample trade lists with known profit/loss values for metrics testing
- Sample equity curves with known peaks/troughs for drawdown testing

**What gets mocked:**
- MT5 connector: never imported by validation modules (backtester works from DataFrames)
- AI engine: provide mock RegimeDetector (returns fixed regime/confidence) and ParameterAdapter (returns fixed params) for backtester testing
- Paper trading: mock AIEngine.run_once() to avoid MT5 dependency

**What runs real:**
- All metrics computations (pure math, no MT5)
- Backtester simulation logic (operates on DataFrames, no MT5)
- Walk-forward orchestrator (calls backtester, no MT5)
- Monte Carlo (reshuffles trade lists, no MT5)

## Integration Points

### Inbound (consumed by validation)

| Source | What | How consumed |
|--------|------|-------------|
| Phase 1: data_pipeline.py | `fetch_historical_ohlcv()` | Backtester loads historical data before simulation loop |
| Phase 1: config.py | DEFAULT_SYMBOLS, TIMEFRAMES, IPC_DIR | Validation config extends config.py with backtesting/paper trading settings |
| Phase 2: features.py | `compute_features()` | Backtester calls features on historical OHLCV |
| Phase 2: regime_detector.py | `RegimeDetector.predict()` | Backtester classifies regime per bar |
| Phase 2: parameter_adapter.py | `ParameterAdapter.adapt()` | Backtester gets adapted SL/TP/lot per bar |
| Phase 2: engine.py | `AIEngine.evaluate_symbol()` | PaperTrader wraps engine for live runs |

### Outbound (produced for Phase 4 dashboard)

| Artifact | Format | Consumed by |
|----------|--------|-------------|
| Backtest results | JSON (metrics + trade list + equity curve) | Dashboard performance view (Phase 4) |
| Walk-forward report | JSON (window-by-window metrics) | Dashboard validation view |
| Monte Carlo report | JSON (distribution statistics) | Dashboard risk analysis |
| Paper trading trade log | JSONL (same format as Phase 1 trade log) | Dashboard trade history |

## Pitfalls (Validation-Specific)

### Pitfall 1: Look-Ahead Bias

The backtester accidentally uses data from the future (e.g., computing features for bar T using T+1 data). This makes backtest results unrealistically good.

**Prevention:** At each bar, only use data from bars 0..T (inclusive). Features like RSI, ATR use a lookback window — ensure the window doesn't peek beyond bar T. bar T's OHLC values ARE available (the bar just closed), so computing indicators on bar T is fine. The simulation checks SL/TP against bar T's high/low — this IS valid because we know the bar's range after it closes.

### Pitfall 2: Survivorship Bias in Historical Data

MT5 historical data may not include delisted symbols or periods where the symbol was untradeable.

**Prevention:** For initial validation, use only major forex pairs (EURUSD, GBPUSD, USDJPY) which have continuous trading history. Flag any data gaps in the backtest report.

### Pitfall 3: Overfitting Thresholds to Backtest

Optimizing RegimeDetector thresholds against the full historical dataset, then reporting those results as "validation." This is the #1 backtesting mistake.

**Prevention:** Strict train/test separation via walk-forward. Threshold optimization (if done) happens ONLY on in-sample data. Out-of-sample results are the ONLY results that count for validation. Report IS/OOS ratio prominently.

### Pitfall 4: Unrealistic Fill Assumptions

Assuming orders always fill at the exact requested price with no spread, commission, or slippage.

**Prevention:** Apply spread on BOTH entry and exit. Apply commission per side. Apply slippage on market orders. Use configurable, conservative defaults. Make costs immediately visible in backtest reports — not buried in footnotes.

### Pitfall 5: Too Few Trades for Statistical Significance

Running a backtest with 10 trades and declaring the strategy "proven."

**Prevention:** Minimum trade count warnings. Walk-forward reports flag windows with < 30 trades. Monte Carlo shows how vulnerable small-sample strategies are to trade sequence. Report confidence intervals, not point estimates.

## Configuration (additions to config.py)

```python
# --- Validation Configuration ---

# Backtesting
DEFAULT_INITIAL_EQUITY = float(os.getenv("FUTRA_BACKTEST_EQUITY", "10000.0"))
DEFAULT_BACKTEST_TIMEFRAME = os.getenv("FUTRA_BACKTEST_TIMEFRAME", "H1")
DEFAULT_BACKTEST_BARS = int(os.getenv("FUTRA_BACKTEST_BARS", "5000"))

# Costs
DEFAULT_SPREAD_PIPS = {"EURUSD": 1.0, "GBPUSD": 1.5, "USDJPY": 1.5}
COMMISSION_PER_LOT = 7.0  # $7 per lot round-turn
SLIPPAGE_PIPS_MAJORS = 0.5
SLIPPAGE_PIPS_MINORS = 1.0

# Walk-forward
WF_IN_SAMPLE_YEARS = 2
WF_OUT_OF_SAMPLE_MONTHS = 6
WF_MIN_OOS_TRADES = 10

# Monte Carlo
MC_ITERATIONS = 2000
MC_CONFIDENCE_LEVEL = 0.95

# Paper trading
PAPER_TRADING_INTERVAL_SECONDS = 3600  # 1 hour
MT5_DEMO_LOGIN = int(os.getenv("MT5_DEMO_LOGIN", "0"))
MT5_DEMO_PASSWORD = os.getenv("MT5_DEMO_PASSWORD", "")
MT5_DEMO_SERVER = os.getenv("MT5_DEMO_SERVER", "")
```

## What NOT to Build

| Avoid | Why | Build Instead |
|-------|-----|--------------|
| Full MT5 Strategy Tester integration | MT5 Strategy Tester is slow, GUI-based, not programmable from Python, and can't integrate with our AI pipeline | Python simulation of EA logic |
| backtrader/vectorbt/zipline | General-purpose frameworks add complexity, abstraction layers, learning curves, and dependency overhead for a simple strategy | Custom bar-level simulator (300-400 lines, directly models our EA) |
| Real-time tick data replay | Tick data is enormous (millions of ticks per symbol) and our strategy operates on H1/D1 bars. Tick-level simulation adds complexity without benefit. | Bar-level OHLCV replay |
| Portfolio-level backtesting (multi-symbol simultaneous) | Adds significant complexity. Run per-symbol backtests independently, aggregate results. Same as EA behavior — each symbol is independent. | Per-symbol backtesting with aggregation |
| Live MT5 connection for backtesting | Backtesting is historical — no live data needed. Mock-based testing is faster and more reliable. | DataFrame-based simulation |
| Optimization framework (genetic algorithms, Bayesian optimization) | Premature optimization. Default thresholds from Phase 2 should work well enough. Tuning is Phase 3+. | Grid search support (simple, transparent) — defer automatic optimization |
| Real-time paper trading dashboard | That's Phase 4 (Monitoring Dashboard). Paper trading runs headless — logs to file. | JSONL trade log (Phase 4 reads it) |

## Testing Strategy

### Unit Tests (per module)

| Module | Key Tests | Count |
|--------|-----------|-------|
| `costs.py` | Fixed spread applied, historical spread read, commission per lot, slippage per symbol | 6-8 |
| `metrics.py` | Known trades produce expected Sharpe, Sortino, drawdown, profit factor; edge cases (no trades, all wins, all losses) | 12-15 |
| `backtester.py` | Bar loop processes positions, SL hit at bar low, TP hit at bar high, position opens at bar close + spread, risk gates block over-limit, equity curve tracked | 10-12 |
| `walk_forward.py` | Window splitting correct, in-sample/out-of-sample separation, aggregate metrics | 6-8 |
| `monte_carlo.py` | Bootstrap produces N simulations, equity curves differ, percentiles correct, CIP computation | 6-8 |
| `paper_trading.py` | Wraps engine, runs on schedule, handles None results | 4-6 |

**Total: ~44-57 tests** — consistent with Phase 1 (106 tests) and Phase 2 (~45 tests planned) scale.

### Verification Tests

- Metrics match known reference values (compute Sharpe manually for a simple equity curve, compare)
- Backtester with flat prices (no movement) produces zero P&L minus costs
- Walk-forward with 1 window produces same result as single backtest
- Monte Carlo on single trade returns same result every iteration (no variance)
- Cost model with zero spread/commission/slippage produces same result as no-cost backtest

## Sources

- **Financial formulas validation:** Sharpe (1966), Sortino (1994), standard industry formulas for profit factor, max drawdown — HIGH confidence, well-established in quantitative finance
- **Walk-forward analysis:** Pardo (2008) "The Evaluation and Optimization of Trading Strategies" — standard methodology, HIGH confidence
- **Monte Carlo bootstrap:** Efron (1979) bootstrap method applied to trading — standard practice, HIGH confidence
- **MT5 Python API:** `copy_rates_from_pos()` returns spread column in OHLCV data — verified in existing data_pipeline.py, HIGH confidence
- **PITFALLS.md §Pitfall 1:** Overfitting prevention via strict IS/OOS separation with walk-forward — project-established pattern, HIGH confidence
- **Phase 1 IPC contract:** Trade log JSONL format (`ea/include/Logger.mqh` LogTrade function) — verified in existing codebase, HIGH confidence
- **Phase 2 AI interface:** RegimeDetector.predict(features) → (str, float), ParameterAdapter.adapt(regime, confidence, volatility, ...) → dict — defined in 02-01-PLAN.md, HIGH confidence
- **Bar-level simulation:** Simulating SL/TP hits from OHLC high/low is standard practice in event-driven backtesting — widely documented in trading system literature, MEDIUM confidence (implementation details vary)

---

*Research for Phase 3: Validation*
*Researched: 2026-05-26*
*Confidence: HIGH — all patterns are well-established in quantitative finance; custom Python simulation directly mirrors Phase 1-2 architecture*
