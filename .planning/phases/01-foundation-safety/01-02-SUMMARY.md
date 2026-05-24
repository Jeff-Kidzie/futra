---
phase: 01-foundation-safety
plan: 02
subsystem: data-pipeline
tags: [MetaTrader5, pandas, numpy, IPC, file-based-IPC, kill-switch, atomic-write, mock-testing]

# Dependency graph
requires:
  - phase: 01-foundation-safety
    plan: 01
    provides: "IPC contract definition (JSON schemas for kill_switch.json, {SYMBOL}_params.json, ea_state.json, trade_log.jsonl)"
provides:
  - "MT5 connection layer with auto-reconnect and None-handling on all API calls"
  - "Historical and real-time OHLCV data pipeline for multiple symbols/timeframes"
  - "Per-symbol IPC params file writer with atomic write (tmp + os.replace)"
  - "IPC reader for EA state and trade log files"
  - "Kill switch Python script with activate/deactivate and close_positions flag"
  - "Mock MT5 test infrastructure enabling fully local testing without live MT5"
affects: [02-ai-engine, 03-validation, 04-monitoring-dashboard]

# Tech tracking
tech-stack:
  added:
    - "MetaTrader5 (Python package) — MT5 terminal API"
    - "pandas — OHLCV data manipulation"
    - "numpy — numerical operations"
  patterns:
    - "TDD (RED → GREEN) per task with atomic commits"
    - "Mock-based testing: patch MetaTrader5 imports for fully local test suite per D-11"
    - "Atomic file writes: tmp file + os.replace() for IPC files (prevents EA partial reads)"
    - "Safe defaults: config.py provides sensible fallback values from env vars"
    - "Connection resilience: auto-reconnect with max retries (3) and backoff (5s)"

key-files:
  created:
    - "python/__init__.py"
    - "python/config.py" — Central configuration (MT5 paths, symbols, timeframes, IPC dir, retry config)
    - "python/mt5_connector.py" — MT5 connection wrapper with auto-reconnect and None-handling
    - "python/data_pipeline.py" — Historical OHLCV fetch and real-time polling
    - "python/ipc/__init__.py"
    - "python/ipc/ipc_writer.py" — Per-symbol params file writer with atomic write
    - "python/ipc/ipc_reader.py" — EA state and trade log reader
    - "python/kill_switch.py" — Kill switch trigger script
    - "python/tests/__init__.py"
    - "python/tests/conftest.py" — Mock MT5 fixtures (mock_mt5, mock_mt5_with_data, sample_ohlcv_data)
    - "python/tests/test_mt5_connector.py" — 9 connector tests
    - "python/tests/test_data_pipeline.py" — 5 data pipeline tests
    - "python/tests/test_ipc_writer.py" — 8 IPC writer/reader tests
    - "python/tests/test_kill_switch.py" — 9 kill switch tests
  modified: []

key-decisions:
  - "MetaTrader5 package installed for importability; all API calls mocked in tests per D-11"
  - "data_pipeline.py imports MetaTrader5 directly (separate from mt5_connector.py import) — requires both modules to be patched in mock fixtures"
  - "Atomic write pattern (tmp + os.replace) used in both ipc_writer.py and kill_switch.py per T-01-02 threat mitigation"
  - "get_latest_bar() uses DataFrame().iloc[0] instead of Series(rates[0]) for pandas 3.x compatibility"

patterns-established:
  - "TDD per-task: RED (failing tests) → GREEN (minimal implementation) → commit each phase"
  - "Mock patch stacking: conftest fixture uses nested context managers to patch all modules importing MetaTrader5"
  - "Contract-first testing: tests validate JSON file structures match Plan 01-01 IPC schemas exactly"

requirements-completed:
  - DATA-01
  - DATA-02
  - DATA-03
  - DATA-09
  - DATA-10

# Metrics
duration: 15min
completed: 2026-05-24
---

# Phase 1 Plan 2: Data Pipeline Summary

**MT5 Python connection with auto-reconnect resilience, multi-asset OHLCV data pipeline, file-based IPC writer/reader with atomic writes, and kill switch trigger script — all tested locally with mock MT5 (no live connection required)**

## Performance

- **Duration:** ~15 min (includes env setup: pip install MetaTrader5, pandas, numpy)
- **Started:** 2026-05-24T20:06:14+07:00 (first commit)
- **Completed:** 2026-05-24T20:13:57+07:00 (last commit)
- **Tasks:** 2 (both TDD — RED + GREEN per task)
- **Files created:** 14
- **Tests passing:** 31/31

## Accomplishments

- MT5 connection layer with `initialize_mt5()`, `shutdown_mt5()`, `is_connected()`, and `ensure_connected()` — auto-reconnect with 3 retries and 5-second backoff per DATA-10
- None-handling on every MT5 API call: both `mt5.initialize()` and `mt5.terminal_info()` return values are checked; `MT5Error` raised for failures
- Historical OHLCV data via `fetch_historical_ohlcv()` returning pandas DataFrames for any symbol/timeframe combo (M15, H1, H4, D1)
- Per-symbol IPC params files written with atomic pattern (`tmp + os.replace`) to prevent EA from reading partial JSON — matches Plan 01-01 contract exactly
- Kill switch Python script with `activate_kill_switch(close_positions=True/False)` and `deactivate_kill_switch()` — atomic writes to `kill_switch.json`
- IPC reader reads EA state (`ea_state.json`) and trade log (`trade_log.jsonl`) with graceful None/empty returns on missing files
- Centralized `config.py` with all values loadable from environment variables with sensible defaults
- Complete mock MT5 infrastructure — 31 tests pass without live MetaTrader5 terminal

## Task Commits

Each TDD task committed atomically (RED → GREEN):

1. **Task 1 (RED): MT5 connector failing tests** — `db7eca2` (test)
2. **Task 1 (GREEN): MT5 connector and config implementation** — `d064ac4` (feat)
3. **Task 2 (RED): Data pipeline, IPC, kill switch failing tests** — `a659bd6` (test)
4. **Task 2 (GREEN): Data pipeline, IPC, kill switch implementation** — `a913ba2` (feat)

No REFACTOR commits — implementations were clean on first pass.

## Files Created/Modified

- `python/config.py` — Central configuration: MT5 paths, IPC directory, default symbols (EURUSD, GBPUSD, USDJPY), timeframes (M15/H1/H4/D1), polling intervals, retry config
- `python/mt5_connector.py` — MT5 connection wrapper: initialize, shutdown, is_connected, ensure_connected with auto-reconnect, None-handling
- `python/data_pipeline.py` — Historical OHLCV fetch (fetch_historical_ohlcv), latest bar (get_latest_bar), real-time polling loop (start_real_time_polling)
- `python/ipc/ipc_writer.py` — Per-symbol params file writer with atomic write (write_symbol_params)
- `python/ipc/ipc_reader.py` — EA state reader (read_ea_state), trade log reader (read_trade_log)
- `python/kill_switch.py` — Kill switch trigger: activate (with optional close_positions), deactivate
- `python/tests/conftest.py` — Mock fixtures: mock_mt5, mock_mt5_with_data, sample_ohlcv_data, temp_ipc_dir
- `python/tests/test_mt5_connector.py` — 9 tests: initialize, shutdown, is_connected, ensure_connected, config defaults
- `python/tests/test_data_pipeline.py` — 5 tests: historical OHLCV fetch, latest bar, error handling
- `python/tests/test_ipc_writer.py` — 8 tests: params file structure, atomic write, multiple symbols, EA state read, trade log read
- `python/tests/test_kill_switch.py` — 9 tests: activate/deactivate, close_positions flag, atomic write, file location

## Decisions Made

- **Separate MetaTrader5 imports**: `data_pipeline.py` imports `MetaTrader5` directly (for MT5 timeframe constants and `copy_rates_from_pos`), while `mt5_connector.py` has its own import. Mock fixtures must patch both modules.
- **pandas 3.x compatibility**: `pd.Series(numpy_void_record)` loses field names in pandas 3.x — switched to `pd.DataFrame(rates).iloc[0]` in `get_latest_bar()`
- **Mock stacking pattern**: `mock_mt5_with_data` fixture wraps `mock_mt5` with an additional `patch("python.data_pipeline.mt5")` to cover the separate import

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock fixture to patch both mt5 imports**
- **Found during:** Task 2 GREEN phase (data pipeline tests)
- **Issue:** `mock_mt5_with_data` only patched `python.mt5_connector.mt5`, but `data_pipeline.py` imports `MetaTrader5` separately — `copy_rates_from_pos` was being called on the real (unpatched) module, returning `(-10004, 'No IPC connection')`
- **Fix:** Added `with patch("python.data_pipeline.mt5", mock_mt5):` context manager inside `mock_mt5_with_data` fixture to also patch the data pipeline's mt5 reference
- **Files modified:** `python/tests/conftest.py`
- **Verification:** All data pipeline tests pass (5/5)
- **Committed in:** `a913ba2` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] Fixed get_latest_bar() pandas 3.x compatibility**
- **Found during:** Task 2 GREEN phase (data pipeline tests)
- **Issue:** `pd.Series(rates[0])` where `rates[0]` is a numpy void record from `to_records()` — in pandas 3.x, the Series index becomes `[0]` (positional integer) instead of preserving field names like "time", causing `KeyError: 'time'`
- **Fix:** Changed to `pd.DataFrame(rates).iloc[0]` which correctly preserves named fields as the Series index
- **Files modified:** `python/data_pipeline.py` (get_latest_bar function)
- **Verification:** `test_returns_series_with_price_fields` passes with "open", "high", "low", "close" accessible
- **Committed in:** `a913ba2` (Task 2 GREEN commit)

**3. [Rule 3 - Blocking] Installed missing Python dependencies**
- **Found during:** Task 1 RED phase (cannot import MetaTrader5, pandas, numpy)
- **Issue:** `MetaTrader5` Python package not installed — `import MetaTrader5 as mt5` fails at module import time even though all API calls are mocked. `pandas` and `numpy` needed for test data fixtures.
- **Fix:** `pip install MetaTrader5 pandas numpy`
- **Verification:** All imports succeed, 31 tests pass
- **Committed in:** N/A (environment setup, not committed to repo)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for test correctness and pandas 3.x compatibility. No scope creep.

## Issues Encountered

- **pandas 3.0.3 behavior change**: `pd.Series()` on a numpy structured void record no longer preserves field names as the index (unlike previous pandas versions). Resolved by using `pd.DataFrame(rates).iloc[0]` instead — functionally equivalent, more explicit.
- **MetaTrader5 package import**: Even for mock-based testing, the `MetaTrader5` package must be pip-installed because Python modules import it at the top level. The package is importable without a running MT5 terminal (only API calls fail, which we mock).

## Threat Mitigations Verified

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-01-02 (Tampering) | Atomic write: `.tmp` + `os.replace()` in ipc_writer.py and kill_switch.py | Verified — no `.tmp` files remain after any operation |
| T-01-07 (Information Disclosure) | MT5 credentials via env vars (`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`), never hardcoded | Verified — config.py uses `os.getenv()` with safe defaults |
| T-01-08 (Denial of Service) | Auto-reconnect with max retries (3) and backoff (5s), None-handling on all API calls | Verified — tests cover reconnect exhaustion and None returns |

## User Setup Required

None — no external service configuration required. All components testable locally. For production:
- Set `MT5_PATH`, `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` environment variables
- Set `FUTRA_IPC_DIR` to match EA's IPC directory (defaults to `{project_root}/ipc/` in dev, `{MT5_DATA}/MQL5/Files/Futra/` in production)

## Next Phase Readiness

- Python data pipeline fully operational with mock testing — ready for Phase 2 (AI Engine) which will consume OHLCV data
- IPC contract compliance verified — EA (Plan 01-01) and Python (Plan 01-02) agree on JSON schemas
- Kill switch script ready for remote triggering (SSH, scheduled task)
- All 31 tests pass — CI-ready for pre-push hooks per D-12
- Next plan: 01-03 (Risk controls: circuit breakers, position sizing validation)

## Self-Check: PASSED

- All 11 key files verified on disk: 11/11 FOUND
- All 4 plan commits verified in git log: `db7eca2`, `d064ac4`, `a659bd6`, `a913ba2`
- Full test suite: 31/31 PASSED (`python -m pytest python/tests/ -v`)
- No `.tmp` files left behind (atomic write verified)
- Config loads with sensible defaults (env var fallback working)

---
*Phase: 01-foundation-safety*
*Completed: 2026-05-24*
