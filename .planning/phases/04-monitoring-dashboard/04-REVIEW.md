---
phase: 04-monitoring-dashboard
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 40
files_reviewed_list:
  - python/config.py
  - python/dashboard/__init__.py
  - python/dashboard/main.py
  - python/dashboard/auth.py
  - python/dashboard/db.py
  - python/dashboard/models.py
  - python/dashboard/ws.py
  - python/dashboard/notification.py
  - python/dashboard/api/__init__.py
  - python/dashboard/api/account.py
  - python/dashboard/api/alerts.py
  - python/dashboard/api/decisions.py
  - python/dashboard/api/drawdown.py
  - python/dashboard/api/equity.py
  - python/dashboard/api/positions.py
  - python/dashboard/api/strategy.py
  - python/dashboard/api/trades.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/types.ts
  - frontend/src/lib/stores.ts
  - frontend/src/lib/utils.ts
  - frontend/src/lib/components/AccountSummary.svelte
  - frontend/src/lib/components/AlertFeed.svelte
  - frontend/src/lib/components/ConnectionStatus.svelte
  - frontend/src/lib/components/DecisionLogTable.svelte
  - frontend/src/lib/components/DrawdownChart.svelte
  - frontend/src/lib/components/EquityChart.svelte
  - frontend/src/lib/components/MetricsCard.svelte
  - frontend/src/lib/components/Nav.svelte
  - frontend/src/lib/components/PositionsTable.svelte
  - frontend/src/lib/components/TradeHistoryTable.svelte
  - frontend/src/routes/+layout.svelte
  - frontend/src/routes/+page.svelte
  - frontend/src/routes/alerts/+page.svelte
  - frontend/src/routes/decisions/+page.svelte
  - frontend/src/routes/login/+page.svelte
  - frontend/src/routes/performance/+page.svelte
  - frontend/src/routes/settings/+page.svelte
  - frontend/src/routes/trades/+page.svelte
  - deploy/Caddyfile
  - deploy/start-dashboard.ps1
  - deploy/README.md
  - .env.example
findings:
  critical: 4
  warning: 11
  info: 9
  total: 24
status: issues_found
---
# Phase 4: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard
**Files Reviewed:** 40
**Status:** issues_found

## Summary

Phase 4 implements a FastAPI dashboard backend, SvelteKit frontend, and production deployment configuration. The architecture is sound: JWT-like token auth (stored in SQLite), WebSocket-based real-time updates, a background MT5 poller, and alert monitoring. The frontend uses Svelte 5 runes, lightweight-charts, and shadcn-svelte components — all well-structured.

However, the review found **4 critical issues** that must be fixed before production use:
1. A configuration mismatch that silently breaks MT5 credential loading from `.env`
2. An equity curve computation that always starts from the initial balance, producing incorrect absolute values for any date window
3. Plaintext credential logging of the default admin password

11 warnings cover connection leaks, cache consistency, data export escapes, dead configuration, and dead code. 9 informational items flag duplicated utility functions and minor code smells.

---

## Critical Issues

### CR-01: MT5 environment variable names mismatch between `.env.example` and `config.py`

**File:** `python/config.py:12-15` vs `.env.example:8-13`
**Issue:** The `.env.example` template uses the prefix `FUTRA_MT5_*` (e.g., `FUTRA_MT5_LOGIN`, `FUTRA_MT5_PASSWORD`, `FUTRA_MT5_SERVER`), but `config.py` reads from env vars **without** that prefix: `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, and `MT5_PATH`. If a user follows the deployment guide and copies `.env.example` to `.env`, none of their MT5 credentials will be read — `config.py` will silently fall back to defaults (`MT5_LOGIN=0`, `MT5_PASSWORD=""`, `MT5_SERVER=""`). This means the dashboard's MT5 poller will either fail to connect entirely (`MT5_PASSWORD=""`) or attempt saved credentials (`MT5_LOGIN=0`) which may not be the intended account. The demo/practice trading vars have the same mismatch (`MT5_DEMO_*` in config vs not in .env.example at all).
**Fix:** Align the env var names. Either rename `.env.example` to match `config.py`:

```diff
# .env.example
- FUTRA_MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
+ MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
- FUTRA_MT5_LOGIN=12345678
+ MT5_LOGIN=12345678
- FUTRA_MT5_PASSWORD=your_mt5_password
+ MT5_PASSWORD=your_mt5_password
- FUTRA_MT5_SERVER=YourBroker-Server
+ MT5_SERVER=YourBroker-Server
```

Or rename the `config.py` reads to use the `FUTRA_MT5_*` prefix for consistency with all other dashboard env vars.

---

### CR-02: Equity curve always starts from `initial_balance`, ignoring prior trading history

**File:** `python/dashboard/api/equity.py:69` and `python/dashboard/api/equity.py:79`
**Issue:** `compute_equity_curve()` always sets the starting equity value to `initial_balance` (default `$10,000`) at `start_date` (e.g., 30 days ago). It never accounts for cumulative profits/losses from trades that occurred *before* the requested window. This means the equity curve for any time window is vertically shifted by the amount of prior accumulated P&L.

**Example:** An account that started at $10,000 and has a 2-year track record running at $12,000 today. Requesting `days=30` shows equity starting at $10,000 (wrong — it should be ~$11,800 from 30 days ago) and ending at $12,000 (correct). The curve slope is right but the absolute y-values are all ~$1,800 too low.

This is a financial correctness bug — equity values are the most fundamental metric on a trading dashboard. The drawdown computation (in `drawdown.py`) inherits this same error since it depends on equity curve values.
**Fix:** Compute the running equity from the very first trade, then truncate to the requested window:

```python
def compute_equity_curve(
    trade_log_path: Path | None = None,
    initial_balance: float = 10000.0,
    days: int = 30,
) -> list[dict]:
    # ... (parse closes into equity_map as before) ...

    # Build running equity from day 1 to today (full history)
    sorted_days = sorted(equity_map.keys())
    if not sorted_days:
        today = datetime.now(timezone.utc).date()
        return [{"time": today.isoformat(), "value": initial_balance}]

    # Compute full equity curve from start of history
    first_day = datetime.fromisoformat(sorted_days[0]).date()
    full_equity: dict[str, float] = {}
    running = initial_balance
    current = first_day
    today = datetime.now(timezone.utc).date()
    while current <= today:
        day_str = current.isoformat()
        if day_str in equity_map:
            running += equity_map[day_str]
        full_equity[day_str] = running
        current += timedelta(days=1)

    # Truncate to requested window
    start_date = today - timedelta(days=days)
    points = [
        {"time": day, "value": round(val, 2)}
        for day, val in full_equity.items()
        if day >= start_date.isoformat()
    ]
    return points
```

---

### CR-03: Default admin password logged in plaintext

**File:** `python/dashboard/db.py:58-60`
**Issue:** When the default admin user is created (`init_db()`), the generated password is logged at `WARNING` level via `logger.warning("Default admin user created: username=admin, password=%s", password)`. In production, logs may be written to files, shipped to centralized logging, or accessible by anyone with read access to the server. This exposes the admin credential.

The dead code at `python/dashboard/auth.py:27-30` (`_ensure_default_admin`) has the same log line, but since that function is never called, it's not an active vulnerability — just dead code copying the same dangerous pattern.
**Fix:** Log only that a default admin was created, not the password:

```python
logger.warning(
    "Default admin user created: username=admin. "
    "Password written to stdout only — change immediately."
)
print(f"\n{'='*60}\nDefault admin password: {password}\n{'='*60}\n")
```

Note: print-to-stdout is still visible but doesn't persist to log files. For production, consider requiring the admin password to be set via environment variable (`FUTRA_ADMIN_PASSWORD`) with no default generation.

---

### CR-04: SQLite connection leak in all authentication endpoints

**File:** `python/dashboard/auth.py:35,63,85`
**Issue:** The `require_auth`, `login`, and `logout` endpoints acquire SQLite connections via `Depends(get_db)` but never close them. Each `get_db()` call creates a new `sqlite3.Connection`; when the function returns, the connection object goes out of scope but is never explicitly `.close()`-d. Python's garbage collector may eventually close it, but this is not guaranteed or timely. Over hours/days of dashboard usage, connections accumulate, consuming file descriptors and memory.

The API endpoints that manually call `get_db()` (alerts, trades, decisions, etc.) properly wrap usage in `try/finally: db.close()`. The auth endpoints do not.

This affects every authenticated request (via `require_auth`), every login, and every logout.
**Fix:** Two options:

**Option A (recommended):** Use a context manager / generator dependency pattern:

```python
# db.py
from contextlib import contextmanager

@contextmanager
def get_db_ctx():
    conn = sqlite3.connect(str(config.DASHBOARD_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()
```

Then in auth.py, use it in each endpoint:

```python
async def require_auth(request: Request):
    with get_db_ctx() as db:
        # ... query, validate, return user_id ...
```

**Option B:** Add explicit close calls before each return in the existing `Depends` pattern:

```python
async def require_auth(request: Request, db=Depends(get_db)):
    try:
        # ... existing auth logic ...
        return row["user_id"]
    finally:
        db.close()
```

---

## Warnings

### WR-01: MT5 cache writes occur outside the `_mt5_lock` critical section

**File:** `python/dashboard/api/__init__.py:48-76`
**Issue:** `poll_mt5_state()` acquires `_mt5_lock` to serialize MT5 API calls (preventing concurrent `positions_get()` / `account_info()` calls), but writes to the shared cache dict happen *after* releasing the lock:

```python
with _mt5_lock:           # line 48
    raw_positions = mt5.positions_get()
    ...
    current_account = ...
                           # lock released after line 72
_mt5_cache["positions"] = current_positions  # line 75 — no lock
_mt5_cache["account"] = current_account      # line 76 — no lock
```

API route handlers read `_mt5_cache` without any lock (`account.py:13`, `positions.py:13`, `notification.py:83`). In CPython, dict writes are atomic due to the GIL, so a torn read isn't possible, but between lines 75-76 a reader could see new positions paired with old account data. More critically, this pattern is fragile — if a future change makes cache writes non-atomic or multi-step, a data race becomes real.
**Fix:** Extend the lock to cover cache writes:

```python
with _mt5_lock:
    raw_positions = mt5.positions_get()
    ...
    _mt5_cache["positions"] = current_positions
    _mt5_cache["account"] = current_account
    _mt5_cache["last_update"] = datetime.now(timezone.utc).isoformat()
```

---

### WR-02: `daily_pnl` is hardcoded to `0.0`

**File:** `python/dashboard/api/__init__.py:68`
**Issue:** The account info poller always sets `"daily_pnl": 0.0`. Neither the frontend nor backend computes actual daily P&L. For a monitoring dashboard, this is one of the top metrics traders want to see. The field exists in the `AccountInfo` model and the frontend types, but the value is never meaningful.
**Fix:** Compute daily P&L by comparing today's balance to yesterday's closing balance, or by summing all `trade_close` profits with today's date from the trade log. If the data isn't yet available, surface a clear "N/A" state rather than silently showing `$0.00`.

---

### WR-03: CSV export does not escape commas, quotes, or newlines

**File:** `frontend/src/routes/trades/+page.svelte:28-48`
**Issue:** The `exportCSV()` function builds CSV rows by naive string concatenation: `[headers.join(','), ...rows.map(r => r.join(','))].join('\n')`. If any field contains a comma, double-quote, or newline, the resulting CSV is malformed. While trading data fields (ticket, symbol, direction, prices) are unlikely to contain these characters, the `duration` field (e.g., `"1h 30m"`) is safe, but `close_time` ISO strings could theoretically be exposed to injection in edge cases.
**Fix:** Properly escape CSV fields:

```typescript
function escapeCSV(value: string | number): string {
    const s = String(value);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
}
// Then: rows.map(r => r.map(escapeCSV).join(','))
```

---

### WR-04: `SESSION_SECRET` is defined but never used in token generation

**File:** `python/config.py:123`
**Issue:** `SESSION_SECRET` is read from `FUTRA_SESSION_SECRET` env var (or auto-generated) and the `.env.example` / deploy README instruct users to set it for persistent sessions. However, `auth.py:login` generates tokens via `secrets.token_hex(32)` — the `SESSION_SECRET` value is never imported or used anywhere. Tokens are random opaque strings stored directly in the SQLite `sessions` table, so sessions persist across restarts regardless of this config. The configuration is misleading: users who set a persistent secret expecting it to affect token generation will be confused, and users who *don't* set it won't experience the "sessions invalidate on restart" behavior the README warns about.
**Fix:** Either:
- Remove `SESSION_SECRET` entirely (tokens don't need a secret when stored server-side), OR
- Switch to JWT-style signed tokens using `SESSION_SECRET` as the signing key (eliminating the DB lookup on every request). If keeping stored tokens, remove `SESSION_SECRET` from `.env.example` and `deploy/README.md` to avoid confusion.

---

### WR-05: `AI_LOG_DIR` defined twice with conflicting defaults — second definition wins

**File:** `python/config.py:47` and `python/config.py:109`
**Issue:** `AI_LOG_DIR` is assigned twice in the same file:

```python
# Line 47 (AI Engine section):
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", str(Path(__file__).parent / "ai" / "decisions")))

# Line 109 (Dashboard section):
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", "logs/ai"))
```

Line 109 overrides line 47. The effective default becomes `Path("logs/ai")` (relative to CWD), discarding the project-root-relative default from line 47. The dashboard's `decisions.py` imports `AI_LOG_DIR` and uses it at `AI_LOG_DIR / "decision_log.jsonl"` — this resolves to `logs/ai/decision_log.jsonl` (relative to wherever Python is launched), which may not find the actual log file if the AI engine writes to `python/ai/decisions/decision_log.jsonl`.
**Fix:** Remove the duplicate definition. If the AI engine and dashboard share the same log path, define it once with a consistent default. If they should differ, use distinct config keys (e.g., `AI_LOG_DIR` for the engine, `AI_DECISION_LOG_DIR` for the dashboard).

```python
# Keep only one:
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", str(Path(__file__).parent.parent / "logs" / "ai")))
```

---

### WR-06: Relative default paths depend on CWD

**File:** `python/config.py:101,110`
**Issue:** Two config values have relative defaults that depend on the current working directory at process startup:
- `DASHBOARD_DB_PATH = Path(os.getenv("FUTRA_DASHBOARD_DB", "dashboard.db"))` → creates `dashboard.db` wherever the process runs
- `STRATEGY_CONFIG_DIR = Path(os.getenv("FUTRA_STRATEGY_CONFIG_DIR", "configs/strategies"))` → looks for strategy configs relative to CWD

The `start-dashboard.ps1` script changes directories before launching, but other launch methods (uvicorn directly, Windows service, Docker) may have different CWDs, silently creating databases in unexpected locations or failing to find configs.
**Fix:** Use project-root-relative paths for defaults:

```python
_PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARD_DB_PATH = Path(os.getenv("FUTRA_DASHBOARD_DB", str(_PROJECT_ROOT / "dashboard.db")))
STRATEGY_CONFIG_DIR = Path(os.getenv("FUTRA_STRATEGY_CONFIG_DIR", str(_PROJECT_ROOT / "configs" / "strategies")))
```

---

### WR-07: Dead code: `_ensure_default_admin` in `auth.py` never called

**File:** `python/dashboard/auth.py:16-32`
**Issue:** The `_ensure_default_admin()` function is defined but never invoked. It duplicates the admin-creation logic already present in `db.py:init_db()`. Additionally, `auth.py` imports `init_db` from `db` (line 7) but never calls it. This dead code adds maintenance burden and risks confusion about which module is authoritative for user creation.
**Fix:** Remove `_ensure_default_admin` and the unused `init_db` import from `auth.py`. Keep the admin-creation logic only in `db.py:init_db()`.

---

### WR-08: `last_update` cache key set but never populated

**File:** `python/dashboard/api/__init__.py:14`
**Issue:** The `_mt5_cache` dictionary includes a `"last_update"` key initialized to `None`, but `poll_mt5_state()` never writes to it. Consumers could use this to know cache freshness (e.g., detecting stale data when MT5 is disconnected), but it's always `None`.
**Fix:** Set `_mt5_cache["last_update"]` after each successful poll:

```python
_mt5_cache["last_update"] = datetime.now(timezone.utc).isoformat()
```

---

### WR-09: Token exposed via WebSocket query parameter

**File:** `python/dashboard/main.py:69`
**Issue:** The WebSocket endpoint accepts the auth token as a URL query parameter (`ws://host:8000/ws?token=...`). Query parameters appear in server access logs, proxy logs, and browser history — unlike `Authorization` headers, which are not typically logged. If Caddy or a reverse proxy logs request URLs, the token is persisted in plaintext.
**Fix:** For WebSocket connections, the browser WebSocket API doesn't support custom headers during the handshake. Common mitigations:
1. Issue a short-lived (e.g., 60-second) WS-specific token via a REST endpoint, then pass that via query param
2. Use the `Sec-WebSocket-Protocol` header (subprotocol negotiation) to carry the token
3. Accept the tradeoff but document the logging risk and ensure reverse proxies strip query params from access logs

```caddyfile
# In Caddyfile, suppress query params from logs:
log {
    output file C:\Futra\logs\caddy.log {
        format json {
            time_format wallclock
        }
    }
}
```

---

### WR-10: `bcrypt` import inside `init_db()` may fail silently

**File:** `python/dashboard/db.py:50`
**Issue:** `init_db()` imports `bcrypt` inside the function body (line 50: `import bcrypt`). While this works, the import is nested inside a `try/except` that catches all exceptions. If `bcrypt` is not installed, the `ImportError` is caught by the outer `except Exception` at line 62, which logs an error but continues — the users table is created without a default admin. The dashboard then starts with zero users and no way to log in.

The root cause module is that `bcrypt` may not be in `requirements.txt` (the requirements file was not reviewed but the deploy script does `pip install -r requirements.txt --quiet`, and if bcrypt is missing, the dashboard starts in a broken state).
**Fix:** Move the `import bcrypt` to the top of the file. If bcrypt is missing, the import fails at module load time (before the server starts), providing a clear, immediate error rather than a silent broken state discovered at runtime.

---

### WR-11: Redundant disconnect handling between `ws.py` and `main.py`

**File:** `python/dashboard/main.py:92-95` and `python/dashboard/ws.py:64-65`
**Issue:** `ws.py:handle_client_messages` catches all exceptions (including `WebSocketDisconnect`) internally and calls `self.disconnect(websocket)`. The exception is NOT re-raised. Therefore, the exception handlers in `main.py:92-95` (`WebSocketDisconnect` and generic `Exception`) are dead code — they can never fire because `handle_client_messages` suppresses all exceptions internally. While harmless, this creates confusion about where disconnects are actually handled and makes the code harder to follow.
**Fix:** Choose one place for disconnect handling. Simplest approach: remove the try/except from `main.py` since `ws.py` already handles it:

```python
await manager.connect(websocket, user_id)
await manager.handle_client_messages(websocket)
```

---

## Info

### IN-01: Duplicated `relativeTime` across two components

**File:** `frontend/src/lib/components/AlertFeed.svelte:6-14` and `frontend/src/routes/alerts/+page.svelte:18-26`
**Issue:** The exact same `relativeTime(dateString)` function is defined in both files. Any change must be made in two places.
**Fix:** Move to `frontend/src/lib/utils.ts` and import from both components.

---

### IN-02: Duplicated `severityBadgeClass` across two components

**File:** `frontend/src/lib/components/AlertFeed.svelte:16-23` and `frontend/src/routes/alerts/+page.svelte:28-35`
**Issue:** Same severity-to-CSS-class mapping duplicated.
**Fix:** Move to `frontend/src/lib/utils.ts`:

```typescript
export function severityBadgeClass(severity: string): string { ... }
```

---

### IN-03: Duplicated `formatCurrency` across three components

**File:** `frontend/src/lib/components/PositionsTable.svelte:8-10`, `frontend/src/lib/components/TradeHistoryTable.svelte:16-18`, `frontend/src/lib/components/AccountSummary.svelte:6-9`
**Issue:** Same `Intl.NumberFormat` wrapper repeated in three files (with slight variation: AccountSummary checks for `undefined|null`).
**Fix:** Consolidate in `utils.ts`:

```typescript
export function formatCurrency(value: number | null | undefined, fallback = '\u2014'): string {
    if (value == null) return fallback;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}
```

---

### IN-04: Duplicated `formatSignedCurrency` across two components

**File:** `frontend/src/lib/components/PositionsTable.svelte:12-15` and `frontend/src/lib/components/TradeHistoryTable.svelte:20-23`
**Issue:** Same signed-currency formatter duplicated.
**Fix:** Move to `utils.ts`.

---

### IN-05: Dead `loading` state in `PositionsTable`

**File:** `frontend/src/lib/components/PositionsTable.svelte:17`
**Issue:** `let loading = $state(false)` is declared but never set to `true`. The loading skeleton view (lines 27-33) is unreachable. Positions are loaded by the parent page (`+page.svelte`), which manages its own loading state. The PositionsTable component should either accept a `loading` prop (like `TradeHistoryTable` does) or remove the dead loading UI.
**Fix:** Either accept `loading` as a prop (consistent with `TradeHistoryTable` and `DecisionLogTable`) or remove the dead code.

---

### IN-06: `user_id` accepted but never used for data isolation

**File:** `python/dashboard/api/account.py:11`, `positions.py:11`, `trades.py:81`, etc.
**Issue:** All authenticated API endpoints accept `user_id: int = Depends(require_auth)` but discard the value. There's no per-user data filtering — all users see the same positions, trades, and alerts. For a single-user trading dashboard this is acceptable, but the `user_id` parameter suggests multi-user support that doesn't exist, which could mislead future developers.
**Fix:** Either remove `user_id` from route handlers (keep `require_auth` as a dependency that returns nothing), or document explicitly that the dashboard is single-user and `user_id` is intentionally unused.

---

### IN-07: Unused import: `init_db` in `auth.py`

**File:** `python/dashboard/auth.py:7`
**Issue:** `init_db` is imported from `.db` but never called in `auth.py`.
**Fix:** Remove the unused import.

---

### IN-08: Caddyfile uses placeholder domain

**File:** `deploy/Caddyfile:3`
**Issue:** The Caddy configuration uses `dashboard.yourdomain.com` as a placeholder. The deploy README instructs users to change this, but if forgotten, Caddy will attempt to provision a Let's Encrypt certificate for `dashboard.yourdomain.com`, which will fail (domain doesn't exist). This is a deployment footgun — consider using `localhost` or an env-var-based domain: `{$FUTRA_DASHBOARD_DOMAIN}`.
**Fix:**

```caddyfile
{$FUTRA_DASHBOARD_DOMAIN:localhost} {
    reverse_proxy localhost:8000
    # ...
}
```

This reads from the `FUTRA_DASHBOARD_DOMAIN` env var, falling back to `localhost` — matching how `config.py` and the start script already work.

---

### IN-09: Unused `_mt5_module` lazy import pattern is inconsistent

**File:** `python/dashboard/notification.py:12-15`
**Issue:** `notification.py` does `try: import MetaTrader5 as _mt5_module` at module level, while `api/__init__.py` does `import MetaTrader5 as mt5` inside the `poll_mt5_state()` function body. Two different import patterns for the same optional dependency in the same package. Both work, but consistency would reduce confusion.
**Fix:** Pick one pattern and apply it consistently.

---

_Reviewed: 2026-05-28_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
