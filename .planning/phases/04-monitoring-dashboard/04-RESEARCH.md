# Monitoring Dashboard Phase Research

**Phase:** 04-monitoring-dashboard
**Researched:** 2026-05-26
**Confidence:** HIGH

## Research Question

How should Phase 4 build an authenticated web dashboard with real-time trading data, AI decision visibility, equity/drawdown charts, and push alerts — accessible from anywhere on a Windows VPS?

## Standard Architecture

### FastAPI + SvelteKit Integration Pattern

Two-tier architecture: FastAPI backend serves data via REST + WebSocket, SvelteKit frontend renders the UI. In development, Vite dev server proxies to FastAPI. In production, FastAPI serves SvelteKit's built static output.

```
┌─────────────────────────────────────────────────────────────┐
│                     Windows VPS                             │
│                                                             │
│  ┌──────────────┐    REST + WS    ┌──────────────────────┐ │
│  │   SvelteKit   │◄──────────────►│       FastAPI         │ │
│  │  (Frontend)   │                │      (Backend)        │ │
│  │              │                │                       │ │
│  │ Port 5173    │                │ Port 8000             │ │
│  │ (dev proxy)  │                │                       │ │
│  └──────┬───────┘                │  ┌─────────────────┐  │ │
│         │                        │  │  SQLite (WAL)   │  │ │
│         │                        │  │  trade_log.jsonl│  │ │
│         │                        │  │  decision_log.  │  │ │
│         │                        │  │  jsonl          │  │ │
│         │                        │  └─────────────────┘  │ │
│         │                        │                       │ │
│         │                        │  ┌─────────────────┐  │ │
│         │                        │  │  MT5 Python API │  │ │
│         │                        │  │  (positions,    │  │ │
│         │                        │  │   account_info, │  │ │
│         │                        │  │   orders)       │  │ │
│         │                        │  └─────────────────┘  │ │
│         │                        └──────────────────────┘ │
│         │                                                 │
│  ┌──────▼───────┐                                         │
│  │   Nginx      │  (reverse proxy + HTTPS)                │
│  │   Port 443   │                                         │
│  └──────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
```

**Development mode:**
- SvelteKit dev server runs on `localhost:5173`
- FastAPI runs on `localhost:8000`
- Vite proxy config forwards `/api/*` requests to FastAPI
- Vite proxy forwards `/ws/*` WebSocket connections to FastAPI

**Production mode:**
- SvelteKit builds to static files (`npm run build` → `build/` directory)
- FastAPI serves built frontend as static files alongside API routes
- Single port (8000) serves both UI and API
- Nginx reverse proxy adds HTTPS on port 443

**Why not separate servers in production:** Single-user system, no load balancing needed. SvelteKit static adapter output is just HTML/JS/CSS — FastAPI can serve them directly with `StaticFiles` middleware. Single deployment unit simplifies Windows VPS setup.

### Real-Time Updates: WebSocket

FastAPI WebSocket endpoint pushes live data to connected dashboard clients. Server pushes on state change, client subscribes per symbol.

**WebSocket message protocol:**

```json
// Server → Client messages
{"type": "positions_update", "data": {"EURUSD": {...}, "GBPUSD": {...}}}
{"type": "account_update", "data": {"balance": 10500.0, "equity": 10450.0, "margin": 1200.0, "free_margin": 9250.0}}
{"type": "trade_alert", "data": {"symbol": "EURUSD", "action": "buy", "price": 1.0850, "sl": 1.0825, "tp": 1.0900}}
{"type": "error", "data": {"message": "MT5 connection lost", "severity": "critical"}}
{"type": "pong", "data": {}}

// Client → Server messages
{"type": "subscribe", "symbols": ["EURUSD", "GBPUSD"]}
{"type": "ping", "data": {}}
```

**Update frequency:** 1-second interval for positions/account data (MT5 Python API doesn't support push — must poll). This is fast enough for a monitoring dashboard (not an HFT terminal).

**Connection lifecycle:**
- Client connects → server registers client in connection pool
- Client sends `subscribe` with symbol list → server filters updates
- Server runs background task polling MT5 every 1s → pushes to subscribed clients
- Client disconnects → server removes from pool
- Heartbeat: server sends `pong` every 30s, client reconnects if no message in 60s

**WebSocket endpoint:** `/ws` — single endpoint, message type routing.

### Data Sources

The dashboard reads from three sources:

| Data | Source | Format | Read Method |
|------|--------|--------|-------------|
| Current positions | MT5 Python API `mt5.positions_get()` | Python objects | Live API call (polled) |
| Account info | MT5 Python API `mt5.account_info()` | Python objects | Live API call (polled) |
| Trade history | `{IPC_DIR}/Futra/trade_log.jsonl` | JSONL (Phase 1 format) | File read + parse |
| AI decision log | `{CONFIG.AI_LOG_DIR}/decision_log.jsonl` | JSONL (Phase 2 format) | File read + parse |
| Equity curve | Computed from trade history | Time series array | Derived at request time |
| Strategy configs | `{CONFIG.STRATEGY_CONFIG_DIR}/*.json` | JSON (Phase 2 format) | File read |

**Phase 1 trade log format** (from `ea/include/Logger.mqh`):
```json
{"event": "trade_open", "symbol": "EURUSD", "ticket": 12345, "direction": "buy", "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900, "timestamp": "2026-05-26T10:15:00Z"}
{"event": "trade_close", "ticket": 12345, "profit": 50.0, "close_price": 1.0900, "timestamp": "2026-05-26T12:30:00Z"}
```

**Phase 2 decision log format** (from `python/ai/decision_logger.py`):
```json
{"timestamp": "2026-05-26T10:14:00Z", "symbol": "EURUSD", "timeframe": "H1", "regime": "trending", "confidence": 0.87, "sl_pips": 25.0, "tp_pips": 50.0, "lot_size": 0.05, "features": {"adx": 28.5, "atr": 0.0012, "volatility": 0.18}, "reasoning": "Strong uptrend (ADX 28.5), tight SL at 1.5x ATR, TP at 2:1 ratio"}
```

**SQLite for dashboard-specific data:** A small `dashboard.db` SQLite database stores dashboard-specific state (user auth tokens, notification preferences, cached computed data). The trade and decision logs remain file-based JSONL — no migration or duplication.

```sql
-- dashboard.db schema
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,      -- 'drawdown', 'connection_lost', 'trade_error', 'model_error'
    message TEXT NOT NULL,
    severity TEXT NOT NULL,  -- 'info', 'warning', 'critical'
    acknowledged INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Authentication Strategy

Single-user system — no multi-tenant complexity. Token-based auth is sufficient.

**Approach: Bearer token with password login**

1. User logs in with username/password → FastAPI validates against `dashboard.db` users table
2. Server generates a random bearer token (64-char hex), stores in sessions table with 24h expiry
3. Client stores token in localStorage, sends in `Authorization: Bearer <token>` header
4. FastAPI middleware checks token on every API request (except login, WS upgrade uses query param)
5. WebSocket auth: client passes token as query param `?token=xxx` during handshake
6. Password hashed with `bcrypt` (passlib library) — never stored plaintext

**Why not JWT:** Single-user, no distributed services, no public/private key infrastructure needed. Simple bearer tokens stored in SQLite are faster to implement, easier to revoke, and the session db is tiny (1 row). JWT adds complexity (key management, refresh tokens, blacklisting) with zero benefit for a single-user system.

**Why not OAuth/OIDC:** Single-user personal dashboard — no third-party login needed. Over-engineering.

**Library:** `passlib[bcrypt]` for password hashing. `python-jose` not needed (no JWT).

### Charting Library: lightweight-charts

TradingView's `lightweight-charts` is purpose-built for financial time series and ideal for equity curve + drawdown charts.

**Why lightweight-charts over alternatives:**

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **lightweight-charts** | Built for financial charts; OHLC/candlestick/line/area series; performant with 10K+ data points; pan/zoom built-in; 0 dependencies; free | Newer library (~2020), smaller ecosystem | ✅ Best fit |
| **Chart.js** | Popular, well-documented, Svelte wrappers available (svelte-chartjs) | Not designed for financial data; no built-in time axis for trading hours; candlestick plugin is third-party | Overkill for simple line charts, underpowered for financial |
| **D3.js** | Maximum flexibility, any visualization possible | Verbose (50+ lines for a simple line chart); no built-in chart types; steep learning curve | Excessive for 2 chart types |

**Integration with SvelteKit:**
- Install `lightweight-charts` npm package (no Svelte wrapper needed — it's a pure JS library)
- Create Svelte component that instantiates chart on mount, destroys on unmount
- Use `createChart(container, options)` with `onMount` lifecycle
- Update data via `ISeriesApi.setData(data[])`
- Handle resize with `chart.resize(width, height)` in a ResizeObserver

**Chart components needed:**
1. `EquityChart.svelte` — Area/line series showing account equity over time
2. `DrawdownChart.svelte` — Area series below zero line showing drawdown %

**Data format for lightweight-charts:**
```typescript
// Equity curve data
interface EquityPoint {
    time: string;  // ISO8601 date string "2026-05-26"
    value: number; // Equity value
}

// Drawdown data
interface DrawdownPoint {
    time: string;
    value: number; // Negative percentage (e.g., -5.2)
}
```

### Push Notifications

Push notifications alert the user to critical events without requiring the dashboard to be open on screen.

**Approach: Browser notifications (Web Notifications API) + in-app alert feed**

Since this is a single-user system accessed from one browser/device, browser notifications are the right level. No need for Firebase Cloud Messaging (multi-device) or email/SMS gateways (personal dashboard).

**Notification types:**

| Event | Severity | Channel |
|-------|----------|---------|
| Drawdown threshold breached | Critical | Browser notification + in-app alert |
| Daily loss limit hit | Critical | Browser notification + in-app alert |
| MT5 connection lost | Critical | Browser notification + in-app alert |
| AI model error (regime detection failed) | Warning | In-app alert only |
| Trade execution failure | Warning | Browser notification + in-app alert |
| Kill switch activated | Critical | Browser notification + in-app alert |

**Implementation:**
1. FastAPI background task monitors MT5 connection, account status, error logs
2. Critical events are pushed via WebSocket as `{"type": "alert", "data": {...}}`
3. SvelteKit client receives alert, stores in in-app alert feed, triggers `new Notification(...)` if browser permissions granted
4. User acknowledges alerts in dashboard → sent back via WebSocket → stored as acknowledged in SQLite

**Browser notification permission flow:**
- Dashboard prompts user on first visit to enable notifications
- `Notification.requestPermission()` → "granted" / "denied"
- If denied, alerts still appear in in-app feed (desktop notification is best-effort)

### Deployment: Windows VPS with HTTPS

**Production deployment architecture on Windows VPS:**

```
Windows VPS
├── MT5 (trading terminal)
├── Python AI engine (background process)
├── FastAPI + SvelteKit (web server)
└── Caddy or Nginx (reverse proxy + HTTPS)
```

**HTTPS approach: Caddy reverse proxy**
- Caddy is the simplest option for Windows — automatic Let's Encrypt certificates, zero config for HTTPS
- Caddy listens on port 443 (HTTPS), reverse-proxies to FastAPI on `localhost:8000`
- Alternative: Nginx for Windows + certbot, but Caddy has native Windows builds and simpler config

**Caddy config (Caddyfile):**
```
dashboard.futra.example.com {
    reverse_proxy localhost:8000
}
```

That's it. Caddy auto-provisions and renews Let's Encrypt certificates.

**Startup:**
- FastAPI runs as a Windows Service (via `nssm` or `pywin32`) or scheduled task on boot
- Caddy runs as a Windows Service
- User accesses `https://dashboard.futra.example.com` from any device

**Domain/DNS:**
- User needs a domain name pointing to the VPS IP (e.g., via DuckDNS for free dynamic DNS, or any domain registrar)
- Phase 4 documents the setup steps but does not automate DNS/domain purchase

**Firewall:**
- Windows Firewall rules: open port 443 (HTTPS), block port 8000 (FastAPI direct — only accessible via localhost reverse proxy)

### FastAPI Backend Structure

```
python/dashboard/
├── __init__.py
├── main.py              # FastAPI app, WebSocket endpoint, static file serving
├── auth.py              # Login/logout, token generation, auth middleware
├── api/
│   ├── __init__.py
│   ├── positions.py     # GET /api/positions — current open positions
│   ├── account.py       # GET /api/account — balance, equity, margin
│   ├── trades.py        # GET /api/trades — trade history (paginated)
│   ├── decisions.py     # GET /api/decisions — AI decision log (paginated)
│   ├── equity.py        # GET /api/equity-curve — equity curve data
│   ├── drawdown.py      # GET /api/drawdown — drawdown curve data
│   ├── alerts.py        # GET /api/alerts, POST /api/alerts/{id}/acknowledge
│   └── strategy.py      # GET /api/strategy — current strategy config
├── ws.py                # WebSocket manager (connection pool, broadcast, heartbeat)
├── db.py                # SQLite connection (dashboard.db)
├── models.py            # Pydantic models for API responses
└── notification.py      # Background alert monitor (MT5 health, thresholds)

python/tests/dashboard/
├── __init__.py
├── conftest.py          # Test fixtures: TestClient, mock MT5, test db
├── test_auth.py         # Login/logout, token validation, middleware
├── test_positions.py    # Positions endpoint tests
├── test_account.py      # Account endpoint tests
├── test_trades.py       # Trade history endpoint tests
├── test_decisions.py    # AI decision log endpoint tests
├── test_equity.py       # Equity curve computation tests
├── test_ws.py           # WebSocket connection, subscription, message format
├── test_alerts.py       # Alert creation, acknowledgment
└── test_notification.py # Background alert monitor tests

# Frontend (new directory at project root)
frontend/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── app.html
│   ├── app.css
│   ├── lib/
│   │   ├── api.ts          # API client (fetch wrappers)
│   │   ├── ws.ts           # WebSocket client (connect, subscribe, reconnect)
│   │   ├── stores.ts       # Svelte writable stores for reactivity
│   │   └── types.ts        # TypeScript interfaces (Position, Account, Trade, Decision, Alert)
│   ├── routes/
│   │   ├── +layout.svelte  # App shell (sidebar nav, auth guard)
│   │   ├── +page.svelte    # Dashboard home (account overview + positions)
│   │   ├── login/+page.svelte
│   │   ├── trades/+page.svelte
│   │   ├── decisions/+page.svelte
│   │   ├── performance/+page.svelte  # Equity curve + drawdown charts
│   │   ├── alerts/+page.svelte
│   │   └── settings/+page.svelte     # Notification prefs, strategy view
│   └── components/
│       ├── Nav.svelte
│       ├── AccountSummary.svelte      # Balance, equity, margin cards
│       ├── PositionsTable.svelte      # Open positions with real-time P&L
│       ├── TradeHistoryTable.svelte   # Paginated trade history
│       ├── DecisionLogTable.svelte    # AI decision log
│       ├── EquityChart.svelte         # lightweight-charts equity curve
│       ├── DrawdownChart.svelte       # lightweight-charts drawdown
│       ├── AlertFeed.svelte           # In-app notification feed
│       └── AlertToast.svelte          # Toast notifications
```

### SvelteKit Adapter Choice

**Static adapter (`@sveltejs/adapter-static`):** Builds to pure HTML/CSS/JS files. FastAPI serves them as static files. No Node.js runtime needed in production — just FastAPI + Uvicorn. Best fit for a single-user dashboard with server-side data.

**Not SSR (`adapter-node`):** Would require Node.js runtime alongside Python. Adds deployment complexity (two runtimes to manage on Windows VPS). Single-user dashboard doesn't benefit from SSR (no SEO, no social sharing, no large user base).

### SvelteKit + WebSocket Pattern

Svelte stores provide reactive state. WebSocket client updates stores → UI reactively updates.

```typescript
// src/lib/stores.ts
import { writable } from 'svelte/store';

export const positions = writable<Position[]>([]);
export const account = writable<Account | null>(null);
export const alerts = writable<Alert[]>([]);
export const wsConnected = writable<boolean>(false);

// src/lib/ws.ts
import { positions, account, alerts, wsConnected } from './stores';

export function connectWebSocket(token: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${token}`);
    
    ws.onopen = () => wsConnected.set(true);
    ws.onclose = () => { wsConnected.set(false); setTimeout(() => connectWebSocket(token), 3000); };
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
            case 'positions_update': positions.set(msg.data); break;
            case 'account_update': account.set(msg.data); break;
            case 'trade_alert': alerts.update(a => [...a, msg.data]); break;
        }
    };
    
    // Subscribe to all symbols (dashboard monitors everything)
    ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'subscribe', symbols: ['EURUSD', 'GBPUSD', 'USDJPY'] }));
    };
}
```

### Package Dependencies

**Python (new additions to requirements.txt):**
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
websockets>=11.0        # WebSocket support for FastAPI
passlib[bcrypt]>=1.7.4  # Password hashing
python-multipart>=0.0.6 # Form data parsing (login form)
httpx>=0.25.0           # TestClient for FastAPI tests
```

**Frontend (package.json additions):**
```json
{
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.0",
    "@sveltejs/kit": "^2.0.0",
    "svelte": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "vite": "^5.0.0",
    "typescript": "^5.0.0"
  },
  "dependencies": {
    "lightweight-charts": "^4.1.0"
  }
}
```

## Features

### Feature: FastAPI Dashboard Backend (`python/dashboard/`)

**Purpose:** REST API + WebSocket server that serves dashboard data — positions, account, trade history, AI decisions, and alerts. Runs alongside the existing Python AI engine.

**Key design decisions:**
- FastAPI app is a separate module (`python/dashboard/main.py`) — does not modify existing AI engine or data pipeline code
- All API routes require authentication (except `/api/auth/login` and WebSocket upgrade)
- MT5 connection is shared with the existing `mt5_connector.py` module — no duplicate connection
- Trade and decision logs are read from existing file paths (no data duplication)
- WebSocket runs in the same Uvicorn process as REST API (FastAPI natively supports both)

**API routes:**
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/login` | Login with username/password → returns token | No |
| POST | `/api/auth/logout` | Invalidate session token | Yes |
| GET | `/api/positions` | Current open positions with P&L | Yes |
| GET | `/api/account` | Account balance, equity, margin, free margin | Yes |
| GET | `/api/trades?limit=50&offset=0` | Trade history (paginated, from trade_log.jsonl) | Yes |
| GET | `/api/decisions?limit=50&offset=0&symbol=EURUSD` | AI decision log (paginated, filterable) | Yes |
| GET | `/api/equity-curve?days=30` | Equity curve data points for charting | Yes |
| GET | `/api/drawdown?days=30` | Drawdown data points for charting | Yes |
| GET | `/api/alerts?acknowledged=false` | Active alerts | Yes |
| POST | `/api/alerts/{id}/acknowledge` | Mark alert as read | Yes |
| GET | `/api/strategy` | Current strategy configuration | Yes |
| WS | `/ws` | Real-time WebSocket (positions, account, alerts) | Token in query param |

**Static file serving (production only):**
```python
# Serve SvelteKit build output when not in dev mode
if not DEV_MODE:
    app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
```

### Feature: SvelteKit Dashboard Frontend (`frontend/`)

**Purpose:** Responsive web dashboard with live trading data, charts, and alert feed. Built with SvelteKit + Tailwind CSS + lightweight-charts.

**Pages (routes):**

1. **Login (`/login`):** Username/password form. Token stored in localStorage. Redirects to `/` on success.

2. **Dashboard Home (`/`):** Account summary cards (balance, equity, margin, free margin, daily P&L), open positions table with real-time P&L updates, recent alerts. This is the "glanceable overview" — user sees system health in 5 seconds.

3. **Trade History (`/trades`):** Paginated trade list with filters (symbol, direction, date range). Shows entry/exit price, profit/loss, duration, regime. Exports to CSV.

4. **AI Decisions (`/decisions`):** Decision log table showing regime, confidence, parameters chosen, reasoning. Filter by symbol. Links decisions to resulting trades.

5. **Performance (`/performance`):** Equity curve chart (area/line), drawdown chart (area below zero), key metrics (Sharpe, Sortino, max DD, win rate, profit factor). Time range selector (7d, 30d, 90d, all).

6. **Alerts (`/alerts`):** Alert history with severity indicators. Filter by acknowledged/unacknowledged. Click to acknowledge.

7. **Settings (`/settings`):** Notification preferences, current strategy config view, logout button.

**UI components:**
- AccountSummary: 4 metric cards (balance, equity, margin, free margin) with colored P&L indicators
- PositionsTable: Real-time table showing symbol, direction, volume, entry, current, P&L, SL, TP
- TradeHistoryTable: Paginated table with sortable columns and CSV export
- DecisionLogTable: Expandable rows showing reasoning text
- EquityChart: lightweight-charts area series, responsive, time range selector
- DrawdownChart: lightweight-charts area series filled below zero in red
- AlertFeed: Time-ordered list with severity badges
- AlertToast: Slide-in toast for new real-time alerts
- Nav: Sidebar navigation with active state highlighting

**Responsive design with Tailwind CSS:**
- Mobile-first: sidebar collapses to hamburger on small screens
- Cards stack vertically on mobile, grid on desktop
- Tables become card lists on mobile (each row is a card)
- Charts resize with container

### Feature: Real-Time WebSocket Updates

**Purpose:** Live position and account updates without page refresh. Server pushes on change, UI reactively updates via Svelte stores.

**Server-side (FastAPI `ws.py`):**
- `ConnectionManager` class: tracks connected clients, manages subscriptions
- Background task `poll_mt5_state()`: every 1 second, calls `mt5.positions_get()` and `mt5.account_info()`, diffs against previous state, broadcasts changes to subscribed clients
- `broadcast()` method: sends message to all clients subscribed to a symbol
- Heartbeat: sends ping every 30s to detect dead connections
- Clean disconnect: removes client from pool on WebSocket close

**Client-side (SvelteKit `ws.ts`):**
- Auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
- Svelte store bindings: `positions`, `account`, `alerts`, `wsConnected`
- Connection status indicator in UI (green dot = connected, red dot = disconnected)

### Feature: Equity Curve & Drawdown Computation

**Purpose:** Compute equity curve and drawdown from trade history for charting.

**Equity curve computation:**
```python
def compute_equity_curve(trade_log_path: Path, initial_balance: float, days: int = 30) -> list[dict]:
    """Replay trades from JSONL log to build daily equity curve."""
    # 1. Read trades from trade_log.jsonl
    # 2. Sort by timestamp
    # 3. Start with initial_balance, apply each trade's profit/loss
    # 4. Record equity after each day's last trade
    # 5. Return [{time: "2026-05-01", value: 10250.0}, ...]
```

**Drawdown computation:**
```python
def compute_drawdown_curve(equity_curve: list[dict]) -> list[dict]:
    """Compute drawdown from equity curve: (peak - current) / peak * 100."""
    # Running peak tracking: peak = max(peak, current_equity)
    # Drawdown = (peak - current) / peak * 100 (as negative percentage)
    # Return [{time: "2026-05-01", value: -3.2}, ...]
```

**Edge cases:**
- No trades: return empty array, UI shows "No trading data yet"
- Single day: return one data point, chart shows it
- Large datasets (>1000 trades): aggregate to daily OHLC for performance
- Non-trading days: fill with previous day's equity value (flat line in chart)

### Feature: Authentication System

**Purpose:** Protect dashboard from unauthorized access. Single-user login with bearer token.

**Login flow:**
1. Client POSTs `{username, password}` to `/api/auth/login`
2. Server looks up user in `dashboard.db` users table
3. Server verifies password with `passlib.verify(password, stored_hash)`
4. On success: generates 64-char random hex token, stores in sessions table with 24h expiry, returns `{token, expires_at}`
5. Client stores token in localStorage
6. All subsequent requests include `Authorization: Bearer <token>` header
7. WebSocket connection passes token as `?token=` query parameter

**Auth middleware:**
```python
# FastAPI dependency
async def require_auth(request: Request, db=Depends(get_db)):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(401, "Missing token")
    session = db.get_session(token)
    if not session or session.is_expired():
        raise HTTPException(401, "Invalid or expired token")
    return session.user_id
```

**WebSocket auth:**
```python
# FastAPI WebSocket endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), db=Depends(get_db)):
    session = db.get_session(token)
    if not session or session.is_expired():
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await manager.connect(websocket, session.user_id)
```

**Initial user creation:** On first startup, if users table is empty, a setup script or documented command creates the first admin user. Not a web UI — security: you don't want a public "create admin" page.

**Security considerations (single-user system):**
- Token stored in localStorage (acceptable for single-user dashboard accessed from own devices)
- Token expiry: 24 hours, no refresh tokens (simplicity — just re-login)
- Rate limiting: not needed for single-user system
- CORS: restrict to dashboard origin in production

### Feature: Alert & Notification System

**Purpose:** Alert the user to critical trading events in real-time, both in-app and via browser notifications.

**Server-side alert generation (`notification.py`):**
```python
class AlertMonitor:
    def __init__(self, db, ws_manager):
        self.db = db
        self.ws_manager = ws_manager
        self.last_account_state = None
    
    def check_all(self):
        """Run all alert checks, create alerts for triggered conditions."""
        self.check_mt5_connection()
        self.check_drawdown_threshold()
        self.check_daily_loss()
        self.check_trade_errors()
    
    def check_drawdown_threshold(self):
        # Compare current equity vs peak equity
        # If drawdown > configured threshold → create critical alert
        pass
    
    def check_mt5_connection(self):
        # Check if mt5.terminal_info() returns None → create critical alert
        pass
```

**Alert polling:** `AlertMonitor.check_all()` runs every 10 seconds via FastAPI background task (`@app.on_event("startup")`). New alerts are persisted to SQLite and broadcast via WebSocket.

**Client-side notification:**
```typescript
function showNotification(alert: Alert) {
    // In-app: add to alert feed store
    alerts.update(a => [...a, alert]);
    
    // Browser notification (if permitted)
    if (Notification.permission === 'granted' && alert.severity === 'critical') {
        new Notification('Futra Alert', {
            body: alert.message,
            icon: '/favicon.png',
            tag: alert.type  // Deduplicate by type
        });
    }
}
```

## Dependencies & Data Flow

```
[MT5 Terminal]
    │ mt5.positions_get(), mt5.account_info()
    ▼
[FastAPI Dashboard Backend]
    │ REST API: /api/positions, /api/account, /api/trades, /api/decisions, /api/equity-curve
    │ WebSocket: live positions + account + alerts
    ▼
[SvelteKit Frontend]
    │ Svelte stores → reactive components
    ▼
[Dashboard UI: Account cards, positions table, trade history, equity chart, alerts]
```

### Inbound (consumed by dashboard)

| Source | What | How consumed |
|--------|------|-------------|
| MT5 Python API | `mt5.positions_get()`, `mt5.account_info()` | FastAPI polls every 1s for live data |
| Phase 1 trade log | `{IPC_DIR}/Futra/trade_log.jsonl` | FastAPI reads for trade history + equity computation |
| Phase 2 decision log | `{AI_LOG_DIR}/decision_log.jsonl` | FastAPI reads for AI decision display |
| Phase 2 strategy config | `{STRATEGY_CONFIG_DIR}/*.json` | FastAPI reads for settings page |
| Existing `mt5_connector.py` | `ensure_connected()` | Reused — no duplicate MT5 connection |
| Existing `config.py` | `IPC_DIR`, `DEFAULT_SYMBOLS` | Extended with dashboard config |

### Outbound (produced by dashboard)

| Artifact | Format | Description |
|----------|--------|-------------|
| `dashboard.db` | SQLite | User auth, sessions, alerts |
| `frontend/build/` | Static HTML/JS/CSS | SvelteKit production build |

### No new IPC contracts needed

The dashboard is read-only — it displays existing data, it doesn't generate new IPC files for the EA. The EA continues to read only `{SYMBOL}_params.json` and `kill_switch.json` from Phase 1 contracts.

## Pitfalls (Dashboard-Specific)

### Pitfall 1: MT5 API Not Thread-Safe

The FastAPI async event loop calls `mt5.positions_get()` from a background task while the AI engine or data pipeline might also call MT5 functions. The MT5 Python API is NOT thread-safe — concurrent calls can crash or return corrupted data.

**Prevention:** All MT5 calls must go through a single-threaded access pattern. Use an `asyncio.Lock` or a dedicated MT5 access queue. Since Phase 1 already wraps MT5 calls in `ensure_connected()`, extend this pattern: add `with mt5_lock:` around all MT5 API calls in the dashboard. OR: have the dashboard read cached data that a single background thread updates.

**Recommended approach:** A single background thread (`MT5Poller`) runs on a 1-second timer, calls all MT5 functions, caches results in thread-safe variables. FastAPI reads from cache (no MT5 calls from async context). This is the simplest correct pattern.

### Pitfall 2: JSONL Log File Growth

Trade and decision logs grow indefinitely. Reading the entire JSONL file for every API request becomes slow with 10,000+ lines.

**Prevention:**
- Paginate API responses: `?limit=50&offset=0` — only parse what's needed
- Read file backward for recent entries: seek to end, read last N lines (faster than full parse)
- Optional: daily log rotation in future (not Phase 4 — logs are small in early usage)
- Equity curve computation: cache result, invalidate when new trades appear

### Pitfall 3: WebSocket Reconnection Storms

If the server restarts, all connected clients attempt to reconnect simultaneously, creating a thundering herd.

**Prevention:** Exponential backoff with jitter on client-side reconnection. `setTimeout(() => connect(), backoff * (1 + Math.random() * 0.5))`. Max backoff: 30 seconds.

### Pitfall 4: SvelteKit Static Adapter with Auth

Static adapter means all routes are pre-rendered HTML. Auth-protected pages still exist as static files — you can't do server-side auth checks on static pages.

**Prevention:**
- All data fetching happens client-side via fetch (CSR — client-side rendering for authenticated content)
- +layout.svelte checks for token in localStorage on mount
- If no token: redirect to `/login` client-side
- API endpoints enforce auth server-side (the real security boundary)
- The static HTML pages are effectively "shells" — no sensitive data is rendered server-side

### Pitfall 5: CORS Issues in Development

SvelteKit dev server (port 5173) and FastAPI (port 8000) are different origins. Browsers block cross-origin requests.

**Prevention:** Vite proxy config forwards `/api/*` and `/ws/*` to FastAPI, so the browser sees same-origin requests. Alternatively: FastAPI CORS middleware allowing `localhost:5173` in dev mode.

```javascript
// vite.config.ts
export default defineConfig({
    server: {
        proxy: {
            '/api': 'http://localhost:8000',
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true
            }
        }
    }
});
```

## Configuration (additions to config.py)

```python
# --- Dashboard Configuration ---

# Dashboard database path
DASHBOARD_DB_PATH = Path(os.getenv("FUTRA_DASHBOARD_DB", "dashboard.db"))

# Development mode (serves Vite proxy, not static files)
DASHBOARD_DEV_MODE = os.getenv("FUTRA_DASHBOARD_DEV", "false").lower() == "true"

# Frontend build directory (for production static file serving)
FRONTEND_BUILD_DIR = Path(os.getenv("FUTRA_FRONTEND_DIR", "frontend/build"))

# Auth
SESSION_EXPIRY_HOURS = int(os.getenv("FUTRA_SESSION_EXPIRY_HOURS", "24"))

# MT5 polling interval for live dashboard updates (seconds)
DASHBOARD_POLL_INTERVAL = float(os.getenv("FUTRA_DASHBOARD_POLL", "1.0"))

# Alert thresholds
DRAWDOWN_ALERT_THRESHOLD = float(os.getenv("FUTRA_DRAWDOWN_ALERT_PCT", "10.0"))  # Alert at 10% drawdown
DAILY_LOSS_ALERT_THRESHOLD = float(os.getenv("FUTRA_DAILY_LOSS_ALERT", "500.0"))  # Alert at $500 daily loss
```

## What NOT to Build

| Avoid | Why | Build Instead |
|-------|-----|--------------|
| Real-time candlestick charting | Out of scope per REQUIREMENTS.md. MT5 provides full charting. Building it is months of work. | Equity curve + drawdown charts only |
| Manual trading controls | Deferred per ROADMAP v2 (DASH-11). Phase 4 is monitoring-only. | Read-only dashboard |
| Multi-user auth system | Single-user system per PROJECT.md. Multi-user adds complexity with zero benefit. | Single-user token auth |
| SSR with adapter-node | Adds Node.js runtime alongside Python on Windows VPS. No SEO benefit for private dashboard. | Static adapter — FastAPI serves files |
| Firebase/SaaS push notifications | Single-user, single-device. External push service adds dependencies and cost. | WebSocket + browser Notification API |
| Custom charting library | Building financial charts from scratch is 100+ hours. Use a battle-tested library. | lightweight-charts (TradingView) |
| Grafana/Prometheus integration | Overkill for single-user. Adds infrastructure complexity (Prometheus + Grafana servers on Windows VPS). | Built-in FastAPI + SvelteKit |
| Docker/containerized deployment | MT5 requires Windows GUI. Docker on Windows is fragile for GUI apps. VPS is already Windows-native. | Direct Windows VPS deployment |

## Testing Strategy

### Unit Tests (per module)

| Module | Key Tests | Count |
|--------|-----------|-------|
| `auth.py` | Login succeeds with correct password, fails with wrong password, token generation, token expiry, logout invalidates token, middleware rejects missing/expired tokens | 8-10 |
| `positions.py` | Returns MT5 positions as JSON, handles no positions, handles MT5 connection error | 4-6 |
| `account.py` | Returns account info as JSON, handles MT5 error | 3-4 |
| `trades.py` | Reads JSONL trade log, pagination, empty log, malformed lines skipped, offset/limit boundaries | 6-8 |
| `decisions.py` | Reads JSONL decision log, symbol filter, pagination, empty log | 6-8 |
| `equity.py` | Computes equity curve from trade list, handles no trades, single trade, multiple trades, validates data points | 6-8 |
| `drawdown.py` | Computes drawdown from equity curve, peak detection, zero drawdown case, increasing equity | 5-6 |
| `ws.py` | Client connects, subscribe/unsubscribe, broadcast to subscribers, heartbeat, disconnect cleanup | 8-10 |
| `alerts.py` | Alert creation, acknowledgment, filtering by acknowledged, listing | 5-6 |
| `notification.py` | Drawdown alert triggers at threshold, MT5 connection loss alert, daily loss alert, alert deduplication | 6-8 |

**Total: ~57-74 tests** — consistent with Phase 1 (106 tests) and Phase 2 (~45 tests) scale.

### Frontend Component Tests

| Component | Key Tests | Count |
|-----------|-----------|-------|
| `AccountSummary` | Renders balance/equity/margin/margin from store, positive/negative P&L colors | 4 |
| `PositionsTable` | Renders position rows from store, P&L computation, empty state | 4 |
| `EquityChart` | Chart instance created on mount, destroyed on unmount, data update | 3 |
| `DrawdownChart` | Chart renders below zero, data update | 3 |
| `AlertFeed` | Renders alerts list, severity badges, empty state | 3 |

**Frontend tests: ~17 tests** — focused on component rendering and data binding.

### Integration Tests

- FastAPI TestClient: login → get positions → verify auth middleware → logout → verify 401
- WebSocket: connect with token → subscribe → send positions update → client receives → disconnect cleanup
- Equity computation: read test trade log → compute equity curve → verify values match known results

## Sources

- **FastAPI WebSocket docs:** `fastapi` websocket support via Starlette — native, well-documented, HIGH confidence
- **lightweight-charts:** TradingView's open-source financial charting library — v4.1+, supports line/area/candlestick/histogram series, HIGH confidence
- **SvelteKit static adapter:** `@sveltejs/adapter-static` — official adapter, produces pure static output, HIGH confidence
- **SvelteKit proxy config:** Vite server proxy — standard pattern for dev API routing, HIGH confidence
- **passlib:** Python password hashing library — bcrypt support, well-maintained, HIGH confidence
- **Caddy on Windows:** Native Windows build available, automatic HTTPS via Let's Encrypt — MEDIUM confidence (less common on Windows, but documented)
- **MT5 Python API thread safety:** MetaQuotes docs do not guarantee thread safety — confirmed via community reports, HIGH confidence (this is a known constraint)
- **Web Notifications API:** Standard browser API — `Notification.requestPermission()`, well-supported in modern browsers, HIGH confidence
- **Phase 1 trade log format:** Verified in `ea/include/Logger.mqh` — JSONL with event/ticket/symbol/profit/timestamp fields, HIGH confidence
- **Phase 2 decision log format:** Defined in `02-02-PLAN.md` — JSONL with regime/confidence/parameters/reasoning fields, HIGH confidence

---

*Research for Phase 4: Monitoring Dashboard*
*Researched: 2026-05-26*
*Confidence: HIGH — all patterns are well-established; primary uncertainties are Windows VPS specifics (Caddy/nginx setup) which are documented but deployment-environment-dependent*
