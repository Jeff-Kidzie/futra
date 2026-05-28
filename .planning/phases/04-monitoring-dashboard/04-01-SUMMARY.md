---
phase: 04-monitoring-dashboard
plan: "01"
subsystem: api
tags: [fastapi, websocket, sqlite, bcrypt, auth, mt5, alerting]

# Dependency graph
requires:
  - phase: 03-validation
    provides: "MT5 connector patterns, trade/decision log formats, config patterns"
provides:
  - "FastAPI dashboard backend with Bearer token auth"
  - "REST API for positions, account, trades, decisions, equity, drawdown, alerts, strategy"
  - "WebSocket server for real-time updates with subscription-based broadcast"
  - "Background MT5 state polling with thread-safe cache"
  - "Alert monitoring for drawdown/connection loss with SQLite persistence"
affects: ["04-02-dashboard-frontend", "04-03-dashboard-deployment"]

# Tech tracking
tech-stack:
  added:
    - "fastapi>=0.100.0, uvicorn[standard]>=0.23.0"
    - "passlib[bcrypt]>=1.7.4 for password hashing"
    - "websockets>=11.0 for WebSocket support"
    - "python-multipart>=0.0.6"
    - "httpx>=0.25.0 for test client"
  patterns:
    - "Bearer token auth: 64-char hex tokens stored in SQLite sessions table with 24h expiry"
    - "Single-threaded MT5 polling: background thread updates cache, API routes read cache"
    - "Subscription-based WebSocket broadcast: clients subscribe to symbols, server filters"
    - "Alert deduplication: same type+message within 60s not re-created"
    - "Test fixtures with temp SQLite DB, monkeypatch for config override"

key-files:
  created:
    - "python/dashboard/__init__.py"
    - "python/dashboard/main.py - FastAPI app with CORS, lifespan, WebSocket, 9 routers"
    - "python/dashboard/auth.py - require_auth dependency, login/logout, token validation"
    - "python/dashboard/db.py - SQLite connection manager, init_db with default admin"
    - "python/dashboard/models.py - 10 Pydantic models for API request/response"
    - "python/dashboard/ws.py - ConnectionManager with broadcast/subscribe/heartbeat"
    - "python/dashboard/notification.py - AlertMonitor with drawdown/connection checks"
    - "python/dashboard/api/positions.py - GET /api/positions from MT5 cache"
    - "python/dashboard/api/account.py - GET /api/account with zeros fallback"
    - "python/dashboard/api/trades.py - GET /api/trades from trade_log.jsonl with pagination"
    - "python/dashboard/api/decisions.py - GET /api/decisions with symbol filter, missing-file grace"
    - "python/dashboard/api/equity.py - compute_equity_curve from trade log replay"
    - "python/dashboard/api/drawdown.py - compute_drawdown_curve from equity data"
    - "python/dashboard/api/alerts.py - GET /api/alerts, POST /api/alerts/{id}/acknowledge"
    - "python/dashboard/api/strategy.py - GET /api/strategy from config JSON"
    - "requirements.txt - Python dependencies"
    - "python/tests/dashboard/test_auth.py - 18 auth tests"
    - "python/tests/dashboard/test_positions.py - 4 position tests"
    - "python/tests/dashboard/test_account.py - 3 account tests"
    - "python/tests/dashboard/test_trades.py - 7 trade tests"
    - "python/tests/dashboard/test_decisions.py - 5 decision tests"
    - "python/tests/dashboard/test_equity.py - 5 equity tests"
    - "python/tests/dashboard/test_alerts.py - 7 alert tests"
    - "python/tests/dashboard/test_ws.py - 11 WebSocket tests"
    - "python/tests/dashboard/test_notification.py - 5 notification tests"
  modified:
    - "python/config.py - added dashboard config (DB path, dev mode, session expiry, poll interval, alert thresholds)"

key-decisions:
  - "Bearer token over JWT — single-user system, simpler revocation via SQLite DELETE"
  - "Default admin created on first startup with random password logged to console"
  - "check_same_thread=False on SQLite connections for FastAPI async thread pool compatibility"
  - "Single-threaded MT5 polling pattern with threading.Lock — MT5 API is not thread-safe"
  - "Equity curve computed at request time from trade_log.jsonl replay"

patterns-established:
  - "TDD execution model: RED phase (failing tests + stubs) → GREEN phase (implementation)"
  - "FastAPI Depends pattern for auth dependency injection"
  - "Monkeypatch + pytest fixtures for fully local testing without MT5"
  - "SQLite WAL mode for concurrent read safety"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-07]

# Metrics
duration: 45min
completed: 2026-05-28
---

# Phase 4 Plan 1: FastAPI Dashboard Backend Summary

**FastAPI backend with Bearer token auth, 9 REST API routes, WebSocket real-time updates, and alert monitoring — 65 tests all passing**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-28
- **Completed:** 2026-05-28
- **Tasks:** 3
- **Files created/modified:** 29 files, +2,276 lines

## Accomplishments

- Auth system: bcrypt password hashing, token-based sessions (24h expiry), default admin creation on first startup
- 8 REST API routes: positions, account, trades (paginated from trade_log.jsonl), decisions (symbol filter, graceful missing file), equity curve (trade replay computation), drawdown curve, alerts (CRUD with acknowledge), strategy config
- WebSocket server at /ws with token query param auth, subscription-based broadcast, heartbeat/cleanup
- Background MT5 poller with thread-safe cache pattern (threading.Lock around all MT5 API calls)
- AlertMonitor detects drawdown threshold breaches and MT5 connection loss, deduplicates within 60s
- All 65 tests pass — no live MT5 connection required

## Task Commits

Each TDD task committed atomically:

1. **Task 1: Auth system, SQLite schema, Pydantic models** — `1566093` (feat)
2. **Task 2: REST API data endpoints + equity/drawdown computation** — `209a99c` (feat)
3. **Task 3: WebSocket server, MT5 poller, alert monitor** — `4649b81` (feat)

_Note: RED-phase stubs were pre-existing in the codebase from a prior partial execution. GREEN phase implemented fully functional implementations for all three tasks._

## Files Created/Modified

- `python/dashboard/auth.py` — Bearer token auth, login/logout, require_auth middleware
- `python/dashboard/db.py` — SQLite WAL connection, schema creation, default admin
- `python/dashboard/models.py` — 10 Pydantic models (Position, AccountInfo, Trade, Decision, EquityPoint, DrawdownPoint, Alert, LoginRequest, LoginResponse, StrategyConfig)
- `python/dashboard/main.py` — FastAPI app with CORS, 9 routers, WebSocket endpoint, lifespan with background tasks
- `python/dashboard/ws.py` — ConnectionManager with broadcast/subscribe/heartbeat
- `python/dashboard/notification.py` — AlertMonitor with drawdown/connection checks and deduplication
- `python/dashboard/api/*.py` — 9 API endpoint modules (positions, account, trades, decisions, equity, drawdown, alerts, strategy) plus shared MT5 cache
- `python/config.py` — Added dashboard configuration (12 new constants)
- `requirements.txt` — 6 Python dependencies
- `python/tests/dashboard/` — 11 test files, 65 tests total

## Decisions Made

- **Bearer token over JWT** — Single-user system; simple SQLite session table provides instant revocation via DELETE, no key management needed
- **Default admin on first startup** — Random password logged to console; no web-facing "create admin" page (security)
- **check_same_thread=False on SQLite** — Required for FastAPI's async thread pool; connections created in main thread, used in worker threads
- **Single-threaded MT5 polling** — MT5 API is not thread-safe; all calls wrapped in `threading.Lock`
- **Trade log replay for equity** — Computed at request time from trade_log.jsonl; no pre-computed cache needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion mismatch for token length**
- **Found during:** Task 1 GREEN
- **Issue:** Test expected `len(token) == 128` but `secrets.token_hex(32)` produces 64 hex characters
- **Fix:** Changed test assertion to `len(token) == 64` to match plan specification
- **Files modified:** `python/tests/dashboard/test_auth.py`
- **Committed in:** `1566093`

**2. [Rule 1 - Bug] Fixed missing test_user fixture in password hash test**
- **Found during:** Task 1 GREEN
- **Issue:** `test_password_hash_not_plaintext` didn't declare `test_user` fixture, so no user existed in DB
- **Fix:** Added `test_user` parameter to the test method
- **Files modified:** `python/tests/dashboard/test_auth.py`
- **Committed in:** `1566093`

**3. [Rule 1 - Bug] Added check_same_thread=False for SQLite cross-thread access**
- **Found during:** Task 1 GREEN
- **Issue:** FastAPI runs sync endpoint functions in thread pool; default SQLite rejects cross-thread access with `ProgrammingError`
- **Fix:** Added `check_same_thread=False` to `sqlite3.connect()` call
- **Files modified:** `python/dashboard/db.py`
- **Committed in:** `1566093`

**4. [Rule 1 - Bug] Fixed test imports from relative to absolute**
- **Found during:** Task 2 GREEN
- **Issue:** Test files used `from ..dashboard.api import` which resolved incorrectly to `python.tests.dashboard.api`
- **Fix:** Changed to absolute imports: `from python.dashboard.api import`
- **Files modified:** `python/tests/dashboard/test_positions.py`, `test_account.py`, `test_trades.py`, `test_alerts.py`
- **Committed in:** `209a99c`

**5. [Rule 1 - Bug] Fixed monkeypatch target for DRAWDOWN_ALERT_THRESHOLD**
- **Found during:** Task 3 GREEN
- **Issue:** Test monkeypatched `python.config.DRAWDOWN_ALERT_THRESHOLD` but notification.py imports the value at module level (by value, not reference)
- **Fix:** Changed monkeypatch target to `python.dashboard.notification.DRAWDOWN_ALERT_THRESHOLD`
- **Files modified:** `python/tests/dashboard/test_notification.py`
- **Committed in:** `4649b81`

**6. [Rule 1 - Bug] Moved MetaTrader5 import to module level in notification.py**
- **Found during:** Task 3 GREEN
- **Issue:** Local `import MetaTrader5 as mt5` inside method couldn't be patched by tests
- **Fix:** Imported at module level as `_mt5_module` with `try/except ImportError` for environments without MT5
- **Files modified:** `python/dashboard/notification.py`
- **Committed in:** `4649b81`

**7. [Rule 1 - Bug] Fixed datetime.utcnow() deprecation**
- **Found during:** Task 2 GREEN
- **Issue:** `datetime.utcnow()` is deprecated in Python 3.12+
- **Fix:** Replaced with `datetime.now(timezone.utc)`
- **Files modified:** `python/dashboard/api/equity.py`
- **Committed in:** `209a99c`

---

**Total deviations:** 7 auto-fixed (7 Rule 1 bugs)
**Impact on plan:** All auto-fixes necessary for correctness and testability. No scope creep. No architectural changes.

## Issues Encountered

- RED-phase stubs were pre-existing in untracked files from a prior partial execution. Converted to proper GREEN implementations across all three tasks.
- SQLite thread-safety error (`check_same_thread`) required understanding FastAPI's async thread pool behavior.
- Monkeypatch target selection required understanding Python's module import semantics (by-value for primitives).

## Next Phase Readiness

- Dashboard backend is complete with all API routes, WebSocket, and alerting
- Ready for Phase 4 Plan 2: SvelteKit frontend that consumes these APIs
- Server starts with: `cd python; python -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000`
- All tests run with: `cd python; python -m pytest tests/dashboard/ -v` (65 passing)

---
## Self-Check: PASSED

- [x] All 17 key implementation files exist on disk
- [x] All 3 task commits verified: `1566093`, `209a99c`, `4649b81`
- [x] SUMMARY.md created at `.planning/phases/04-monitoring-dashboard/04-01-SUMMARY.md`

---

*Phase: 04-monitoring-dashboard*
*Completed: 2026-05-28*
