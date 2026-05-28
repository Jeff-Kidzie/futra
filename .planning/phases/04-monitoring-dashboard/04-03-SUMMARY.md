---
phase: 04-monitoring-dashboard
plan: "03"
subsystem: deployment
tags: [caddy, windows-vps, powershell, nssm, lets-encrypt, https, cors, firewall, fastapi]

# Dependency graph
requires:
  - phase: 04-monitoring-dashboard
    plan: "01"
    provides: "FastAPI backend with CORS, config, auth, REST API, WebSocket"
  - phase: 04-monitoring-dashboard
    plan: "02"
    provides: "SvelteKit static build output at frontend/build/"
provides:
  - "Production FastAPI config with restricted CORS and StaticFiles serving"
  - "Caddy reverse proxy configuration with automatic Let's Encrypt HTTPS"
  - "Windows VPS deployment scripts (PowerShell startup)"
  - "Deployment guide with NSSM Windows Service setup and troubleshooting"
  - ".env.example template documenting all 17 production environment variables"
affects: ["05-future-phase-deployment"]

# Tech tracking
tech-stack:
  added:
    - "Caddy v2 reverse proxy with automatic HTTPS"
    - "NSSM (Non-Sucking Service Manager) for Windows Services"
    - "secrets module for session secret generation"
  patterns:
    - "Production CORS: restrict to https://{DASHBOARD_DOMAIN} with allow_methods=['GET','POST','PUT','DELETE']"
    - "Static file serving: FastAPI mounts frontend/build/ when DASHBOARD_DEV_MODE=false"
    - "PowerShell deployment: 5-step process (prereqs, pip, build, firewall, services)"
    - "Windows Firewall: allow 443 (HTTPS), block 8000 (direct FastAPI) from external"
    - "Session secret: auto-generate via secrets.token_hex(32), override via FUTRA_SESSION_SECRET env var"

key-files:
  created:
    - ".env.example - Template documenting all 17 production environment variables"
    - "deploy/Caddyfile - Caddy reverse proxy with security headers and auto-HTTPS"
    - "deploy/start-dashboard.ps1 - PowerShell startup script with 5-step deployment process"
    - "deploy/README.md - Step-by-step deployment guide for Windows VPS"
  modified:
    - "python/config.py - Added DASHBOARD_DOMAIN, SESSION_SECRET, FUTRA_INITIAL_BALANCE + import secrets"
    - "python/dashboard/main.py - Production CORS middleware with DASHBOARD_DOMAIN restriction"

key-decisions:
  - "Caddy over Nginx for Windows HTTPS — simpler config, native Windows build, automatic Let's Encrypt"
  - "NSSM for Windows Services over Task Scheduler — proper service lifecycle management, restart on failure"
  - "Auto-generated session secret via secrets.token_hex(32) — sessions survive restart only if FUTRA_SESSION_SECRET is explicitly set in .env"
  - "Restricted production CORS to https://{DASHBOARD_DOMAIN} — no wildcard origins in production"
  - "PowerShell script uses -- (double hyphen) instead of em dashes for compatibility"

patterns-established:
  - "Deployment pattern: FastAPI StaticFiles mount → Caddy reverse proxy → Windows Firewall → NSSM service"
  - "Security pattern: layered defense — Caddy HTTPS + restricted CORS + blocked direct FastAPI port + security headers"

requirements-completed: [DASH-06, DASH-07]

# Metrics
duration: 11min
completed: 2026-05-28
---

# Phase 4 Plan 3: Dashboard Production Deployment Summary

**Production deployment configuration with Caddy HTTPS reverse proxy, restricted CORS, Windows VPS startup scripts, firewall rules, and step-by-step deployment guide — enabling DASH-06 (internet access) and DASH-07 (HTTPS)**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-05-28T16:30:52+07:00
- **Completed:** 2026-05-28T16:41:59+07:00
- **Tasks:** 2
- **Files created/modified:** 6 files

## Accomplishments

- Production FastAPI configuration: restricted CORS to `https://{DASHBOARD_DOMAIN}` with allow_methods/allow_headers whitelist, serving frontend build via StaticFiles when not in dev mode
- Config additions: `DASHBOARD_DOMAIN` (env-driven), `SESSION_SECRET` (auto-generated with secrets.token_hex), `FUTRA_INITIAL_BALANCE` for equity computation
- Caddy reverse proxy configuration with automatic Let's Encrypt HTTPS, security headers (X-Frame-Options DENY, CSP, X-Content-Type-Options nosniff, Referrer-Policy), and log output
- PowerShell startup script (`deploy/start-dashboard.ps1`) with 5-step process: prerequisite checks (Python, Node.js, Caddy), pip install, frontend build, Windows Firewall configuration (allow 443, block 8000), and service launch with Caddy
- Deployment guide (`deploy/README.md`) with 7 sections covering prerequisites, clone, env config, Caddy domain setup, one-time start, NSSM Windows Service installation, verification, and troubleshooting
- `.env.example` documenting all 17 production environment variables with descriptions

## Task Commits

Each task committed atomically:

1. **Task 1: Production FastAPI config, .env.example, and Caddy reverse proxy** — `ee1d0ec` (feat)
2. **Task 2: Windows VPS deployment scripts and deployment guide** — `58bbc06` (feat)

## Files Created/Modified

- `python/config.py` — Added `import secrets`, `DASHBOARD_DOMAIN`, `SESSION_SECRET` (auto-generated), `FUTRA_INITIAL_BALANCE`
- `python/dashboard/main.py` — Production CORS middleware with `allow_origins=[f"https://{DASHBOARD_DOMAIN}"]`, restricted methods/headers
- `.env.example` — 17 environment variables: MT5 credentials (3), dashboard settings (4), auth (2), alerts (2), AI engine (2), data (4)
- `deploy/Caddyfile` — Caddy reverse proxy config: `reverse_proxy localhost:8000` with 4 OWASP security headers + CSP for Inter font CDN
- `deploy/start-dashboard.ps1` — PowerShell startup: prerequisite checks, pip install, frontend build, firewall (netsh), service launch (FastAPI + Caddy), `-Dev` mode support
- `deploy/README.md` — 7-section deployment guide: prerequisites, clone, env config (.env.example → .env), Caddy domain, one-time start + NSSM Windows Services, verification, troubleshooting (4 scenarios)

## Decisions Made

- **Caddy over Nginx for Windows** — Caddy has native Windows binaries and simpler config; automatic Let's Encrypt requires zero additional configuration
- **NSSM for Windows Services** — Proper service lifecycle (start/stop/restart) compared to Task Scheduler; supports auto-start on boot
- **Auto-generated session secret** — `secrets.token_hex(32)` generates a random 64-char hex secret if `FUTRA_SESSION_SECRET` is not set; this means sessions invalidate on restart unless the env var is explicitly configured (fail-secure)
- **Restricted production CORS** — Methods limited to GET/POST/PUT/DELETE, headers limited to Authorization/Content-Type; no wildcard origins in production

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Em dashes in PowerShell script caused parse errors**
- **Found during:** Task 2 (PowerShell script verification)
- **Issue:** The plan template for `deploy/start-dashboard.ps1` contained Unicode em dash characters (`\u2014`) in strings like "Production Startup" and section headers. PowerShell's parser (both `PSParser` and `ScriptBlock::Create`) failed to parse the file with errors at lines 93, 130, 135, 167.
- **Fix:** Replaced all em dash characters (`\u2014`) with ASCII double-hyphens (`--`) throughout the script.
- **Files modified:** `deploy/start-dashboard.ps1`
- **Verification:** `[ScriptBlock]::Create()` parses successfully; `Get-Command deploy\start-dashboard.ps1 -Syntax` returns clean output.
- **Committed in:** `58bbc06`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** No scope change. The PowerShell script content is functionally identical — only cosmetic character substitution. All plan acceptance criteria still pass.

## Issues Encountered

None — plan executed cleanly with one minor character-encoding issue that was fixed inline.

## Threat Flags

None detected. All threat mitigations from the plan's `<threat_model>` are implemented:
- T-04-14 (Spoofing): Caddy Let's Encrypt auto-HTTPS configured
- T-04-15 (Tampering): Security headers in Caddyfile (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- T-04-16 (Information Disclosure): Windows Firewall blocks external port 8000, FastAPI listens on localhost only
- T-04-17 (DoS): Accepted for Phase 4 (single-user system)
- T-04-18 (Elevation): SESSION_SECRET documented as must-change; auto-generates if not set (fail-secure)
- T-04-19 (Information Disclosure): StaticFiles only serves frontend/build/; .env.example has no secrets
- T-04-20 (Tampering): CSP restricts scripts to 'self', prevents inline scripts

## Known Stubs

None. All deployment artifacts are production-ready:
- `.env.example` documents all variables but requires user to fill in real values (by design)
- `deploy/Caddyfile` uses placeholder domain `dashboard.yourdomain.com` — documented in README as step 4
- `deploy/start-dashboard.ps1` handles missing Caddy gracefully (falls back to http://localhost:8000)

## Next Phase Readiness

- Dashboard deployment configuration is complete
- A fresh Windows VPS can be set up by following `deploy/README.md` end-to-end
- Phase 4 (Monitoring Dashboard) is now fully complete across all 3 plans:
  - 04-01: FastAPI backend with auth, REST API, WebSocket, alerting
  - 04-02: SvelteKit frontend with 7 route pages, 10 custom components, charts
  - 04-03: Production deployment with Caddy HTTPS, firewall, Windows Services
- Ready for milestone completion (`/gsd-complete-milestone`) or Phase 5 planning

## Self-Check: PASSED

- [x] All 6 key files exist on disk: `.env.example`, `deploy/Caddyfile`, `deploy/start-dashboard.ps1`, `deploy/README.md`, `python/config.py`, `python/dashboard/main.py`
- [x] Both task commits verified: `ee1d0ec`, `58bbc06`
- [x] All 13 Task 1 acceptance criteria verified
- [x] All 11 Task 2 acceptance criteria verified
- [x] CONTENTS CHECK: `python/config.py` contains DASHBOARD_DOMAIN, SESSION_SECRET, FUTRA_INITIAL_BALANCE
- [x] CONTENTS CHECK: `python/dashboard/main.py` has production CORS `else` block with `DASHBOARD_DOMAIN`
- [x] CONTENTS CHECK: `.env.example` has 17 FUTRA_* environment variables
- [x] CONTENTS CHECK: `deploy/Caddyfile` has `reverse_proxy localhost:8000` and 4 security headers
- [x] CONTENTS CHECK: Powershell script parses without errors

---

*Phase: 04-monitoring-dashboard*
*Completed: 2026-05-28*
