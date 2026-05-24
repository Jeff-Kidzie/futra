# Phase 1: Foundation + Safety - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The trading system connects to MT5, executes trades safely with emergency shutdown, and maintains reliable communication between EA and Python — it works even if the AI layer crashes. This phase delivers: EA core with kill switch, market orders, position management; data pipeline with MT5 Python connection, multi-asset data, file-based IPC; and risk controls with circuit breakers, position sizing validation, and safe defaults.
</domain>

<decisions>
## Implementation Decisions

### Kill Switch
- **D-01:** Kill switch uses file-based signal — EA polls a kill switch file every tick (consistent with DWX Connect IPC pattern)
- **D-02:** Kill switch behavior is configurable per activation — file includes a `close_positions` flag; when true, EA closes all open positions before halting; when false, EA only stops placing new trades
- **D-03:** Kill switch is triggered via a Python script that writes the kill switch file — can be run remotely via SSH or as a scheduled task
- **D-04:** Kill switch auto-resets after a configurable timeout period — trading auto-resumes when timeout expires (no manual reset required)

### Data Flow Architecture
- **D-05:** Python pulls market data directly via MT5 API (MetaTrader5 package) — EA does not push data to files; Python has its own MT5 connection for data
- **D-06:** EA reads AI parameters via per-symbol params files with staleness check — EA compares file modification timestamp and skips re-parsing if unchanged
- **D-07:** Data refresh uses periodic polling — configurable intervals per timeframe (e.g., every 15 min for M15 bars)
- **D-08:** IPC files are organized per-symbol — each symbol gets its own params file (e.g., `EURUSD_params.json`, `GBPUSD_params.json`), avoiding file-locking contention

### Testing Strategy
- **D-09:** Pure MQL5 EA implementation with Python mock integration tests — no C++ abstraction layer; EA is written in native MQL5
- **D-10:** IPC integration tests as the primary testing approach — EA behavior is tested through its file interface: write params, check if EA reads and acts correctly, verify output
- **D-11:** Python side uses mock MT5 data files in test harness — no live MT5 connection required for tests; mock data files simulate MT5 API responses
- **D-12:** Automated tests run on pre-push/CI — pytest for Python side, integration test scripts for EA; both run automatically to catch regressions

### the Agent's Discretion
- IPC message protocol details (JSON structure, file naming convention, heartbeat mechanism) — not discussed; agent should follow DWX Connect conventions
- Safe default parameter values (SL/TP percentages, position sizing rules when AI is offline) — not discussed; agent should choose conservative defaults
- Error recovery specifics (MT5 reconnection behavior, IPC timeout values, fallback strategies) — not discussed; agent should implement robust error handling per REQUIREMENTS.md DATA-10
- Circuit breaker threshold defaults (max drawdown %, daily loss cap, max positions per symbol) — not discussed; agent should choose conservative starting values

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Project scope, constraints, key decisions, and core value statement
- `.planning/REQUIREMENTS.md` — Full v1 requirements (DATA-01 through DATA-10, RISK-01 through RISK-05, AI-03)
- `.planning/ROADMAP.md` §Phase 1 — Phase goal, success criteria, plan breakdown

### Architecture References
- `AGENTS.md` — Technology stack (MQL5 EA, Python AI, file-based IPC, FastAPI, SvelteKit, SQLite) and conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- DWX Connect pattern for file-based IPC between MQL5 EA and Python (referenced in REQUIREMENTS.md DATA-09 and PROJECT.md)
- MetaTrader5 Python package for data access (referenced in AGENTS.md tech stack)
- Safe defaults pattern — EA must continue trading with hardcoded safe defaults when AI is unavailable (AI-03)

### Integration Points
- MT5 terminal (MQL5 EA runs inside it)
- MT5 Python API (MetaTrader5 package) — Python connects independently for data
- File-based IPC directory (DWX Connect pattern) — shared directory for EA ↔ Python communication
- Kill switch file — read by EA every tick

</code_context>

<specifics>
## Specific Ideas

- Kill switch Python script should be executable remotely (SSH or scheduled task) since the MT5 machine is likely a headless VPS
- Per-symbol params files avoid the need for file locking or concurrent access handling across multiple EA instances
- Staleness check (timestamp comparison) on params file reads prevents unnecessary JSON parsing on every tick
- IPC integration tests mean: write a params file → let EA process it → check EA's output/log file for expected behavior
- Test harness uses mock data files to simulate MT5 API responses, enabling fully local testing without a live MT5 connection

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Foundation + Safety*
*Context gathered: 2026-05-24*