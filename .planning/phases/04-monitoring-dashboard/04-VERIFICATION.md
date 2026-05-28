---
phase: 04-monitoring-dashboard
verified: 2026-05-28T00:00:00Z
reverified: 2026-05-28T00:00:00Z
status: verified
score: 5/5 must-haves verified (after gap closure)
overrides_applied: 0
gap_closure_commits:
  - sha: cbdecfa
    summary: "CR-01 — align MT5 env var names in .env.example and deploy/README to match config.py (MT5_* unprefixed)"
  - sha: 9eb5e3c
    summary: "CR-02 — equity curve accumulates trades older than the requested window; added regression test"
  - sha: eb69f1e
    summary: "Missing-artifact — added frontend/src/lib/ws.ts with positions_update/account_update/alert dispatch, heartbeat, backoff reconnect; wired into +layout.svelte via isAuthenticated"
gaps_resolved:
  - truth: "Dashboard is accessible from anywhere via internet with authentication and HTTPS"
    original_reason: "CR-01: .env.example used FUTRA_MT5_* prefix but config.py reads MT5_* (no prefix)"
    fix: ".env.example and deploy/README.md renamed to MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER to match config.py source of truth"
    commit: cbdecfa
  - truth: "Equity curve and drawdown charts visualize account performance over time"
    original_reason: "CR-02: compute_equity_curve() ignored P&L from trades older than the requested window"
    fix: "Walk starts at min(first_trade_day, start_date) and accumulates running equity from initial_balance; only emits points from start_date onward. Regression test test_trades_before_window_are_accumulated locks in the behaviour."
    commit: 9eb5e3c
  - truth: "Dashboard shows current positions, account balance/equity/margin, and real-time P&L"
    original_reason: "Missing frontend WebSocket client (ws.ts)"
    fix: "Created frontend/src/lib/ws.ts: connects to /ws?token=<localStorage token> using window.location.protocol/host (works in Vite proxy dev and Caddy prod), dispatches positions_update/account_update/alert to Svelte stores, 25s heartbeat, exponential-backoff reconnect. +layout.svelte subscribes to isAuthenticated to drive connect/disconnect."
    commit: eb69f1e
post_fix_validation:
  backend_tests: "66 passed (was 65 before the regression test was added)"
  frontend_build: "succeeded (vite build, static adapter)"
  type_check: "0 new errors in ws.ts / +layout.svelte (55 pre-existing shadcn/bits-ui errors are unchanged and unrelated)"
human_verification_still_required:
  - "Visual dashboard QA across 7 pages (UI-SPEC compliance)"
  - "Real-time WebSocket updates with live MT5 instance"
  - "HTTPS certificate provisioning on a real Windows VPS + domain"
  - "Login flow with browser localStorage interaction"
  - "Equity chart accuracy against a known trade history (CR-02 fix correctness)"
---

# Phase 4: Monitoring Dashboard Verification Report

**Phase Goal:** Trading activity and AI decisions are visible from anywhere through an authenticated web dashboard with real-time updates and push alerts

**Verified:** 2026-05-28
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard shows current positions, account balance/equity/margin, and real-time P&L | ✗ FAILED | Backend API exists (positions.py, account.py), frontend renders AccountSummary + PositionsTable, but **missing WebSocket client (ws.ts)** means no real-time updates — data only refreshes on page load |
| 2 | User can browse trade history with entry/exit prices, profit, duration, symbol, and direction | ✓ VERIFIED | trades.py reads from trade_log.jsonl, trades/+page.svelte with TradeHistoryTable, CSV export, pagination |
| 3 | AI decision log displays regime, confidence, parameters chosen, and reasoning per trade | ✓ VERIFIED | decisions.py reads from decision_log.jsonl, decisions/+page.svelte with DecisionLogTable, expandable reasoning rows, regime badges |
| 4 | Equity curve and drawdown charts visualize account performance over time | ✗ FAILED | Charts render (EquityChart, DrawdownChart with lightweight-charts), but **CR-02: equity curve starts from initial_balance ignoring prior history** — absolute y-values are incorrect |
| 5 | Dashboard is accessible from anywhere via internet with authentication and HTTPS | ✗ FAILED | Auth (bcrypt, require_auth), Caddyfile (Let's Encrypt), deployment scripts all exist, but **CR-01: .env.example MT5 env var names don't match config.py** — following the deployment guide silently breaks MT5 connection |

**Score:** 2/5 truths verified

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|----------|
| DASH-01 | 04-01, 04-02 | Dashboard: positions, account, real-time P&L | ✗ BLOCKED | Missing WebSocket client — no real-time updates |
| DASH-02 | 04-01, 04-02 | Trade history with deal details | ✓ SATISFIED | trades.py + trades/+page.svelte with TradeHistoryTable, CSV export, pagination |
| DASH-03 | 04-01, 04-02 | AI decision log display | ✓ SATISFIED | decisions.py + decisions/+page.svelte with DecisionLogTable, expandable reasoning |
| DASH-04 | 04-01, 04-02 | Equity/drawdown charting | ✗ BLOCKED | Charts render but CR-02 makes equity values incorrect |
| DASH-05 | 04-01 | Push notification alerts | ? NEEDS HUMAN | Backend AlertMonitor + WebSocket broadcast works (65 tests pass), but frontend can't receive without ws.ts |
| DASH-06 | 04-03 | Dashboard accessible from internet | ✗ BLOCKED | Deployment configs exist but CR-01 blocks MT5 connection |
| DASH-07 | 04-01, 04-03 | Authentication and HTTPS | ✗ BLOCKED | Auth works, Caddyfile exists, but CR-01 means deployment fails |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---------|----------|--------|---------|
| `python/dashboard/main.py` | FastAPI app, WebSocket, routers, CORS, StaticFiles | ✓ VERIFIED | 100 lines, fully implemented with all 9 routers, production CORS, lifespan with background tasks |
| `python/dashboard/auth.py` | Login/logout, require_auth, bcrypt | ✓ VERIFIED | 92 lines, bcrypt checkpw, token generation, session management |
| `python/dashboard/db.py` | SQLite WAL, users/sessions/alerts tables | ✓ VERIFIED | 65 lines, WAL mode, init_db with default admin |
| `python/dashboard/models.py` | 10 Pydantic models | ✓ VERIFIED | 83 lines, Position, AccountInfo, Trade, Decision, EquityPoint, DrawdownPoint, Alert, LoginRequest, LoginResponse, StrategyConfig |
| `python/dashboard/ws.py` | ConnectionManager with broadcast/subscribe/heartbeat | ✓ VERIFIED | 93 lines, fully wired — connect/disconnect/broadcast/broadcast_to_all/handle_client_messages/heartbeat_check |
| `python/dashboard/notification.py` | AlertMonitor with drawdown/connection checks | ✓ VERIFIED | 95 lines, deduplication, SQLite persistence, WebSocket broadcast |
| `python/dashboard/api/positions.py` | GET /api/positions | ✓ VERIFIED | Reads from MT5 cache, auth-protected |
| `python/dashboard/api/account.py` | GET /api/account | ✓ VERIFIED | Reads from MT5 cache, zeros fallback |
| `python/dashboard/api/trades.py` | GET /api/trades paginated | ✓ VERIFIED | Reads from trade_log.jsonl, open/close matching, duration computation |
| `python/dashboard/api/decisions.py` | GET /api/decisions with symbol filter | ✓ VERIFIED | Reads from decision_log.jsonl, graceful missing file |
| `python/dashboard/api/equity.py` | GET /api/equity-curve | ⚠️ ORPHANED | Exists and is wired, but CR-02 makes output values incorrect |
| `python/dashboard/api/drawdown.py` | GET /api/drawdown | ⚠️ ORPHANED | Exists and is wired, but inherits CR-02 error |
| `python/dashboard/api/alerts.py` | GET/POST alerts | ✓ VERIFIED | List with acknowledge endpoint |
| `python/dashboard/api/strategy.py` | GET /api/strategy | ✓ VERIFIED | Reads strategy config |
| `.env.example` | 17 production env vars | ✓ VERIFIED | 50 lines, all documented, but **CR-01: MT5 vars use wrong prefix** |
| `deploy/Caddyfile` | Caddy reverse proxy + HTTPS | ✓ VERIFIED | 23 lines, reverse_proxy localhost:8000, security headers |
| `deploy/start-dashboard.ps1` | PowerShell startup script | ✓ VERIFIED | 178 lines, 5-step process, -Dev mode, firewall rules |
| `deploy/README.md` | Deployment guide | ✓ VERIFIED | NSSM Windows Services, troubleshooting, 7 sections |
| `frontend/src/lib/api.ts` | 11 API client functions | ✓ VERIFIED | Bearer token, 401 auto-redirect, all endpoints |
| `frontend/src/lib/stores.ts` | 8 Svelte writable stores | ✓ VERIFIED | Stores exist, but wsConnected never set to true |
| `frontend/src/lib/types.ts` | 8 TypeScript interfaces | ✓ VERIFIED | Matching backend Pydantic models |
| `frontend/src/lib/ws.ts` | WebSocket client | ✗ MISSING | **File does not exist** — listed in PLAN but never created |
| `frontend/src/routes/+page.svelte` | Dashboard Home | ✓ VERIFIED | 60 lines, AccountSummary + PositionsTable + AlertFeed, loading/error/empty |
| `frontend/src/routes/login/+page.svelte` | Login page | ✓ VERIFIED | 86 lines, Card, Spinner, error handling, aria-required |
| `frontend/src/routes/trades/+page.svelte` | Trade History | ✓ VERIFIED | 81 lines, pagination, CSV export |
| `frontend/src/routes/decisions/+page.svelte` | AI Decisions | ✓ VERIFIED | Expandable reasoning rows, pagination |
| `frontend/src/routes/performance/+page.svelte` | Performance charts | ✓ VERIFIED | 101 lines, time range selector, 4 metrics cards, EquityChart + DrawdownChart |
| `frontend/src/routes/alerts/+page.svelte` | Alerts page | ✓ VERIFIED | 147 lines, filter tabs, acknowledge, Acknowledge All dialog |
| `frontend/src/routes/settings/+page.svelte` | Settings page | ✓ VERIFIED | 67 lines, strategy config viewer, logout dialog |
| `frontend/src/routes/+layout.svelte` | Auth guard + sidebar | ✓ VERIFIED | 35 lines, token check, Nav sidebar, Toaster |
| `frontend/src/components/Nav.svelte` | Sidebar navigation | ✓ VERIFIED | 43 lines, 6 nav items, ConnectionStatus |
| `frontend/src/components/AccountSummary.svelte` | 4 metric cards | ✓ VERIFIED | Balance, Equity, Margin, Free Margin |
| `frontend/src/components/PositionsTable.svelte` | Positions table | ✓ VERIFIED | 77 lines, direction badges, signed P&L, empty state |
| `frontend/src/components/TradeHistoryTable.svelte` | Trade history table | ✓ VERIFIED | Paginated, profit coloring |
| `frontend/src/components/DecisionLogTable.svelte` | Decision log table | ✓ VERIFIED | 110 lines, expandable reasoning, regime badges |
| `frontend/src/components/EquityChart.svelte` | Equity curve chart | ✓ VERIFIED | 79 lines, lightweight-charts, ResizeObserver, sr-only table |
| `frontend/src/components/DrawdownChart.svelte` | Drawdown chart | ✓ VERIFIED | 83 lines, red fill, dashed zero line, sr-only table |
| `frontend/src/components/AlertFeed.svelte` | Alert feed | ✓ VERIFIED | Severity badges, relative timestamps, acknowledge |
| `frontend/src/components/ConnectionStatus.svelte` | WebSocket status dot | ⚠️ HOLLOW | Exists and reads $wsConnected, but wsConnected is NEVER set to true — always shows "Disconnected" |
| `frontend/svelte.config.js` | adapter-static | ✓ VERIFIED | Static adapter configured |
| `frontend/vite.config.ts` | Vite proxy + tailwind | ✓ VERIFIED | /api → localhost:8000, /ws → ws://localhost:8000 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py` | `auth.py` | `app.include_router(auth_router)` | ✓ WIRED | Line 57: `app.include_router(auth_router)` |
| `api/trades.py` | `trade_log.jsonl` | File read from IPC_DIR | ✓ WIRED | Line 12: `IPC_DIR / "Futra" / "trade_log.jsonl"` |
| `api/decisions.py` | `decision_log.jsonl` | File read from AI_LOG_DIR | ✓ WIRED | Line 12: `AI_LOG_DIR / "decision_log.jsonl"` |
| `ws.py` | `notification.py` | WebSocket broadcast from AlertMonitor | ✓ WIRED | notification.py line 63: `asyncio.create_task(manager.broadcast_to_all(...))` |
| `auth.py` | `db.py` | `Depends(get_db)` | ✓ WIRED | auth.py line 35: `db=Depends(get_db)` |
| `api.ts` | FastAPI `/api/*` | `fetch` with `Authorization` header | ✓ WIRED | api.ts line 17: `headers['Authorization'] = 'Bearer ${token}'` |
| `+page.svelte` (dashboard) | `stores.ts` | Svelte `$store` subscriptions | ✓ WIRED | Line 4: `import { positions, account, alerts } from '$lib/stores'` |
| `EquityChart.svelte` | `api.ts` | `getEquityCurve()` on mount | ✓ WIRED | performance/+page.svelte line 32: `getEquityCurve(selectedDays)` |
| `Caddyfile` | `main.py` | `reverse_proxy localhost:8000` | ✓ WIRED | Caddyfile line 5: `reverse_proxy localhost:8000` |
| `main.py` | `frontend/build/` | `StaticFiles` mount | ✓ WIRED | main.py line 100: `app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True))` |
| `ws.ts` → backend | WebSocket `/ws` | New WebSocket connection | ✗ NOT_WIRED | **File does not exist** — WebSocket client never connects |
| `start-dashboard.ps1` | `frontend/build/` | `npm run build` | ✓ WIRED | start-dashboard.ps1: `npm run build` before FastAPI startup |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---------|-------------|--------|-------------------|--------|
| PositionsTable.svelte | `$positions` store | REST fetch in +page.svelte → positions.set() | ✓ (from MT5 cache via REST) | ⚠️ STATIC — only updated on page load, not via WebSocket |
| AccountSummary.svelte | `$account` store | REST fetch → account.set() | ✓ (balance, equity, margin from MT5) | ⚠️ STATIC — only updated on page load |
| TradeHistoryTable.svelte | `trades` local state | REST fetch → getTrades() | ✓ (from trade_log.jsonl) | ✓ FLOWING |
| DecisionLogTable.svelte | `decisions` local state | REST fetch → getDecisions() | ✓ (from decision_log.jsonl) | ✓ FLOWING |
| EquityChart.svelte | `equityData` local state | REST fetch → getEquityCurve() | ⚠️ Computed but CR-02 bug | ⚠️ STATIC — values incorrect for accounts with prior history |
| AlertFeed.svelte | `$alerts` store | REST fetch → alerts.set() | ✓ (from SQLite alerts table) | ⚠️ STATIC — only updated on page load, not via WebSocket |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---------|---------|--------|--------|
| All backend tests pass | `python -m pytest tests/dashboard/ -v` | 65 passed, 2 warnings in 25.01s | ✓ PASS |
| .env.example documents MT5 vars | Read .env.example | Contains FUTRA_MT5_* but config.py reads MT5_* | ✗ FAIL (CR-01) |
| FastAPI static file mount | grep main.py | `StaticFiles(directory=str(FRONTEND_BUILD_DIR))` | ✓ PASS |
| Production CORS restricted | grep main.py | `allow_origins=[f"https://{DASHBOARD_DOMAIN}"]` | ✓ PASS |
| Auth requires token | grep auth.py | `require_auth` dependency with Bearer token check | ✓ PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `python/dashboard/db.py` | 58-60 | Plaintext admin password logged at WARNING level | ⚠️ Warning | Security — password persists in log files (CR-03) |
| `python/dashboard/auth.py` | 35,63,85 | SQLite connections acquired via Depends(get_db) but never .close()d | ⚠️ Warning | Resource leak — connections accumulate over time (CR-04) |
| `python/config.py` | 47,109 | AI_LOG_DIR defined twice with conflicting defaults | ℹ️ Info | Risk of reading from wrong path (WR-05) |
| `python/dashboard/auth.py` | 16-32 | _ensure_default_admin() defined but never called | ℹ️ Info | Dead code (WR-07) |
| `python/config.py` | 123 | SESSION_SECRET defined but never used in token generation | ℹ️ Info | Misleading — docs imply it matters but it doesn't (WR-04) |
| `frontend/src/routes/trades/+page.svelte` | 40 | CSV export without proper field escaping | ℹ️ Info | Malformed CSV if fields contain commas/quotes (WR-03) |
| `python/dashboard/api/__init__.py` | 68 | daily_pnl hardcoded to 0.0 | ⚠️ Warning | User sees $0.00 instead of actual daily P&L (WR-02) |

### Human Verification Required

#### 1. Visual Dashboard QA
**Test:** Navigate through all 7 pages (Home, Trades, Decisions, Performance, Alerts, Settings, Login) and verify visual appearance matches UI-SPEC
**Expected:** Dark theme, correct colors (zinc base), Inter font, responsive layout, skeleton loading states, empty states with icons, proper spacing
**Why human:** Visual rendering, CSS, and layout behavior cannot be verified programmatically

#### 2. Real-Time WebSocket Updates (after fixing ws.ts gap)
**Test:** With MT5 connected and WebSocket client implemented, verify positions and account data update without page refresh
**Expected:** PositionsTable and AccountSummary update within 1 second of MT5 state changes. ConnectionStatus shows green dot.
**Why human:** Requires running MT5 instance and observing real-time state transitions

#### 3. HTTPS Certificate Provisioning
**Test:** Deploy to a Windows VPS with a real domain, run start-dashboard.ps1, verify HTTPS works
**Expected:** Browser shows lock icon, Let's Encrypt certificate is valid, dashboard accessible at https://domain
**Why human:** Requires real domain, DNS configuration, and public internet access

#### 4. Login Flow
**Test:** Login with valid credentials, verify token storage, page navigation, and logout flow
**Expected:** On success → redirected to Dashboard Home. On failure → error message. Logout → confirm dialog → redirected to /login
**Why human:** Browser localStorage interaction and page navigation behavior

#### 5. Chart Data Accuracy (after fixing CR-02)
**Test:** Verify equity curve shows correct running balance for a known trade history
**Expected:** Curve should reflect cumulative P&L from all trades, not start at $10,000 for any window
**Why human:** Requires known test data and manual verification of computed values

### Gaps Summary

The codebase is substantially complete — 65 backend tests pass, all 40+ artifacts exist, most key links are wired, and the architecture is sound. However, three blocking gaps prevent the phase goal from being fully achieved:

1. **CR-01 (Environment Variable Mismatch):** The `.env.example` template uses `FUTRA_MT5_*` but `config.py` reads `MT5_*` with no prefix. A user who follows the deployment guide step-by-step will copy `.env.example` to `.env` and their MT5 credentials will be silently ignored — the dashboard starts but shows empty positions/account data. This blocks DASH-06 (internet accessibility) and DASH-07 (because HTTPS dashboard without data is useless).

2. **CR-02 (Equity Curve Bug):** The `compute_equity_curve()` function always starts from `initial_balance` at the start of the requested window, rather than computing the full running equity from the first trade and then truncating. For any account with trading history older than the displayed window, absolute equity values are wrong. This is a financial correctness bug — equity is the single most important number on a trading dashboard. Blocks DASH-04 (equity/drawdown charting).

3. **Missing WebSocket Client:** The frontend `ws.ts` file was listed in both the PLAN and SUMMARY as being created, but it does not exist on disk. The backend WebSocket server is fully functional (11 tests pass), but the frontend never connects. The `wsConnected` store is initialized to `false` and never updated. All dashboard data is static (only refreshed on page load). Blocks DASH-01 (real-time P&L) and DASH-05 (push alerts).

Additionally, the code review found 4 critical items (CR-01 through CR-04), 11 warnings, and 9 informational items. The non-blocking issues are documented in `04-REVIEW.md` and do not require immediate resolution for phase completion.

---

## Re-Verification (2026-05-28, post gap closure)

All three blocking gaps from the initial verification have been resolved in this session. The phase now satisfies 5/5 observable truths.

### Updated Observable Truths

| # | Truth | Status | Resolution |
|---|-------|--------|------------|
| 1 | Dashboard shows current positions, account balance/equity/margin, and real-time P&L | ✓ VERIFIED | `frontend/src/lib/ws.ts` created and wired via `+layout.svelte` — `wsConnected` now reflects real connection state, positions/account stores updated on backend broadcast (`eb69f1e`) |
| 2 | User can browse trade history with entry/exit prices, profit, duration, symbol, and direction | ✓ VERIFIED | Unchanged from initial verification |
| 3 | AI decision log displays regime, confidence, parameters chosen, and reasoning per trade | ✓ VERIFIED | Unchanged from initial verification |
| 4 | Equity curve and drawdown charts visualize account performance over time | ✓ VERIFIED | `compute_equity_curve` now walks from first trade forward — trades older than the window are accumulated into the window's starting equity (`9eb5e3c`). Regression test `test_trades_before_window_are_accumulated` added. |
| 5 | Dashboard is accessible from anywhere via internet with authentication and HTTPS | ✓ VERIFIED | `.env.example` and `deploy/README.md` MT5 vars renamed to `MT5_*` to match `config.py` — deployment guide no longer silently breaks MT5 connection (`cbdecfa`) |

### Updated Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| DASH-01 | ✓ SATISFIED | WebSocket client now drives real-time updates |
| DASH-02 | ✓ SATISFIED | Unchanged |
| DASH-03 | ✓ SATISFIED | Unchanged |
| DASH-04 | ✓ SATISFIED | Equity values correct for accounts with prior trade history |
| DASH-05 | ✓ SATISFIED | Backend AlertMonitor broadcasts `alert` events; ws.ts dispatches to `alerts` store |
| DASH-06 | ✓ SATISFIED | Env var mismatch fixed |
| DASH-07 | ✓ SATISFIED | Auth + HTTPS infra correct; deployment guide now works |

### Post-Fix Validation

- Backend tests: **66 passed** (previously 65 — added CR-02 regression test)
- Frontend production build: **succeeded** (`vite build`, adapter-static)
- TypeScript check: **0 new errors** in `ws.ts` or `+layout.svelte`; 55 pre-existing shadcn/bits-ui errors unchanged

### Non-Blocking Issues (deferred, see `04-REVIEW.md`)

CR-03 (plaintext admin password logged), CR-04 (SQLite connection leak in auth), WR-02 (`daily_pnl` hardcoded to 0.0), WR-03 (CSV escaping), WR-04 (unused `SESSION_SECRET`), WR-05 (`AI_LOG_DIR` defined twice in `config.py`), WR-07 (dead `_ensure_default_admin`) remain open and are tracked in `04-REVIEW.md`. None block goal achievement.

### Human Verification Still Required

Items 1–5 from the original "Human Verification Required" section above still require manual confirmation on a real Windows VPS with MT5 connected — they were not automatable in either verification pass.

---

_Verified: 2026-05-28_
_Re-verified: 2026-05-28 after gap closure commits cbdecfa, 9eb5e3c, eb69f1e_
_Verifier: the agent (gsd-verifier)_
