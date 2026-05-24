# Phase 1: Foundation + Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 01-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 1-Foundation + Safety
**Areas discussed:** Kill switch trigger & behavior, Data flow architecture, Testing strategy for MQL5

---

## Kill Switch Trigger & Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| File-based signal | EA polls a kill switch file every tick — simple, reliable, works even if Python crashes | ✓ |
| MT5 keyboard shortcut | Press a key in MT5 terminal to trigger — immediate but requires physical access to the VPS | |
| File signal + MT5 event | Python writes file + can call a custom indicator to send event — both channels but more complex | |

**User's choice:** File-based signal
**Notes:** Consistent with DWX Connect IPC pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable per activation | Kill switch file has a `close_positions: true/false` field — EA respects it on activation | ✓ |
| Always close all positions | Kill switch always halts AND closes all positions — maximum safety | |
| Halt only, no auto-close | Kill switch only stops new trades, leaves existing positions running — less disruptive but riskier | |

**User's choice:** Configurable per activation
**Notes:** `close_positions` flag in kill switch file

| Option | Description | Selected |
|--------|-------------|----------|
| Python script | Script that writes the kill switch file with configurable params — can be run remotely via SSH or scheduled task | ✓ |
| Shell script (no Python) | Batch/PowerShell that writes the kill file directly — no Python dependency, works if Python is crashed | |
| Both | Python for programmatic/API triggers, shell script for manual emergency when Python is down | |

**User's choice:** Python script

| Option | Description | Selected |
|--------|-------------|----------|
| Manual reset only | Kill switch persists until explicitly cleared — safe default, avoids accidental restart | |
| Auto-reset with timeout | Auto-reset after configurable timeout — trades resume automatically | ✓ |
| Reset on MT5 restart | Kill switch clears when MT5 restarts — restarts can happen for many reasons | |

**User's choice:** Auto-reset with timeout

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-resume trading | After timeout, EA resumes trading automatically | ✓ |
| Conditional resume | After timeout, EA checks market conditions before resuming | |
| Paused until manual resume | After timeout, kill switch clears but EA stays paused until manual resume | |

**User's choice:** Auto-resume trading after timeout
**Notes:** User accepted the trade-off — could re-enter a bad market, but trading auto-resumes

---

## Data Flow Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Python pull via MT5 API | Python uses MetaTrader5 package to pull data directly — EA doesn't push data, only reads AI params from files | ✓ |
| EA push to files | EA writes OHLCV data to files, Python reads them — more complex EA code, but Python doesn't need MT5 connection | |
| Hybrid (API + file push) | Python pulls historical/lower-TF data via API, EA pushes real-time ticks via files — dual channel, more complex | |

**User's choice:** Python pull via MT5 API

| Option | Description | Selected |
|--------|-------------|----------|
| Pull: EA reads params file | EA polls a file directory every tick for Python parameter updates — simple, consistent with kill switch pattern | ✓ |
| Pull with staleness check | EA polls but checks timestamp to skip unchanged params — avoids re-parsing | ✓ |
| Push: Python signals EA | Python writes params then sends event/pipe signal — faster but more complex | |

**User's choice:** Pull with staleness check (both "EA reads params file" and "staleness check" selected)

| Option | Description | Selected |
|--------|-------------|----------|
| Periodic polling | Python periodically pulls data via MT5 API at fixed intervals — predictable, low overhead | ✓ |
| Real-time tick subscription | Python subscribes to real-time ticks and reacts to every price change — more responsive but higher CPU | |
| Hybrid (periodic + real-time) | Periodic for most timeframes, real-time for active TF — balances responsiveness and efficiency | |

**User's choice:** Periodic polling

| Option | Description | Selected |
|--------|-------------|----------|
| Per-symbol params files | Each symbol gets its own file (e.g., EURUSD_params.json) — simple, avoids file locking between symbols | ✓ |
| Single shared params file | One file for all symbols — simpler file management but needs locking | |
| Atomic write (temp+rename) | Python writes to temp file then atomically renames — eliminates partial read but more complex | |

**User's choice:** Per-symbol params files

---

## Testing Strategy for MQL5

| Option | Description | Selected |
|--------|-------------|----------|
| C++ core + thin MQL5 wrapper | Write EA logic in C++ with thin MQL5 wrapper — C++ has mature testing tools | |
| Pure MQL5 + Python mock integration tests | Write EA in MQL5, test via IPC integration with Python mocks — test through file interface | ✓ |
| MQL5 native testing + Python mocks | Use MQL5 Test Framework for EA unit tests, plus Python mocks for integration tests | |

**User's choice:** Pure MQL5 + Python mock integration tests

| Option | Description | Selected |
|--------|-------------|----------|
| IPC integration tests only | Test EA through its file interface — write params files, check if EA reads and acts correctly | ✓ |
| Dependency injection in MQL5 | Wrap core logic in classes with DI — test logic in isolation, mock MT5 API calls | |
| End-to-end demo account tests | Python harness spins up MT5, places orders on demo, validates results | |

**User's choice:** IPC integration tests only

| Option | Description | Selected |
|--------|-------------|----------|
| Mock MT5 data files | Python mock fills data files with sample prices — tests EA → IPC → Python flow without live MT5 | ✓ |
| Mock MT5 server | Write a fake MT5 server that responds to MT5 Python API — comprehensive but significant effort | |
| Python pytest + manual EA testing | Test Python side with pytest/mocks, test EA side manually via MT5 Strategy Tester | |

**User's choice:** Mock MT5 data files

| Option | Description | Selected |
|--------|-------------|----------|
| Automated (pre-push/CI) | Run tests on every commit via pre-push hook or CI — catches regressions early | ✓ |
| Manual script | Run tests manually before deploying changes — works but relies on developer discipline | |
| Hybrid (auto Python, manual EA) | Python tests automated via pytest, EA integration tests manual — matches hybrid architecture | |

**User's choice:** Automated (pre-push/CI)

---

## the Agent's Discretion

- IPC message protocol details (JSON structure, file naming, heartbeat) — user did not select this area for discussion
- Safe default parameter values (SL/TP/sizing) — not discussed in this session
- Error recovery specifics (reconnect behavior, timeout values) — not discussed
- Circuit breaker threshold defaults — not discussed

## Deferred Ideas

None — discussion stayed within phase scope.