# Architecture Research

**Domain:** Hybrid AI-powered automated trading system for MetaTrader 5 with web dashboard
**Researched:** 2026-05-23
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Windows VPS / Local Machine                  │
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────────────────────┐  │
│  │   MetaTrader 5   │         │        Python Service            │  │
│  │   ┌──────────┐   │         │                                  │  │
│  │   │  MQL5    │◄─┼────IPC──┼─►│  ┌─────────┐  ┌────────────┐ │  │
│  │   │    EA    │   │  (Files)│  │  │ Bridge  │  │    AI      │ │  │
│  │   │          │   │         │  │  │ Module  │  │   Engine    │ │  │
│  │   │ executes │   │         │  │  │         │  │            │ │  │
│  │   │ trades   │   │         │  │  └────┬────┘  └─────┬──────┘ │  │
│  │   │ manages  │   │         │  │       │              │        │  │
│  │   │ positions │   │         │  │       ▼              ▼        │  │
│  │   └──────────┘   │         │  │  ┌─────────────────────────┐ │  │
│  │                  │         │  │  │     FastAPI Backend      │ │  │
│  │  (MT5 Terminal   │         │  │  │  ┌──────┐  ┌─────────┐ │ │  │
│  │   must be open)  │         │  │  │  │ REST │  │WebSocket│ │ │  │
│  └──────────────────┘         │  │  │  │ API  │  │  Server │ │ │  │
│                               │  │  └──────┘  └─────────┘ │ │  │
│                               │  │         │              │   │  │
│                               │  │  ┌──────┴──────────────┐│  │  │
│                               │  │  │   SQLite Database    ││  │  │
│                               │  │  │  trades, decisions,  ││  │  │
│                               │  │  │  metrics, parameters  ││  │  │
│                               │  │  └──────────────────────┘│  │  │
│                               │  └──────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ (HTTPS via reverse proxy)
                                   ▼
                         ┌──────────────────┐
                         │   Dashboard SPA   │
                         │   (Svelte +       │
                         │    Tailwind CSS)  │
                         │                   │
                         │  • Positions      │
                         │  • P&L / Equity   │
                         │  • AI Decisions   │
                         │  • Trade History   │
                         │  • Risk Status    │
                         └──────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| **MQL5 Expert Advisor** | Trade execution, position management, real-time tick monitoring, risk enforcement (last line of defense) | MQL5 code running inside MT5 terminal |
| **Python Bridge Module** | File-based IPC with EA, data pipeline orchestration, sync between MT5 Python API and EA | Python async service, reads/writes shared files in MT5's MQL5/Files directory |
| **AI Engine** | Regime detection, parameter adaptation (SL/TP/position sizing), feature engineering, model inference | Python modules using scikit-learn / PyTorch |
| **FastAPI Backend** | REST API for dashboard data, WebSocket server for live updates, authentication, serves AI decisions and trade data | FastAPI with Uvicorn, async endpoints |
| **SQLite Database** | Persistent storage for trade history, AI decisions, performance metrics, audit trail | SQLAlchemy ORM with async support; SQLite file in data/ directory |
| **Dashboard SPA** | Visual monitoring interface for positions, P&L, AI decisions, risk status, performance charts | Svelte + SvelteKit SPA, Tailwind CSS, lightweight chart libraries |
| **Reverse Proxy** | HTTPS termination, authentication gateway, exposes dashboard to internet | Caddy ( simplest for personal project, auto HTTPS) or Nginx |

### Communication Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    Component Communication Map                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MT5 EA  ◄──── File-based IPC (shared JSON files) ────►  Bridge │
│  (MQL5)            MQL5/Files/ directory                        │
│                                                                  │
│  Bridge  ◄──── MT5 Python API (inter-process) ──────────►  MT5  │
│                    mt5.initialize(), order_send(),               │
│                    copy_rates_from(), positions_get()            │
│                                                                  │
│  Bridge  ◄──── Function calls (in-process) ────────────►  AI   │
│                    Python module imports                         │
│                                                                  │
│  Bridge  ◄──── SQLAlchemy (async) ─────────────────────►  DB   │
│                    Insert trade events, AI decisions             │
│                                                                  │
│  Backend ◄──── REST API (HTTP/JSON) ─────────────────►  Client │
│                    GET /api/positions, /api/trades, etc.         │
│                                                                  │
│  Backend ◄──── WebSocket (ws://) ─────────────────────►  Client │
│                    Live position updates, AI decisions            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Recommended Project Structure

```
futra/
├── ea/                           # MQL5 Expert Advisor
│   ├── Experts/
│   │   └── FutraEA.mq5           # Main EA source
│   ├── Include/
│   │   ├── FutraParams.mqh        # Parameter definitions
│   │   ├── FutraRisk.mqh          # Risk management module
│   │   └── FutraUtils.mqh         # Utility functions
│   └── Scripts/
│       └── FutraTest.mq5          # Testing/debugging scripts
│
├── ai/                           # Python AI Engine
│   ├── __init__.py
│   ├── bridge/                   # MT5 ↔ Python communication
│   │   ├── __init__.py
│   │   ├── mt5_connector.py       # MT5 Python API wrapper
│   │   ├── file_bridge.py         # File-based IPC with EA
│   │   └── event_handler.py       # Process EA events
│   ├── features/                 # Feature engineering
│   │   ├── __init__.py
│   │   ├── indicators.py         # Technical indicators
│   │   ├── volatility.py          # Volatility features
│   │   └── regime.py              # Market regime features
│   ├── models/                   # AI models
│   │   ├── __init__.py
│   │   ├── regime_detector.py     # Regime classification model
│   │   ├── parameter_adapter.py   # SL/TP/position sizing logic
│   │   └── config.py              # Model configuration
│   ├── risk/                     # Risk management (Python side)
│   │   ├── __init__.py
│   │   └── risk_manager.py        # Drawdown limits, position sizing
│   └── core/                     # AI orchestration
│       ├── __init__.py
│       ├── engine.py              # Main AI engine loop
│       └── scheduler.py          # AI evaluation scheduling
│
├── api/                          # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Settings, environment
│   ├── dependencies.py           # DI, auth, DB sessions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── positions.py           # Position endpoints
│   │   ├── trades.py              # Trade history endpoints
│   │   ├── performance.py         # Analytics endpoints
│   │   ├── ai_decisions.py        # AI decision log endpoints
│   │   ├── risk.py                 # Risk status endpoints
│   │   └── auth.py                 # Authentication endpoints
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── position_service.py
│   │   ├── trade_service.py
│   │   ├── performance_service.py
│   │   └── ai_service.py
│   ├── models/                   # SQLAlchemy + Pydantic models
│   │   ├── __init__.py
│   │   ├── database.py            # DB engine, session factory
│   │   ├── trade.py               # Trade ORM model
│   │   ├── decision.py            # AI decision ORM model
│   │   ├── position.py            # Position snapshot model
│   │   └── schemas.py             # Pydantic request/response schemas
│   └── websocket/
│       ├── __init__.py
│       └── handler.py             # WebSocket connection manager
│
├── dashboard/                    # Svelte Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   ├── websocket.ts        # WS client
│   │   │   └── stores.ts           # Svelte stores
│   │   ├── routes/
│   │   │   ├── +page.svelte        # Dashboard home
│   │   │   ├── trades/+page.svelte # Trade history
│   │   │   ├── ai/+page.svelte     # AI decisions
│   │   │   └── settings/+page.svelte # Config
│   │   └── components/
│   │       ├── PositionTable.svelte
│   │       ├── EquityChart.svelte
│   │       ├── DecisionLog.svelte
│   │       └── RiskGauge.svelte
│   ├── static/                    # Static assets
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── package.json
│
├── shared/                       # Shared configuration
│   ├── config/
│   │   ├── trading.yaml           # Trading pairs, timeframes
│   │   ├── risk.yaml              # Risk parameters
│   │   └── ai.yaml                # AI model parameters
│   └── types/
│       └── parameters.py          # Shared parameter schemas
│
├── tests/                        # Test suite
│   ├── test_ea/                   # MQL5 tests (Strategy Tester)
│   ├── test_ai/                   # AI engine tests
│   ├── test_api/                  # API endpoint tests
│   └── test_integration/          # End-to-end tests
│
├── data/                         # Runtime data (gitignored)
│   ├── futra.db                   # SQLite database
│   ├── logs/                      # Application logs
│   └── models/                    # Saved AI model files
│
├── pyproject.toml                 # Python project config
├── requirements.txt               # Python dependencies
├── Makefile                       # Build/run commands
└── README.md
```

### Structure Rationale

- **`ea/`**: MQL5 code mirrors MT5's expected directory structure (Experts, Include, Scripts). Files in this directory are symlinked or copied to MT5's data folder.
- **`ai/`**: Python AI service organized by concern: bridge (communication), features (data transformation), models (ML), risk (safety). The `bridge/` module isolates all MT5 communication so the AI modules remain testable without MT5.
- **`api/`**: Standard FastAPI project layout with routes (HTTP), services (business logic), models (DB + schemas), and websocket handlers. Separates concerns cleanly.
- **`dashboard/`**: SvelteKit SPA with standard project structure. Routes map to dashboard sections. Components are reusable UI pieces.
- **`shared/`**: Configuration files shared between EA, AI, and API. The EA reads YAML config written by Python. Keeps single source of truth for parameters.
- **`data/`**: Gitignored runtime data — database, logs, saved models. Created at runtime, not versioned.

## Architectural Patterns

### Pattern 1: File-Based IPC Bridge (EA ↔ Python)

**What:** The MQL5 EA and Python service communicate through shared files in MT5's `MQL5/Files/` directory. Python writes parameter JSON files; the EA polls and reads them. The EA writes event JSON files; Python reads them.

**When to use:** Primary communication channel between MT5 EA and Python when real-time sub-millisecond latency is not required (parameter updates on M15+ timeframes).

**Trade-offs:**
- ✅ No MQL5 dependencies to compile (no ZeroMQ DLLs needed)
- ✅ Simple to implement and debug (just read JSON files)
- ✅ Works with MT5's sandboxed file access
- ✅ DWX Connect (the industry standard) uses this pattern successfully
- ✅ Crash-safe: Python crash doesn't affect EA execution (EA uses last known parameters)
- ⚠️ Polling-based (~5ms interval, sufficient for M15+ timeframes)
- ⚠️ Windows file system locking requires careful file write patterns
- ⚠️ Not suitable for tick-by-tick data streaming

**Example:**

```python
# ai/bridge/file_bridge.py — Python side writes parameters
import json
from pathlib import Path
from datetime import datetime

class FileBridge:
    """Write AI parameters and read EA events via shared files."""
    
    def __init__(self, mt5_files_dir: str):
        self.mt5_dir = Path(mt5_files_dir)
        self.params_file = self.mt5_dir / "futra_params.json"
        self.events_file = self.mt5_dir / "futura_events.json"
    
    def write_parameters(self, symbol: str, sl_pips: float, 
                         tp_pips: float, lot_size: float, 
                         regime: str, confidence: float):
        """Atomic write: write to temp file, then rename."""
        params = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "stop_loss_pips": sl_pips,
            "take_profit_pips": tp_pips,
            "lot_size": lot_size,
            "regime": regime,
            "confidence": confidence,
        }
        # Atomic write pattern — avoids EA reading partial file
        temp = self.params_file.with_suffix('.tmp')
        temp.write_text(json.dumps(params))
        temp.rename(self.params_file)  # Atomic on NTFS
```

```mql5
// ea/Include/FuturaParams.mqh — MQL5 side reads parameters
struct FutraParams {
    string   symbol;
    double   stop_loss_pips;
    double   take_profit_pips;
    double   lot_size;
    string   regime;
    double   confidence;
    datetime timestamp;
};

FutraParams ReadFutraParams() {
    FutraParams params;
    // Read from MQL5/Files/ directory (MT5 sandbox)
    int handle = FileOpen("futra_params.json", FILE_READ|FILE_TXT|FILE_ANSI);
    if (handle != INVALID_HANDLE) {
        string json = FileReadString(handle);
        FileClose(handle);
        // Parse JSON — MQL5 has JSON parsing via #include or manual
        ParseParamsJSON(json, params);
    }
    return params;
}
```

### Pattern 2: MT5 Python API for Data Access

**What:** Use the official `MetaTrader5` Python package to access historical data, account info, positions, and trade history. This is separate from the EA↔Python IPC — it's Python directly connecting to the MT5 terminal process.

**When to use:** Reading historical OHLCV data for backtesting, fetching account/position snapshots for the dashboard, and placing orders from Python (for backtesting or manual override).

**Trade-offs:**
- ✅ Official, well-supported API
- ✅ No custom code needed on MQL5 side
- ✅ Full access to all MT5 data (rates, ticks, positions, orders, account)
- ⚠️ Synchronous API (blocks while MT5 processes request)
- ⚠️ Requires MT5 terminal to be running and logged in on the same machine
- ⚠️ Not suitable for real-time tick-by-tick processing (use EA for that)

**Example:**

```python
# ai/bridge/mt5_connector.py
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd

class MT5Connector:
    """Wraps the MT5 Python API for data access and account queries."""
    
    def initialize(self) -> bool:
        if not mt5.initialize():
            print(f"MT5 init failed: {mt5.last_error()}")
            return False
        return True
    
    def get_historical_data(self, symbol: str, timeframe: int, 
                            bars: int) -> pd.DataFrame:
        """Fetch OHLCV data for backtesting or feature engineering."""
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None:
            raise RuntimeError(f"No data for {symbol}")
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def get_account_info(self) -> dict:
        """Current account status for dashboard."""
        info = mt5.account_info()
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "margin_free": info.margin_free,
            "profit": info.profit,
        }
```

### Pattern 3: Async Service Loop (AI Engine)

**What:** The AI engine runs as a continuous async loop that periodically evaluates market conditions, updates parameters, and writes decisions to the database. The loop uses configurable intervals per timeframe (e.g., every M15 bar close).

**When to use:** For the main AI orchestration that ties bridge, features, models, and risk together.

**Trade-offs:**
- ✅ Predictable evaluation schedule aligned with bar closes
- ✅ Decouples AI compute cadence from tick-by-tick EA execution
- ✅ Easy to add new evaluation triggers (time-based or event-based)
- ⚠️ Requires careful scheduling to avoid overlap with slow model inference
- ⚠️ Missed evaluations if service restarts mid-cycle (mitigated by stateless design)

**Example:**

```python
# ai/core/engine.py
import asyncio
from datetime import datetime

class AIEngine:
    """Main orchestration loop for the AI parameter engine."""
    
    def __init__(self, bridge: FileBridge, mt5: MT5Connector, 
                 db: AsyncSession, config: dict):
        self.bridge = bridge
        self.mt5 = mt5
        self.db = db
        self.config = config
        self.running = False
    
    async def run(self):
        """Main evaluation loop. Runs on M15 bar close schedule."""
        self.running = True
        while self.running:
            for symbol in self.config["symbols"]:
                await self.evaluate_symbol(symbol)
            # Wait for next M15 bar close
            await asyncio.sleep(self._seconds_to_next_bar())
    
    async def evaluate_symbol(self, symbol: str):
        """Full AI pipeline for one symbol."""
        # 1. Fetch latest data
        data = self.mt5.get_historical_data(symbol, mt5.TIMEFRAME_M15, 200)
        
        # 2. Compute features
        features = self.feature_engineer.compute(data)
        
        # 3. Detect regime
        regime, confidence = self.regime_detector.predict(features)
        
        # 4. Adapt parameters
        params = self.parameter_adapter.adapt(regime, confidence, 
                                                self.risk_manager)
        
        # 5. Send parameters to EA
        self.bridge.write_parameters(
            symbol, params.sl, params.tp, params.lot, 
            regime, confidence
        )
        
        # 6. Log decision
        await self.log_decision(symbol, regime, confidence, params)
```

### Pattern 4: WebSocket Push for Live Dashboard Updates

**What:** The FastAPI backend pushes real-time updates to the dashboard via WebSocket connections. The AI engine and MT5 data pipeline feed events into a shared in-memory event bus that WebSocket handlers subscribe to.

**When to use:** Any time the dashboard needs live data: position changes, new AI decisions, P&L updates, risk alerts.

**Trade-offs:**
- ✅ Real-time push without polling
- ✅ FastAPI has native WebSocket support
- ✅ Svelte handles WebSocket reconnection gracefully
- ⚠️ Must handle connection drops gracefully (auto-reconnect with backoff)
- ⚠️ Single-user means one WebSocket connection — keep it simple

**Example:**

```python
# api/websocket/handler.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    """Manages WebSocket connections for live dashboard updates."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, event_type: str, data: dict):
        """Push event to all connected clients."""
        message = json.dumps({"type": event_type, "data": data})
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.active_connections -= dead  # Clean up disconnected

# In the AI engine or bridge, when an event happens:
# await manager.broadcast("ai_decision", {"symbol": "EURUSD", "regime": "trending"})
# await manager.broadcast("position_update", {"ticket": 12345, "pnl": 12.50})
```

### Pattern 5: Fail-Safe EA with Conservative Defaults

**What:** The MQL5 EA always has conservative default parameters hard-coded. If the AI parameter file is missing, stale, or unreadable, the EA continues trading with safe defaults rather than stopping or trading recklessly.

**When to use:** Always. This is a non-negotiable safety pattern for any automated trading system.

**Trade-offs:**
- ✅ EA never stops trading due to AI service crash
- ✅ Gradual degradation — AI crash → conservative parameters, not NO parameters
- ✅ Testing friendly — can run EA without AI service
- ⚠️ Must be very careful about what "conservative defaults" means per symbol
- ⚠️ Need monitoring to detect when AI is not sending updates (dashboard alert)

**Example:**

```mql5
// ea/Experts/FutraEA.mq5
input int DefaultSL_Pips = 50;      // Conservative default SL
input int DefaultTP_Pips = 100;     // Conservative default TP
input double DefaultLotSize = 0.01; // Minimum lot size
input int MaxStalenessSeconds = 300; // 5 min — consider params stale

datetime lastParamsTime = 0;
FutraParams currentParams;

void OnInit() {
    // Start with hardcoded safe defaults
    currentParams.stop_loss_pips = DefaultSL_Pips;
    currentParams.take_profit_pips = DefaultTP_Pips;
    currentParams.lot_size = DefaultLotSize;
    currentParams.regime = "UNKNOWN";
    currentParams.confidence = 0.0;
}

void OnTick() {
    // Try to refresh AI parameters
    FutraParams newParams = ReadFutraParams();
    if (newParams.timestamp > lastParamsTime) {
        currentParams = newParams;
        lastParamsTime = newParams.timestamp;
    }
    
    // If params are stale, fall back to defaults
    bool usingAIParams = true;
    if (TimeCurrent() - lastParamsTime > MaxStalenessSeconds) {
        // Switch to conservative defaults
        currentParams.stop_loss_pips = DefaultSL_Pips;
        currentParams.take_profit_pips = DefaultTP_Pips;
        currentParams.lot_size = DefaultLotSize;
        usingAIParams = false;
        // Log: AI parameters stale, using defaults
    }
    
    // Execute trading logic with currentParams...
}
```

## Data Flow

### Primary Data Flow: Market → AI → EA → Dashboard

```
[MT5 Terminal]
     │
     │ (1) Tick data / OHLCV bars
     │     via onTick() events in EA
     │     AND mt5.copy_rates_from() in Python
     ▼
[MQL5 EA]  ──────────────────────────────────────────────┐
     │                                                     │
     │ (2) Tick events written to events file               │
     │     (futra_events.json)                              │
     ▼                                                     │
[Python Bridge] ◄─────────────────────────────────────────┘
     │
     │ (3) Raw market data fed into feature engineering
     ▼
[Feature Engineering]
     │
     │ (4) Computed features (ATR, volatility, momentum...)
     ▼
[AI Models]
     │
     │ (5) Regime classification + confidence
     │ (6) Adaptive SL/TP/position sizing
     ▼
[Risk Manager]
     │
     │ (7) Risk-adjusted parameters (capped lot, validated SL)
     ▼
[File Bridge] ──write──► [futra_params.json] ──read──► [MQL5 EA]
     │                                              applies to trades
     │
     │ (8) Log decision to database
     ▼
[SQLite Database]
     │
     │ (9) FastAPI reads decisions, trades, metrics
     ▼
[FastAPI REST + WebSocket]
     │
     │ (10) HTTP responses / WS push
     ▼
[Svelte Dashboard]
```

### Request Flow: Dashboard Query

```
[User opens dashboard]
     ↓
[Svelte SPA boots] → [WebSocket connect] → [Initial REST data fetch]
     ↓                       ↓                        ↓
[Render positions]    [Live updates]          [Load history]
     ↓                       ↓                        ↓
[Component state] ← ─ ─ ─ ─ ┘                        │
     ↓                                                │
[User navigates to trade history]                     │
     ↓                                                │
[GET /api/trades?from=&to=]  ──────────────────────► [FastAPI]
     ↓                                                    ↓
[Render trade table]  ◄──────────────────── [SQLite query]
```

### State Management

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  MT5 State   │      │ Python State  │      │ Dashboard    │
│  (EA memory) │      │ (AI Engine)   │      │ (Svelte)     │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ Positions    │ ───► │ Positions    │ ───► │ Positions     │
│ Orders       │      │ AI params    │      │ AI decisions  │
│ Account info │ ───► │ Regime state │ ───► │ P&L chart     │
│ Events       │      │ Risk status  │      │ Risk gauges   │
└──────────────┘      └──────────────┘      └──────────────┘
     │                      │                       │
     │  (shared files)      │  (database)          │  (WebSocket)
     ▼                      ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Authoritative Sources                      │
│  MT5 = source of truth for positions, orders, account        │
│  Database = source of truth for history, decisions, metrics   │
│  AI Engine = source of truth for regime, parameters            │
└──────────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **Parameter Update Flow:** Python AI → JSON file → EA polls & reads → applies to next trade. Latency: ~5-50ms (file write + EA poll). Acceptable for M15+ timeframe strategies.

2. **Event Notification Flow:** EA writes trade events (open, close, modify) → JSON file → Python Bridge reads → Database → WebSocket push → Dashboard. Latency: 1-5 seconds end-to-end.

3. **Dashboard Data Flow:** Dashboard SPA → REST API (historical data) or WebSocket (live updates) → FastAPI → SQLite or in-memory cache → serialized JSON response. Historical queries go to DB; live updates via WebSocket.

4. **Backtesting Data Flow:** MT5 Python API (`copy_rates_from`) → Pandas DataFrame → Feature Engineering → AI Model → Parameter decisions → metrics aggregation → stored results in DB.

5. **Recovery Flow:** On restart, AI Engine reads last known state from DB, reconnects to MT5, and resumes evaluation. EA falls back to hardcoded defaults during the gap.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (personal) | Current design — everything on one Windows VPS. SQLite is perfect. Single Python process. |
| 2-5 users | Upgrade SQLite → PostgreSQL. Add authentication. Same architecture otherwise. |
| Multi-tenant SaaS | NOT IN SCOPE per PROJECT.md — would require complete rearchitecture (message queues, container orchestration, multi-DB, etc.) |

### Scaling Priorities (for single-user system)

1. **First bottleneck:** Python AI service restart EA losing parameters — Mitigated by fail-safe EA defaults. Add health-check in dashboard.

2. **Second bottleneck:** SQLite write contention under heavy logging — Mitigated by async writes and WAL mode. Upgrade to PostgreSQL if it becomes an issue (unlikely for single user).

3. **Third bottleneck:** WebSocket reconnection drops during MT5 restart — Mitigated by auto-reconnect with exponential backoff in both Python bridge and Svelte client.

## Anti-Patterns

### Anti-Pattern 1: Python-Driven Trade Execution

**What people do:** Use the MT5 Python API (`order_send()`) as the primary trade execution path, with the EA reduced to a parameter listener or eliminated entirely.

**Why it's wrong:** Python is not running inside MT5's event loop. It can't react to tick events in real time. If Python crashes, the system stops trading. If Python is slow (GC pause, model inference), trades are delayed. MT5 Python API calls are synchronous — they block while waiting for MT5 to respond.

**Do this instead:** EA drives all trade execution decisions inside MT5. Python provides parameters and intelligence, but EA is the execution engine with its own safety logic. EA can trade autonomously even if Python goes down.

### Anti-Pattern 2: Over-Engineering the Communication Bridge

**What people do:** Set up ZeroMQ with PUSH/PULL/SUB socket architecture, compile MQL5 ZeroMQ bindings, manage multiple socket connections, handle reconnection logic — all before the system has proven it works.

**Why it's wrong:** ZeroMQ adds significant complexity (C++ DLLs to compile, socket ports to manage, reconnection edge cases). For parameter updates on minute timeframes, file-based IPC is simpler and proven reliable (DWX Connect uses this in production). Adding ZeroMQ before you need it complicates debugging and deployment.

**Do this instead:** Start with file-based IPC (shared JSON files in MT5's Files directory, exactly like DWX Connect). If latency profiling shows it's insufficient for specific use cases, upgrade to ZeroMQ for those specific channels. The file bridge module isolates the IPC strategy so it's swappable.

### Anti-Pattern 3: Monolithic Service Architecture

**What people do:** Put MT5 connection, AI engine, web server, and WebSocket handler all in a single synchronous Python process.

**Why it's wrong:** MT5 Python API calls are synchronous and blocking. If the AI model takes 2 seconds to evaluate, the FastAPI server can't serve dashboard requests during that time. Blocking operations poison the event loop.

**Do this instead:** Use asyncio for the web layer (FastAPI + WebSocket). Run the AI engine evaluation in a background thread or as separate async tasks. Use `asyncio.to_thread()` for synchronous MT5 API calls. The file bridge is naturally non-blocking (just file I/O, which is fast on local SSD).

### Anti-Pattern 4: Storing State Only in Memory

**What people do:** Keep all positions, trade history, and AI decisions in Python dictionaries, relying on MT5 as the persistent store.

**Why it's wrong:** If Python crashes, all AI decision history is lost. You can't analyze why the AI made specific decisions. The dashboard has nothing to show after restart. MT5's trade history can be retrieved, but AI reasoning and regime classifications are ephemeral.

**Do this instead:** Persist every AI decision, trade event, and regime classification in SQLite immediately. Use WAL mode for concurrent reads during dashboard queries. This provides audit trail, debugging capability, and dashboard data even after restarts.

### Anti-Pattern 5: Skipping the Fallback/Defaults Layer

**What people do:** Code the EA to only trade when it receives AI parameters, and stop trading entirely if the AI service disconnects.

**Why it's wrong:** The entire purpose of having an EA (MQL5 code) is that it runs 24/5 inside MT5 and can trade autonomously. If the AI goes down, you still want the EA managing existing positions (trailing stops, risk limits) and potentially trading with conservative defaults.

**Do this instead:** EA always has hardcoded safe defaults. AI parameters are enhancements, not requirements. If the AI parameter file is stale (>5 minutes old), the EA switches to defaults and flags a warning. Existing position management (SL moves, trailing stops) continues regardless.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **MT5 Terminal** | Inter-process (MT5 Python API: `MetaTrader5` package) | Requires MT5 running and logged in on same Windows machine. Initialize with `mt5.initialize()`. Synchronous API — call from thread, not event loop. |
| **MT5 EA** | File-based IPC (shared files in `MQL5/Files/`) | EA polls `futra_params.json` every tick or timer. Python writes atomically (write to .tmp, rename). DWX Connect pattern. |
| **Broker** | Via MT5 (transparent) | All broker connectivity through MT5. No direct broker API needed. MT5 handles connectivity, reconnection, order routing. |
| **DNS/HTTPS** | Caddy reverse proxy (auto HTTPS via Let's Encrypt) | Required for internet-accessible dashboard. Caddy auto-provisions TLS certificates. |
| **Notifications** | Telegram Bot API or SMTP (email) | Future: alerting for drawdown thresholds, AI errors, trade failures. Dashboard can use browser notifications as first step. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| EA ↔ Python Bridge | File-based IPC (shared JSON files) | EA reads parameters file every tick/timer. Python reads events file. Atomic writes prevent corruption. |
| Python Bridge ↔ MT5 API | Inter-process (`MetaTrader5` package) | Synchronous. Call from `asyncio.to_thread()`. Must initialize/shutdown properly. Single connection — wrap in connection manager. |
| AI Engine ↔ Database | SQLAlchemy async (aiosqlite driver) | Async DB operations. WAL mode for concurrent reads. Transactions for multi-table writes. |
| AI Engine ↔ WebSocket | In-process (Python function call) | Same process. AI engine calls `manager.broadcast()` directly. No serialization overhead. |
| FastAPI ↔ Database | SQLAlchemy async session | Dependency injection per request. Auto-commit on route completion. |
| Dashboard ↔ Backend | REST + WebSocket | REST for initial page loads and historical queries. WebSocket for live updates. JWT for auth. |
| Dashboard ↔ WebSocket | Persistent WebSocket connection | Auto-reconnect with exponential backoff. Heartbeat every 30s. Re-sync full state on reconnect. |

## Build Order & Dependencies

The components depend on each other in specific ways. This build order ensures each phase has everything it needs:

```
Phase 1: MT5 EA Core
├── No external dependencies
├── MQL5 Expert Advisor with hardcoded defaults
├── Basic order execution (buy/sell with SL/TP)
├── Position management
├── File reading (parameters.json)
└── Can run standalone with default parameters

Phase 2: Data Pipeline + Python Bridge
├── Depends on: Phase 1 (EA must be running for live data)
├── MT5 Python API connector (mt5.initialize, copy_rates_from)
├── File bridge (read/write shared files)
├── Feature engineering (indicators from OHLCV data)
└── SQLite schema + initial data storage

Phase 3: AI Parameter Engine
├── Depends on: Phase 2 (needs features from data pipeline)
├── Regime detection model
├── Parameter adaptation logic (SL/TP/position sizing)
├── Risk management layer (Python side)
├── Decision logging to database
└── Continuous evaluation loop

Phase 4: Backtesting Framework
├── Depends on: Phase 2 + 3 (needs data pipeline and AI models)
├── Historical data replay
├── Performance analytics (Sharpe, Sortino, drawdown)
├── Walk-forward validation
└── Paper trading mode (MT5 demo account)

Phase 5: Web Dashboard
├── Depends on: Phases 1-3 (needs data from all components)
├── FastAPI backend (REST + WebSocket)
├── Authentication (JWT)
├── Svelte dashboard SPA
├── Position/account/equity views
├── AI decision log
└── Performance charts

Phase 6: Risk Management Hardening
├── Depends on: All previous phases
├── Emergency circuit breakers (EA + Python)
├── Drawdown monitoring and auto-stop
├── Alert notifications (Telegram/email)
├── Dashboard risk widget
└── Comprehensive logging and audit trail
```

### Dependency Graph

```
              ┌──────────────┐
              │  MT5 EA Core │  (Phase 1)
              │  (MQL5 only) │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │ Data Pipeline │  (Phase 2)
              │ + Python Bridge│
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  AI Engine    │  (Phase 3)
              │  (Regime +    │
              │  Params)      │
              └──────┬───────┘
                     │
         ┌───────────┼───────────┐
         │                       │
  ┌──────▼───────┐      ┌──────▼───────┐
  │ Backtesting  │      │ Web Dashboard│  (Phase 5)
  │ Framework    │      │ (FastAPI +   │
  │ (Phase 4)    │      │  Svelte)     │
  └──────┬───────┘      └──────┬───────┘
         │                     │
         └──────────┬──────────┘
                    │
           ┌───────▼────────┐
           │ Risk Mgmt        │  (Phase 6)
           │ Hardening        │
           └─────────────────┘
```

## Alternative Communication Approaches (Decision Record)

### ZeroMQ (Not Recommended for Initial Build)

The DWX ZeroMQ Connector uses PUSH/PULL/SUB sockets for real-time bidirectional communication between EA and Python. It provides lower latency (~1ms vs ~5ms for file-based) and supports pub/sub patterns for tick streaming.

**Why not recommended now:**
1. Requires compiling MQL5 ZeroMQ bindings (mql-zmq + libsodium DLLs) — significant setup barrier for a developer new to trading
2. DWX ZeroMQ Connector is archived (no longer maintained); DWX Connect (file-based) is the successor
3. The project targets M15+ timeframes where 5ms parameter update latency is negligible
4. Adds deployment complexity (must manage DLL files in MT5 directories)
5. File-based IPC is proven at scale (DWX Connect uses it in production for their prop trading)

**When to consider it:**
- If you need sub-second parameter updates on M1 timeframe strategies
- If you need real-time tick streaming from EA to Python (though MT5 Python API `copy_ticks_from()` can handle most use cases)
- If you need to support multiple EAs or multiple strategy processes

### Named Pipes (Windows IPC)

Windows named pipes provide faster inter-process communication than files. MQL5 can read named pipes via the `FileOpen()` function with `FILE_READ` flag.

**Why not recommended:**
1. MQL5's named pipe support is not well-documented
2. Adds Windows-specific complexity
3. File-based is simpler, proven, and sufficient for the use case
4. Named pipes are overkill for the polling frequency we need

### MT5 Python API as Primary Execution Path (Anti-Pattern)

Using `order_send()`, `positions_get()`, etc. from Python as the primary trade execution mechanism.

**Why avoided:**
1. Synchronous API that blocks the Python event loop
2. If Python crashes, no position management happens
3. Can't react to tick events in real-time
4. The entire value of an EA is autonomous execution inside MT5's event loop

**Valid use case:** Backtesting, historical data access, and manual order management from dashboard (not automated trading).

## Sources

- DWX ZeroMQ Connector (github.com/darwinex/dwx-zeromq-connector) — HIGH confidence, proven MT4/5 ZeroMQ bridge pattern
- DWX Connect (github.com/darwinex/dwxconnect) — HIGH confidence, successor to ZeroMQ bridge, file-based IPC, MT5 native support
- MT5 Python API official documentation (mql5.com/en/docs/python_metatrader5) — HIGH confidence, official reference
- PyZMQ documentation (zeromq/pyzmq) — HIGH confidence, async patterns well documented
- FastAPI WebSocket documentation — HIGH confidence, official documentation
- SQLAlchemy 2.0 async documentation — HIGH confidence, official documentation
- DWX Connect README analysis — file-based communication pattern, ~5ms polling interval, proven production use
- MetaTrader5 Python package API reference — full data access and order management capabilities confirmed

---
*Architecture research for: hybrid AI trading system with web dashboard*
*Researched: 2026-05-23*