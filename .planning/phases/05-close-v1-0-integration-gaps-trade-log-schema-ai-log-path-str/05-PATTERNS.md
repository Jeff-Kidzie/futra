# Phase 5: Close v1.0 integration gaps — Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 21 (5 modified config/producer, 4 modified consumer, 4 modified existing tests, 4 new integration tests, 3 MQL5 producer, 1 NEW production entry, 1 .env.example)
**Analogs found:** 21 / 21 — every new/modified file has at least one in-tree analog. No greenfield patterns required.

The whole phase is contract reconciliation: every fix is "make file A obey the convention that file B already established." The analog table below is therefore directional — each modified file's analog is *the file across the contract boundary that the modification must conform to*.

## File Classification

| New/Modified File | Wave | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `python/config.py` (G3 + G4) | A | config | constant declaration | `python/config.py:18` (`IPC_DIR`) | exact (same file, mirror the pattern from `IPC_DIR` to `AI_LOG_DIR`/`STRATEGY_CONFIG_DIR`) |
| `.env.example` (G6 optional) | A | config | env-var documentation | `.env.example:38-42` (existing `FUTRA_AI_LOG_DIR` block) | exact |
| `ea/include/Logger.mqh` (G1) | B1 | producer (MQL5) | file-I/O, append-only JSONL | self — `Logger.mqh:27-56` existing `LogTrade()` is the structural analog; only the format string and signature change | exact (same file) |
| `ea/include/OrderManager.mqh` (G1 call-site) | B1 | producer call-site (MQL5) | request-response | `OrderManager.mqh:113-114` and `:189-190` — replace `LogTrade(tradeResult)` with `LogTradeOpen(tradeResult)` | exact (same file) |
| `ea/include/PositionManager.mqh` (G1 call-site + ticket fix) | B1 | producer call-site (MQL5) | request-response | `PositionManager.mqh:69-82` (close), `:153-166` (modify) — same `TradeResult logEntry` pattern; fix `logEntry.ticket = result.order` → `ticket` | exact (same file) |
| `python/ai/decision_logger.py` (G2 + timeframe sub-gap) | B2 | producer (Python) | event-driven JSONL append | `python/ipc/ipc_writer.py:17-49` (single-file path constant via config import), self for `log_decision()` body | role-match (path) + exact (logging body) |
| `python/ai/engine.py` (G5 default-on + G2 timeframe pass-through) | B2 | service orchestrator | event-driven | `python/ai/engine.py:35-36` (existing `self.detector = regime_detector or RegimeDetector()` default-on pattern) — mirror for logger | exact (same file) |
| `python/ai/strategy_manager.py` (G4 import rename) | B3 | producer (Python) | file-I/O, JSON | self — import line update only; rest of file unchanged | exact (mechanical rename) |
| `python/dashboard/api/equity.py` (G7 optional — FUTRA_INITIAL_BALANCE wiring) | B4 | consumer (FastAPI route) | request-response, file read | `python/dashboard/api/trades.py:8, 12` (config import + module-level constant pattern) | exact (sibling file) |
| `python/ai/__main__.py` (G5 part 2, optional) | B2 | NEW production entry point | event-loop service | `python/validation/paper_trading.py:1-50` (engine-receiving service loop) | role-match |
| `python/tests/ai/test_decision_logger.py` (G2 fixture updates) | C | test (unit, AI) | n/a | self — existing tests; add `timeframe="H1"` arg to every `log_decision(...)` call | exact (same file) |
| `python/tests/ai/test_engine.py` (G5 default-on test updates) | C | test (unit, AI) | n/a | `python/tests/ai/test_engine.py:177-199` (existing `test_engine_works_without_logger` + `test_existing_engine_tests_still_pass`) | exact (same file, invert assertions) |
| `python/tests/ai/test_parameter_adapter.py` (BL-01 regression) | C | test (unit, AI) | n/a | `.planning/phases/02-ai-engine/02-REVIEW.md:60-69` (proof-of-concept) + sibling `test_parameter_adapter.py` style | role-match |
| `python/tests/ai/test_strategy_manager.py` (BL-01 cross-contam regression) | C | test (unit, AI) | n/a | `python/tests/ai/test_strategy_manager.py:124-135` (`test_apply_strategy_modifies_instances`) — clone shape | exact (same file) |
| `python/tests/dashboard/test_trades.py` (G1 fixture reshape) | C | test (API, dashboard) | request-response | `python/tests/dashboard/test_trades.py:30-54` (existing — replace fabricated fixtures with `Logger.mqh`-format-derived ones) | exact (same file, swap fixture source) |
| `python/tests/dashboard/test_decisions.py` (G2 fixture update) | C | test (API, dashboard) | request-response | `python/tests/dashboard/test_decisions.py:28-44` — fixtures already match new schema, just verify | exact (same file) |
| `python/tests/dashboard/test_equity.py` (G1 fixture reshape) | C | test (API, dashboard) | request-response | `python/tests/dashboard/test_equity.py:29-46` — reshape inline fixtures | exact (same file) |
| `python/tests/integration/__init__.py` (NEW) | C | test bootstrap | n/a | empty file pattern from sibling `python/tests/ai/__init__.py` (if present) | role-match |
| `python/tests/integration/test_trade_log_contract.py` (NEW, G1) | C | test (integration) | producer→consumer round-trip | `python/tests/dashboard/test_trades.py:30-54` (assertion structure) + `python/tests/dashboard/conftest.py:46-69` (TestClient + auth_headers) | role-match |
| `python/tests/integration/test_decision_log_contract.py` (NEW, G2 + G5) | C | test (integration) | producer→consumer round-trip | `python/tests/ai/test_decision_logger.py:25-36` (JSONL round-trip) + `python/dashboard/api/decisions.py:16-42` (reader entrypoint) | role-match |
| `python/tests/integration/test_strategy_contract.py` (NEW, G4) | C | test (integration) | producer→consumer round-trip | `python/tests/ai/test_strategy_manager.py:79-87` (round-trip) + `python/dashboard/api/strategy.py:14-29` (reader entrypoint) | role-match |
| `python/tests/integration/test_config_no_duplicates.py` (NEW, G3 + G4) | C | test (regression guard) | n/a | mechanical grep — no analog (new test category, but trivial) | no analog (mechanical) |

## Shared Conventions (apply across all relevant plans)

These are the **cross-cutting contract anchors** the planner should reference repeatedly. Surface these in every plan so the executor cannot accidentally diverge from them.

### S1. Project-root-relative path constant (IPC_DIR pattern)

**Source of truth:** `python/config.py:18`

```python
# IPC Directory (local dev default, overridden in production)
IPC_DIR = Path(os.getenv("FUTRA_IPC_DIR", str(Path(__file__).parent.parent / "ipc")))
```

**Why it's the anchor:** `Path(__file__).parent.parent` resolves to `<repo>/` regardless of CWD. This eliminates the CWD-divergence bug that line 109 (`Path("logs/ai")`) and line 110 (`Path("configs/strategies")`) introduce — those defaults silently differ when the AI engine launches from `python/` versus the dashboard launching from `<repo>/`.

**Apply to:**
- `AI_LOG_DIR` (G3 fix)
- `STRATEGY_CONFIG_DIR` (G4 fix)
- Any future config constant in `python/config.py`

**Mechanical rewrite template:**
```python
AI_LOG_DIR = Path(os.getenv(
    "FUTRA_AI_LOG_DIR",
    str(Path(__file__).parent.parent / "logs" / "ai"),
))

STRATEGY_CONFIG_DIR = Path(os.getenv(
    "FUTRA_STRATEGY_CONFIG_DIR",
    str(Path(__file__).parent.parent / "configs" / "strategies"),
))
```

**Regression test (mechanical guard):**
```python
# python/tests/integration/test_config_no_duplicates.py
def test_ai_log_dir_defined_once():
    src = Path("python/config.py").read_text()
    assert src.count("AI_LOG_DIR =") == 1
    assert "AI_STRATEGY_DIR" not in src  # G4 collapses this
```

### S2. JSONL append-write idiom (Python producer)

**Source of truth:** `python/ai/decision_logger.py:144-150`

```python
log_path = self._get_log_path()
try:
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    logger.debug(f"Logged AI decision: {symbol} {regime}")
except OSError as e:
    logger.error(f"Failed to write decision log: {e}")
```

**Why it's the anchor:** This is the canonical Python-side JSONL write — `"a"` open, single `json.dumps + "\n"` per record, `OSError` caught and logged (not raised) so the producer never crashes the engine loop.

**Apply to:**
- DecisionLogger after G2 single-file rewrite (same pattern, `self.log_path` becomes constant)
- Any new JSONL emitter (none planned in Phase 5, but worth locking)

### S3. JSONL append-write idiom (MQL5 producer)

**Source of truth:** `ea/include/Logger.mqh:40-55`

```mql5
// TRADE_LOG_FILE already includes "Futra/" prefix
ResetLastError();
int handle = FileOpen(TRADE_LOG_FILE, FILE_TXT|FILE_READ|FILE_WRITE|FILE_SHARE_READ);

if(handle == INVALID_HANDLE)
{
   Print("LogTrade: FileOpen failed for ", TRADE_LOG_FILE,
         ", error: ", GetLastError(),
         " | Trade: ticket=", result.ticket,
         ", retcode=", result.retcode);
   return;
}

// Seek to end for append
FileSeek(handle, 0, SEEK_END);
FileWrite(handle, jsonLine);
FileClose(handle);
```

**Why it's the anchor:** The file-open / seek-end / write / close sequence with `FILE_SHARE_READ` is the established MQL5 producer pattern. `INVALID_HANDLE` falls back to `Print()` (non-crashing). All new `LogTradeOpen`/`LogTradeClose`/`LogTradeModify` functions must reuse this body verbatim — only the `jsonLine` `StringFormat` block changes.

**Apply to:**
- All new event-specific logger functions in `Logger.mqh` (G1)

### S4. JSONL line-reader idiom (Python consumer)

**Source of truth:** `python/dashboard/api/trades.py:24-34` (and identical at `decisions.py:22-32`, `equity.py:31-39`)

```python
try:
    with open(TRADE_LOG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Malformed JSON line in trade_log.jsonl, skipping")
                continue
            # ... entry.get("event") dispatch ...
except Exception as e:
    logger.error("Error reading trade log: %s", e)
    return []
```

**Why it's the anchor:** Skip-on-malformed is established. `entry.get("event")` (never `entry["event"]`) is the established dispatch — silent skip when the field is absent. After G1, the EA emits the `event` field, so the existing reader code does not need to change — but the test fixtures must produce the EA-shaped strings.

**Apply to:**
- No new readers in Phase 5, but the contract test (`test_trade_log_contract.py`) must assert that an EA-format line, parsed via this exact code path, yields a populated `read_trades()` result.

### S5. Pydantic response model symmetry (writer record ⟷ reader model)

**Source of truth:** `python/dashboard/models.py:51-60` (`Decision`)

```python
class Decision(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str      # REQUIRED — DecisionLogger must emit this (G2 sub-gap)
    regime: str
    confidence: float
    sl_pips: float
    tp_pips: float
    lot_size: float
    reasoning: str
```

**Why it's the anchor:** Every required field in this model **must** appear in the JSONL record the writer emits. The current `decision_logger.py:130-142` record omits `timeframe` — production reads will Pydantic-500. The G2 fix must add `timeframe` to the writer record AND propagate `timeframe=self.timeframe` from `engine.py:91-103` into `log_decision(...)`.

**Apply to:**
- `decision_logger.py` (G2): add `timeframe: str` parameter (required, no default), add `"timeframe": timeframe` to the record dict
- `engine.py` (G2 + G5 merged): pass `timeframe=self.timeframe` into `self.decision_logger.log_decision(...)`
- Integration test (G2): round-trip `Decision(**entry)` over every line of writer output

**Equivalent contract for Trade:** `python/dashboard/models.py:38-48` is the target shape for G1. `trades.py:54-65` builds the row from EA-derived fields; the EA emission must supply every `entry.get(...)` key referenced there (`event`, `ticket`, `symbol`, `direction`, `price`, `close_price`, `profit`, `timestamp`).

### S6. Default-on dependency injection (engine constructor)

**Source of truth:** `python/ai/engine.py:35-36`

```python
self.detector = regime_detector or RegimeDetector()
self.adapter = parameter_adapter or ParameterAdapter()
```

**Why it's the anchor:** `regime_detector` and `parameter_adapter` are default-on — pass `None` (or omit) → constructor instantiates the default. The current `decision_logger` parameter inverts this: `None` → disabled. G5 must align it with the established pattern.

**Recommended G5 form** (preserves explicit-disable via a kwarg, per RESEARCH.md §G5):
```python
def __init__(
    self,
    ...,
    decision_logger: DecisionLogger | None = None,
    enable_decision_log: bool = True,    # NEW
):
    self.detector = regime_detector or RegimeDetector()
    self.adapter = parameter_adapter or ParameterAdapter()
    if decision_logger is None and enable_decision_log:
        decision_logger = DecisionLogger()    # default-on, mirrors S6
    self.decision_logger = decision_logger
```

### S7. Test fixture patching idiom (consumer-side endpoint tests)

**Source of truth:** `python/tests/dashboard/test_trades.py:8-17`

```python
@pytest.fixture
def temp_trade_log(tmp_path, monkeypatch):
    """Create a temporary trade_log.jsonl with known test data."""
    log_path = tmp_path / "Futra" / "trade_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "python.dashboard.api.trades.TRADE_LOG_PATH",
        log_path,
    )
    return log_path
```

**Why it's the anchor:** Endpoint tests patch the **module-level path constant** (not the config import) and write fixtures into a `tmp_path`-rooted file. After G1, the contents of these fixtures change (from fabricated `{"event":...}` dicts to EA-format strings), but the patching mechanism stays identical.

**Apply to:**
- `test_trades.py` G1 reshape: keep fixture, swap entry-source
- `test_equity.py` G1 reshape: keep fixture, swap entry-source
- `test_decisions.py` G2: already matches; verify no changes needed
- New `test_*_contract.py` files: reuse the `monkeypatch.setattr` pattern for `DECISION_LOG_PATH`, `TRADE_LOG_PATH`, `STRATEGY_CONFIG_DIR`

### S8. Instance-level mutable-state shadowing (BL-01)

**Source of truth:** `python/ai/parameter_adapter.py:54-56`

```python
self.SL_MULTIPLIERS = dict(self.__class__.SL_MULTIPLIERS)
self.TP_MULTIPLIERS = dict(self.__class__.TP_MULTIPLIERS)
self.LOT_MULTIPLIERS = dict(self.__class__.LOT_MULTIPLIERS)
```

**Why it's the anchor:** The fix exists (commit `2dfd5e1`) but has no regression test. The new test must assert that mutating `a1.SL_MULTIPLIERS` does **not** mutate `a2.SL_MULTIPLIERS` or `ParameterAdapter.SL_MULTIPLIERS`.

**Apply to:**
- `test_parameter_adapter.py` new test (the BL-01 regression)
- `test_strategy_manager.py` new test (cross-contamination via `apply_strategy`)

## Pattern Assignments

---

### `python/config.py` (Wave A: G3 + G4) — config, constant declaration

**Analog:** Self — line 18 (`IPC_DIR`)

**Imports pattern (already in place, no change):**
```python
# python/config.py:1-8
import os
import secrets
from pathlib import Path
```

**Canonical project-root-relative constant pattern** (mirror from `IPC_DIR` line 18):
```python
# python/config.py:18 — DO NOT CHANGE — this is the pattern to clone
IPC_DIR = Path(os.getenv("FUTRA_IPC_DIR", str(Path(__file__).parent.parent / "ipc")))
```

**Required Wave A edits:**

1. **Replace line 47** (old `AI_LOG_DIR` with `python/ai/decisions` default) with the canonical pattern:
   ```python
   AI_LOG_DIR = Path(os.getenv(
       "FUTRA_AI_LOG_DIR",
       str(Path(__file__).parent.parent / "logs" / "ai"),
   ))
   ```
   This both fixes the CWD-relative default AND becomes the single definition.

2. **Replace line 48** (old `AI_STRATEGY_DIR`) — DELETE the line entirely.

3. **Replace line 109** (old duplicate `AI_LOG_DIR`) — DELETE entirely.

4. **Replace line 110** (old `STRATEGY_CONFIG_DIR` with CWD-relative default) — DELETE and move to consolidated block near line 48:
   ```python
   STRATEGY_CONFIG_DIR = Path(os.getenv(
       "FUTRA_STRATEGY_CONFIG_DIR",
       str(Path(__file__).parent.parent / "configs" / "strategies"),
   ))
   ```

**Cross-cutting:** Apply S1 (project-root-relative pattern).

**Verification:**
- Smoke-test import: `python -c "from python.config import AI_LOG_DIR, STRATEGY_CONFIG_DIR; print(AI_LOG_DIR.resolve(), STRATEGY_CONFIG_DIR.resolve())"`
- Resolved paths must end in `\logs\ai` and `\configs\strategies` regardless of CWD.

---

### `.env.example` (Wave A optional: G6) — env-var documentation

**Analog:** Self — lines 38-42 (existing AI Engine block)

**Existing pattern:**
```ini
# --- AI Engine (Phase 2) ---
# Directory for AI decision logs
FUTRA_AI_LOG_DIR=logs/ai
# Directory for strategy configuration exports
FUTRA_STRATEGY_CONFIG_DIR=configs/strategies
```

**G6 addition (recommended, 4 lines):**
```ini
# --- Paper Trading (Phase 3) ---
# Demo account credentials for paper trading (separate from live MT5_LOGIN above)
MT5_DEMO_LOGIN=12345678
MT5_DEMO_PASSWORD=your_demo_password
MT5_DEMO_SERVER=YourBroker-Demo
```

**No changes needed to existing `FUTRA_AI_LOG_DIR` or `FUTRA_STRATEGY_CONFIG_DIR` lines** — the values `logs/ai` and `configs/strategies` continue to work with the new project-root-relative defaults.

---

### `ea/include/Logger.mqh` (Wave B1: G1 producer) — producer (MQL5), file-I/O, append-only JSONL

**Analog:** Self — `LogTrade()` at lines 27-56; reuse the format-string + FileOpen body verbatim, only change the `jsonLine` `StringFormat` per event type.

**Imports / preamble pattern** (lines 1-7, unchanged):
```mql5
#property strict
#include "Common.mqh"
```

**Core JSON-build pattern to mirror** (lines 27-37):
```mql5
void LogTrade(TradeResult &result)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\","
      "\"volume\":%.2f,\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,"
      "\"retcode\":%d,\"comment\":\"%s\",\"timestamp\":\"%s\"}",
      result.ticket, result.symbol, result.type,
      result.volume, result.price, result.sl, result.tp,
      result.retcode, result.comment, timestamp
   );
   // ... FileOpen / FileSeek / FileWrite / FileClose (S3) ...
}
```

**Required emissions after G1** (three new functions; reuse S3 FileOpen body for all):

```mql5
void LogTradeOpen(TradeResult &result)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"event\":\"trade_open\",\"ticket\":%I64u,\"symbol\":\"%s\","
      "\"direction\":\"%s\",\"volume\":%.2f,\"price\":%.5f,"
      "\"sl\":%.5f,\"tp\":%.5f,\"retcode\":%d,"
      "\"comment\":\"%s\",\"timestamp\":\"%s\"}",
      result.ticket, result.symbol, result.type,
      result.volume, result.price, result.sl, result.tp,
      result.retcode, result.comment, timestamp
   );
   // ... reuse S3 FileOpen body ...
}

void LogTradeClose(TradeResult &result, double profit)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"event\":\"trade_close\",\"ticket\":%I64u,\"symbol\":\"%s\","
      "\"direction\":\"%s\",\"volume\":%.2f,\"close_price\":%.5f,"
      "\"profit\":%.2f,\"retcode\":%d,\"comment\":\"%s\","
      "\"timestamp\":\"%s\"}",
      result.ticket, result.symbol, result.type,
      result.volume, result.price, profit,
      result.retcode, result.comment, timestamp
   );
   // ... reuse S3 FileOpen body ...
}

void LogTradeModify(ulong ticket, double sl, double tp, int retcode)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"event\":\"trade_modify\",\"ticket\":%I64u,"
      "\"sl\":%.5f,\"tp\":%.5f,\"retcode\":%d,\"timestamp\":\"%s\"}",
      ticket, sl, tp, retcode, timestamp
   );
   // ... reuse S3 FileOpen body ...
}
```

**Existing `LogTrade()` (lines 27-56), `LogError()` (lines 61-85), `LogInfo()` (lines 90-113):**
- `LogTrade()` — remove (no remaining callers after `OrderManager` + `PositionManager` updates) OR keep as a back-compat shim that delegates to `LogTradeOpen`. Recommend remove.
- `LogError()` — optionally add `"event":"error"` field for filter symmetry (Open Question 2 in RESEARCH.md). Zero functional cost.
- `LogInfo()` — leave unchanged; not consumed by dashboard.

**Cross-cutting:** Apply S3 (MQL5 JSONL append-write idiom — reuse the existing `LogTrade()` body for every new function).

---

### `ea/include/OrderManager.mqh` (Wave B1: G1 call-site) — producer call-site (MQL5)

**Analog:** Self — lines 113-114 and 189-190 (the two existing `LogTrade(tradeResult)` calls)

**Existing pattern** (line 113-114, identical at 189-190):
```mql5
// Log every trade result (per DATA-08)
LogTrade(tradeResult);
```

**Required edits:**
- Line 114 (in `OpenBuyOrder`): `LogTrade(tradeResult);` → `LogTradeOpen(tradeResult);`
- Line 190 (in `OpenSellOrder`): `LogTrade(tradeResult);` → `LogTradeOpen(tradeResult);`

**No structural changes** — `tradeResult` is already populated correctly; the type field (`"buy"`/`"sell"`) is the new `direction` value.

---

### `ea/include/PositionManager.mqh` (Wave B1: G1 call-site + ticket fix) — producer call-site (MQL5)

**Analog:** Self — lines 69-82 (close) and 153-166 (modify)

**Existing close-side pattern** (lines 69-82):
```mql5
// Log the close as a trade result
TradeResult logEntry;
ZeroMemory(logEntry);
logEntry.ticket    = result.order;    // BUG — should be position ticket
logEntry.symbol    = symbol;
logEntry.type      = (posType == POSITION_TYPE_BUY) ? "sell" : "buy";   // BUG — should be the position's direction
logEntry.volume    = volume;
logEntry.price     = result.price;
logEntry.sl        = 0;
logEntry.tp        = 0;
logEntry.retcode   = result.retcode;
logEntry.comment   = "Position closed";
logEntry.timestamp = TimeCurrent();
LogTrade(logEntry);
```

**Required fix** (per RESEARCH.md G1 risks + Pitfall 4):

1. **Capture `profit` BEFORE `OrderSend`** — add at line 24 (after `PositionSelectByTicket(ticket)` succeeds):
   ```mql5
   double profitAtClose = PositionGetDouble(POSITION_PROFIT);
   ```

2. **Replace lines 69-82** with corrected ticket + direction + call:
   ```mql5
   // Log the close as a trade result
   TradeResult logEntry;
   ZeroMemory(logEntry);
   logEntry.ticket    = ticket;                                                   // FIX: position ticket, not result.order
   logEntry.symbol    = symbol;
   logEntry.type      = (posType == POSITION_TYPE_BUY) ? "buy" : "sell";          // FIX: position's direction, not closing order's
   logEntry.volume    = volume;
   logEntry.price     = result.price;
   logEntry.sl        = 0;
   logEntry.tp        = 0;
   logEntry.retcode   = result.retcode;
   logEntry.comment   = "Position closed";
   logEntry.timestamp = TimeCurrent();
   LogTradeClose(logEntry, profitAtClose);
   ```

3. **Replace `LogTrade(logEntry);` at line 166** (modify call site) with:
   ```mql5
   LogTradeModify(ticket, newSL, newTP, result.retcode);
   ```
   And remove the now-unused `TradeResult logEntry` block at lines 153-165.

**Why both fixes matter:** `trades.py:37-40` joins open↔close by `ticket`. If the close emits `result.order` (closing-order ticket) while the open emitted the position ticket, the join fails silently. Open trades will stay "open" forever in the dashboard.

---

### `python/ai/decision_logger.py` (Wave B2: G2 single-file + timeframe) — producer (Python), event-driven JSONL append

**Analog:**
- For the path constant: `python/dashboard/api/trades.py:12` (`TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"`)
- For the write body: self — lines 144-150 (already canonical)

**Imports (line 11, unchanged):**
```python
from ..config import AI_LOG_DIR
```

**Constant-path pattern to mirror from `trades.py:12`:**
```python
# python/dashboard/api/trades.py:12 — single canonical path
TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"
```

**Required G2 edits to `decision_logger.py`:**

1. **Replace `__init__` (lines 23-27)** to set a constant single-file path:
   ```python
   def __init__(self, log_dir: Path | None = None):
       self.log_dir = log_dir or AI_LOG_DIR
       self.log_dir.mkdir(parents=True, exist_ok=True)
       self.log_path = self.log_dir / "decision_log.jsonl"     # NEW — constant
       # DELETED: self._current_date = None
       # DELETED: self._file_path = None
   ```

2. **Delete `_get_log_path()` entirely** (lines 29-35).

3. **Update `log_decision()` signature (lines 81-92)** — add required `timeframe` param:
   ```python
   def log_decision(
       self,
       symbol: str,
       timeframe: str,         # NEW — required, no default (loud failure on misuse)
       regime: str,
       confidence: float,
       sl_pips: float,
       tp_pips: float,
       lot_size: float,
       volatility: float | None = None,
       atr: float | None = None,
       features: dict[str, float] | None = None,
   ) -> Path:
   ```

4. **Update record dict (lines 130-142)** — add `timeframe`:
   ```python
   record = {
       "timestamp": timestamp,
       "symbol": symbol,
       "timeframe": timeframe,        # NEW
       "regime": regime,
       "confidence": round(confidence, 4),
       "sl_pips": round(sl_pips, 1),
       "tp_pips": round(tp_pips, 1),
       "lot_size": round(lot_size, 2),
       "volatility": round(volatility, 4) if volatility is not None else None,
       "atr": round(atr, 1) if atr is not None else None,
       "features_snapshot": features_snapshot,
       "reasoning": reasoning,
   }
   ```

5. **Update write block (line 144)** — use `self.log_path` instead of `self._get_log_path()`:
   ```python
   try:
       with open(self.log_path, "a") as f:
           f.write(json.dumps(record) + "\n")
       logger.debug(f"Logged AI decision: {symbol} {regime}")
   except OSError as e:
       logger.error(f"Failed to write decision log: {e}")
   return self.log_path
   ```

**Cross-cutting:** Apply S2 (JSONL append-write idiom — preserved), S5 (Pydantic symmetry — timeframe required to match `Decision` model).

---

### `python/ai/engine.py` (Wave B2: G5 default-on + G2 timeframe pass-through) — service orchestrator

**Analog:** Self — lines 35-36 (existing `regime_detector or RegimeDetector()` default-on pattern)

**Existing default-on pattern to mirror (lines 35-36):**
```python
self.detector = regime_detector or RegimeDetector()
self.adapter = parameter_adapter or ParameterAdapter()
```

**Required G5 edits to `__init__` (lines 25-38):**
```python
def __init__(
    self,
    symbols: list[str] | None = None,
    timeframe: str = AI_DEFAULT_TIMEFRAME,
    regime_detector: RegimeDetector | None = None,
    parameter_adapter: ParameterAdapter | None = None,
    decision_logger: DecisionLogger | None = None,
    enable_decision_log: bool = True,      # NEW — explicit disable via False
):
    self.symbols = symbols or DEFAULT_SYMBOLS
    self.timeframe = timeframe
    self.detector = regime_detector or RegimeDetector()
    self.adapter = parameter_adapter or ParameterAdapter()
    if decision_logger is None and enable_decision_log:
        decision_logger = DecisionLogger()    # default-on (mirrors S6)
    self.decision_logger = decision_logger
    self.logger = logging.getLogger(__name__)
```

**Required G2 edit to `evaluate_symbol` (lines 91-103):**
```python
# 7. Log AI decision (per AI-04)
if self.decision_logger is not None:
    try:
        self.decision_logger.log_decision(
            symbol=symbol,
            timeframe=self.timeframe,    # NEW — propagate timeframe
            regime=regime,
            confidence=confidence,
            sl_pips=adapted["sl_pips"],
            tp_pips=adapted["tp_pips"],
            lot_size=adapted["lot_size"],
            volatility=volatility,
            atr=atr_pips,
            features=features,
        )
    except Exception as e:
        self.logger.warning(f"Failed to log decision for {symbol}: {e}")
```

**Cross-cutting:** Apply S5 (timeframe propagation), S6 (default-on DI pattern).

---

### `python/ai/strategy_manager.py` (Wave B3: G4 import rename) — producer (Python), file-I/O

**Analog:** Self — only the import line and one constructor line change

**Existing pattern (line 9):**
```python
from ..config import AI_STRATEGY_DIR
```

**Existing constructor (line 32):**
```python
self.strategy_dir = strategy_dir or AI_STRATEGY_DIR
```

**Required edits:**
1. Line 9: `from ..config import AI_STRATEGY_DIR` → `from ..config import STRATEGY_CONFIG_DIR`
2. Line 32: `self.strategy_dir = strategy_dir or AI_STRATEGY_DIR` → `self.strategy_dir = strategy_dir or STRATEGY_CONFIG_DIR`

**Nothing else changes.** All other code in this file (export_strategy, import_strategy, apply_strategy, including the `adapter.SL_MULTIPLIERS.update(...)` calls at lines 155-160 that are now safe due to the BL-01 fix in `parameter_adapter.py:54-56`) remains as-is.

---

### `python/dashboard/api/equity.py` (Wave B4 optional: G7 — FUTRA_INITIAL_BALANCE wiring) — consumer (FastAPI route)

**Analog:** Sibling `python/dashboard/api/trades.py:1-13` (same module structure, same import style)

**Imports pattern to mirror (`trades.py:1-13`):**
```python
"""GET /api/trades — paginated trade history from trade_log.jsonl."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from ..auth import require_auth
from ..models import Trade
from ...config import IPC_DIR

logger = logging.getLogger(__name__)

TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"
router = APIRouter(prefix="/api/trades", tags=["trades"])
```

**Required edits to `equity.py`:**

1. **Update imports (line 9)** to also pull the balance constant:
   ```python
   from ...config import IPC_DIR, FUTRA_INITIAL_BALANCE
   ```

2. **Update `compute_equity_curve` signature (line 17-21)** to default to the config value instead of hardcoded:
   ```python
   def compute_equity_curve(
       trade_log_path: Path | None = None,
       initial_balance: float | None = None,
       days: int = 30,
   ) -> list[dict]:
       """Replay trades from JSONL log to build daily equity curve."""
       if initial_balance is None:
           initial_balance = FUTRA_INITIAL_BALANCE
       ...
   ```

3. **Update endpoint call (line 99)** to pass the config-derived value through (or leave as-is since the default now resolves correctly):
   ```python
   curve = compute_equity_curve(days=days)    # initial_balance defaults via config
   ```

**Existing tests at `test_equity.py`** that pass `initial_balance=10000.0` explicitly still work — the parameter is now Optional, not removed.

---

### `python/ai/__main__.py` (Wave B2 optional: G5 part 2 production entry) — NEW production entry point

**Analog:** `python/validation/paper_trading.py:1-50` (engine-receiving service loop pattern)

**File doesn't exist yet — entire content is NEW.**

**Imports + body pattern to mirror from `paper_trading.py`** (existing service-loop convention):
```python
"""Production entry point: run the AI engine loop with decision logging on (G5)."""
import logging
import time

from .engine import AIEngine
from ..config import PAPER_TRADING_INTERVAL_SECONDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("python.ai")


def main() -> None:
    """Run the AI engine evaluation loop until interrupted."""
    engine = AIEngine()   # default-on logger (S6 + G5)
    logger.info(
        "AIEngine started: symbols=%s timeframe=%s",
        engine.symbols,
        engine.timeframe,
    )
    while True:
        try:
            engine.run_once()
        except KeyboardInterrupt:
            logger.info("AIEngine stopped by user")
            return
        except Exception as e:
            logger.error("AIEngine loop error: %s", e, exc_info=True)
        time.sleep(PAPER_TRADING_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
```

**Run with:** `python -m python.ai`

**Cross-cutting:** Apply S6 (default-on DI — `AIEngine()` constructor now wires `DecisionLogger()` automatically thanks to G5).

---

### `python/tests/ai/test_decision_logger.py` (Wave C: G2 fixture updates) — test (unit, AI)

**Analog:** Self — existing test file; mechanical edits only

**Existing pattern (lines 20, 27, 41, 51-54, 67-68, 92-93, 107):**
```python
logger.log_decision("EURUSD", "trending", 0.85, 50.0, 100.0, 0.01)
```

**Required edits:** add `"H1"` (timeframe) as the second positional argument to **every** `log_decision(...)` call:
```python
logger.log_decision("EURUSD", "H1", "trending", 0.85, 50.0, 100.0, 0.01)
```

**Update the required-keys set (line 32-35)** to include `timeframe`:
```python
required = {
    "timestamp", "symbol", "timeframe", "regime", "confidence", "sl_pips",
    "tp_pips", "lot_size", "volatility", "features_snapshot", "reasoning",
}
```

**Test 1 (`test_log_decision_creates_file`, lines 16-22):** the glob `*.jsonl` assertion still works (single file `decision_log.jsonl` is `*.jsonl`); no change beyond the `log_decision` arg.

---

### `python/tests/ai/test_engine.py` (Wave C: G5 default-on test updates) — test (unit, AI)

**Analog:** Self — lines 177-199

**Existing patterns to update:**

**Lines 177-189 (`test_engine_works_without_logger`):**
```python
def test_engine_works_without_logger():
    """Test 7: Engine does not crash when decision_logger is None."""
    engine = AIEngine(symbols=["EURUSD"], decision_logger=None)
    ...
```

**Required edit** — preserve "no log" semantics via `enable_decision_log=False`:
```python
def test_engine_works_without_logger():
    """Test 7: Engine does not crash when decision logging is explicitly disabled."""
    engine = AIEngine(symbols=["EURUSD"], enable_decision_log=False)
    assert engine.decision_logger is None
    ...
```

**Lines 192-199 (`test_existing_engine_tests_still_pass`):**
```python
def test_existing_engine_tests_still_pass():
    engine = AIEngine(symbols=["EURUSD"])
    ...
    assert engine.decision_logger is None     # CURRENT — inverts under G5
```

**Required edit** — assertion inverts (default-on):
```python
def test_existing_engine_tests_still_pass():
    """Test 8: Default-on logger wired automatically (G5)."""
    from python.ai.decision_logger import DecisionLogger
    engine = AIEngine(symbols=["EURUSD"])
    assert engine.symbols == ["EURUSD"]
    assert engine.timeframe == "H1"
    assert engine.detector is not None
    assert engine.adapter is not None
    assert isinstance(engine.decision_logger, DecisionLogger)
```

**Cross-cutting:** Apply S6.

---

### `python/tests/ai/test_parameter_adapter.py` (Wave C: BL-01 regression) — test (unit, AI)

**Analog:** `.planning/phases/02-ai-engine/02-REVIEW.md:60-69` (the BL-01 proof-of-concept)

**Existing file's tests** establish style (Read confirmed standard `def test_*` style). **NEW test to append:**
```python
def test_instance_multipliers_are_independent():
    """BL-01 regression: instance dicts must shadow class-level dicts so that
    apply_strategy() on adapter A never mutates adapter B's multipliers.

    The fix lives at parameter_adapter.py:54-56 (commit 2dfd5e1).
    This test catches any future refactor that silently removes it.
    """
    from python.ai.parameter_adapter import ParameterAdapter

    a1 = ParameterAdapter()
    a2 = ParameterAdapter()

    a1.SL_MULTIPLIERS["trending"] = 99.0
    a1.TP_MULTIPLIERS["trending"] = 88.0
    a1.LOT_MULTIPLIERS["trending"] = 77.0

    # a2 must be untouched
    assert a2.SL_MULTIPLIERS["trending"] == 1.0, "BL-01: SL cross-contamination"
    assert a2.TP_MULTIPLIERS["trending"] == 1.5, "BL-01: TP cross-contamination"
    assert a2.LOT_MULTIPLIERS["trending"] == 1.0, "BL-01: LOT cross-contamination"

    # Class-level dict must remain pristine
    assert ParameterAdapter.SL_MULTIPLIERS["trending"] == 1.0
    assert ParameterAdapter.TP_MULTIPLIERS["trending"] == 1.5
    assert ParameterAdapter.LOT_MULTIPLIERS["trending"] == 1.0
```

**Cross-cutting:** Apply S8.

---

### `python/tests/ai/test_strategy_manager.py` (Wave C: BL-01 cross-contam regression) — test (unit, AI)

**Analog:** Self — `test_apply_strategy_modifies_instances` at lines 124-135 (clone the structure, extend the assertions)

**Existing pattern to clone (lines 124-135):**
```python
def test_apply_strategy_modifies_instances(manager, detector, adapter, tmp_path):
    """Test 8: apply_strategy() modifies detector and adapter attributes in-place."""
    path = manager.export_strategy(
        RegimeDetector(adx_trend_threshold=40.0),
        ParameterAdapter(max_position_size=0.5),
        filepath=tmp_path / "test_strategy.json",
    )
    strategy = manager.import_strategy(path)
    result = manager.apply_strategy(detector, adapter, strategy)
    assert result is True
    assert detector.adx_trend == 40.0
    assert adapter.max_position_size == 0.5
```

**NEW test to append:**
```python
def test_apply_strategy_does_not_cross_contaminate(manager, tmp_path):
    """BL-01 regression: applying a strategy to adapter A must not affect adapter B.

    Export a strategy with a custom LOT multiplier, apply it to adapter_a only,
    and assert adapter_b's class-derived defaults are intact.
    """
    from python.ai.regime_detector import RegimeDetector
    from python.ai.parameter_adapter import ParameterAdapter

    adapter_a = ParameterAdapter()
    adapter_b = ParameterAdapter()
    detector_for_export = RegimeDetector()

    custom_adapter = ParameterAdapter()
    custom_adapter.LOT_MULTIPLIERS["trending"] = 0.01

    path = manager.export_strategy(
        detector_for_export, custom_adapter,
        filepath=tmp_path / "test_strategy.json",
    )
    strategy = manager.import_strategy(path)

    detector_a = RegimeDetector()
    manager.apply_strategy(detector_a, adapter_a, strategy)

    assert adapter_a.LOT_MULTIPLIERS["trending"] == 0.01
    assert adapter_b.LOT_MULTIPLIERS["trending"] == 1.0, "BL-01 regression"
    assert ParameterAdapter.LOT_MULTIPLIERS["trending"] == 1.0, "BL-01: class dict mutated"
```

**Cross-cutting:** Apply S8.

---

### `python/tests/dashboard/test_trades.py` (Wave C: G1 fixture reshape) — test (API, dashboard)

**Analog:** Self — lines 30-54 (fixture structure stays; entry-source content swaps)

**Existing fabricated fixture (lines 32-43):**
```python
entries = [
    {"event": "trade_open", "symbol": "EURUSD", "ticket": 1, "direction": "buy",
     "volume": 0.1, "price": 1.0850, "sl": 1.0825, "tp": 1.0900,
     "timestamp": "2026-05-26T10:15:00Z"},
    {"event": "trade_close", "ticket": 1, "profit": 50.0, "close_price": 1.0900,
     "timestamp": "2026-05-26T12:30:00Z"},
    ...
]
```

**Required reshape** — replace inline dict construction with a helper that produces strings using the **literal `Logger.mqh` `StringFormat` template** (so the EA contract is the source-of-truth):

```python
# python/tests/dashboard/test_trades.py — new helper at top of file
def ea_log_trade_open(ticket, symbol, direction, volume, price, sl, tp,
                     retcode=10009, comment="Futra",
                     timestamp="2026-05-26T10:15:00Z") -> str:
    """Emit a string character-for-character matching Logger.mqh:LogTradeOpen output.

    SOURCE: ea/include/Logger.mqh (post-G1).
    If the EA template changes, this fixture must change in the same commit.
    """
    return (
        f'{{"event":"trade_open","ticket":{ticket},"symbol":"{symbol}",'
        f'"direction":"{direction}","volume":{volume:.2f},"price":{price:.5f},'
        f'"sl":{sl:.5f},"tp":{tp:.5f},"retcode":{retcode},'
        f'"comment":"{comment}","timestamp":"{timestamp}"}}'
    )

def ea_log_trade_close(ticket, symbol, direction, volume, close_price, profit,
                       retcode=10009, comment="Position closed",
                       timestamp="2026-05-26T12:30:00Z") -> str:
    return (
        f'{{"event":"trade_close","ticket":{ticket},"symbol":"{symbol}",'
        f'"direction":"{direction}","volume":{volume:.2f},'
        f'"close_price":{close_price:.5f},"profit":{profit:.2f},'
        f'"retcode":{retcode},"comment":"{comment}","timestamp":"{timestamp}"}}'
    )
```

**Update `write_trade_log` to write raw strings** (existing helper at lines 20-24):
```python
def write_trade_log(log_path: Path, lines: list[str]):
    with open(log_path, "w") as f:
        for line in lines:
            f.write(line + "\n")
```

**Update each test body** (lines 32-43, 58-65, 73-80, 117-124) to call the new helpers instead of dict literals.

**Cross-cutting:** Apply S7 (patching idiom unchanged). The whole point of the reshape is that fixtures now match real producer output.

---

### `python/tests/dashboard/test_decisions.py` (Wave C: G2 verification) — test (API, dashboard)

**Analog:** Self — existing fixtures already match the post-G2 schema (including `"timeframe": "H1"` at lines 31, 34, 49, 52, 77).

**Required edits:** none beyond confirming. After G2 is shipped, run this file unchanged — all tests should still pass because the fixture data already conformed to what the dashboard reader expects.

**Optional:** add one new assertion in `test_decision_has_required_fields` to round-trip through the Pydantic model:
```python
from python.dashboard.models import Decision
decision_obj = Decision(**decision)
assert decision_obj.timeframe == "H1"
```

**Cross-cutting:** Apply S5 (Pydantic round-trip).

---

### `python/tests/dashboard/test_equity.py` (Wave C: G1 fixture reshape) — test (API, dashboard)

**Analog:** Self — same reshape pattern as `test_trades.py`

**Existing inline-dict pattern (lines 31-37) replaced** by calls to the `ea_log_trade_open` / `ea_log_trade_close` helpers (copied from `test_trades.py` OR factored into a shared helper module).

**Recommended factoring:** create `python/tests/dashboard/ea_log_fixtures.py` and have both `test_trades.py` and `test_equity.py` import from it. Single source of truth for the EA emission format.

**Cross-cutting:** Apply S7.

---

### `python/tests/integration/__init__.py` (Wave C: NEW) — test bootstrap

**Analog:** Empty `__init__.py` files elsewhere in `python/tests/` subtree

**Content:** empty file (or a single comment line):
```python
"""Producer→consumer integration tests for v1.0 contracts (Phase 5)."""
```

---

### `python/tests/integration/test_trade_log_contract.py` (Wave C: NEW — G1 round-trip) — test (integration)

**Analog:**
- For the assertion structure: `python/tests/dashboard/test_trades.py:30-54`
- For the auth + TestClient mechanics: `python/tests/dashboard/conftest.py:46-69`

**Imports pattern** (mirror dashboard tests):
```python
"""G1 producer→consumer round-trip: EA Logger.mqh format → trades.py reader.

These tests use the literal Logger.mqh StringFormat template (rebuilt in Python)
to emit lines that are character-for-character identical to what the recompiled
EA will write to MQL5/Files/Futra/trade_log.jsonl.

If Logger.mqh is changed, these tests must change in the same commit.
"""
import json
import pytest
from pathlib import Path
from python.dashboard.api.trades import read_trades, TRADE_LOG_PATH
from python.dashboard.api.equity import compute_equity_curve
```

**Fixture pattern (mirror S7 from `test_trades.py:8-17`):**
```python
@pytest.fixture
def temp_trade_log(tmp_path, monkeypatch):
    log_path = tmp_path / "Futra" / "trade_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("python.dashboard.api.trades.TRADE_LOG_PATH", log_path)
    monkeypatch.setattr("python.dashboard.api.equity.TRADE_LOG_PATH", log_path)
    return log_path
```

**Core test pattern** (from RESEARCH.md G1 validation strategy):
```python
def test_ea_trade_open_format_parses(temp_trade_log):
    """An EA-format trade_open line is correctly parsed by read_trades()."""
    line = (
        '{"event":"trade_open","ticket":12345,"symbol":"EURUSD",'
        '"direction":"buy","volume":0.10,"price":1.08500,'
        '"sl":1.08000,"tp":1.09000,"retcode":10009,'
        '"comment":"Futra","timestamp":"2026-05-29T10:15:00Z"}'
    )
    temp_trade_log.write_text(line + "\n")

    # Pure-Python parse (no API, no auth) to assert reader contract
    trades = read_trades(limit=10, offset=0)
    # Open without close → not in closed_trades; should return []
    assert trades == []


def test_ea_open_close_pair_join(temp_trade_log):
    """Open + close with matching ticket → one paired trade row."""
    lines = [
        '{"event":"trade_open","ticket":12345,"symbol":"EURUSD",'
        '"direction":"buy","volume":0.10,"price":1.08500,'
        '"sl":1.08000,"tp":1.09000,"retcode":10009,'
        '"comment":"Futra","timestamp":"2026-05-29T10:15:00Z"}',
        '{"event":"trade_close","ticket":12345,"symbol":"EURUSD",'
        '"direction":"buy","volume":0.10,"close_price":1.08800,'
        '"profit":30.00,"retcode":10009,"comment":"Position closed",'
        '"timestamp":"2026-05-29T12:30:00Z"}',
    ]
    temp_trade_log.write_text("\n".join(lines) + "\n")

    trades = read_trades(limit=10, offset=0)
    assert len(trades) == 1
    assert trades[0]["ticket"] == 12345
    assert trades[0]["entry_price"] == 1.08500
    assert trades[0]["exit_price"] == 1.08800
    assert trades[0]["profit"] == 30.00


def test_equity_curve_from_ea_emitted_closes(temp_trade_log):
    """Equity curve accumulates from EA-emitted trade_close events."""
    lines = [
        # ... three trade_open/close pairs across three days ...
    ]
    temp_trade_log.write_text("\n".join(lines) + "\n")

    curve = compute_equity_curve(days=30)
    assert len(curve) >= 1
    final_value = curve[-1]["value"]
    # initial_balance (10000) + sum(profits)
    assert final_value == 10000.0 + sum_of_profits
```

**Cross-cutting:** Apply S4 (reader idiom unchanged), S7 (patching idiom). The contract is "EA-format JSONL line → S4 reader path → correct row."

---

### `python/tests/integration/test_decision_log_contract.py` (Wave C: NEW — G2 + G5 round-trip) — test (integration)

**Analog:**
- For the JSONL round-trip: `python/tests/ai/test_decision_logger.py:25-36`
- For the consumer entrypoint: `python/dashboard/api/decisions.py:16-42`

**Imports pattern:**
```python
"""G2 + G5 producer→consumer round-trip: DecisionLogger → api/decisions.py.

Closes the audit's AI-04 + DASH-03 gaps end-to-end.
"""
import json
import pytest
from pathlib import Path
from python.ai.decision_logger import DecisionLogger
from python.ai.engine import AIEngine
from python.dashboard.api.decisions import read_decisions
from python.dashboard.models import Decision
```

**Fixture pattern:**
```python
@pytest.fixture
def patched_decision_log(tmp_path, monkeypatch):
    log_path = tmp_path / "decision_log.jsonl"
    monkeypatch.setattr("python.dashboard.api.decisions.DECISION_LOG_PATH", log_path)
    return log_path
```

**Core tests:**
```python
def test_decision_logger_writes_to_dashboard_path(patched_decision_log, tmp_path):
    """G2: DecisionLogger writes to decision_log.jsonl (the path the reader expects)."""
    logger = DecisionLogger(log_dir=patched_decision_log.parent)
    logger.log_decision(
        symbol="EURUSD",
        timeframe="H1",
        regime="trending",
        confidence=0.85,
        sl_pips=50.0,
        tp_pips=100.0,
        lot_size=0.10,
    )
    assert patched_decision_log.exists()
    rows = read_decisions(symbol=None, limit=10, offset=0)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "EURUSD"
    assert rows[0]["timeframe"] == "H1"


def test_decision_logger_round_trip_pydantic(patched_decision_log, tmp_path):
    """G2 sub-gap: writer record passes Decision Pydantic validation."""
    logger = DecisionLogger(log_dir=patched_decision_log.parent)
    logger.log_decision(
        symbol="EURUSD", timeframe="H1", regime="trending",
        confidence=0.85, sl_pips=50.0, tp_pips=100.0, lot_size=0.10,
    )
    line = patched_decision_log.read_text().strip()
    record = json.loads(line)
    # Must not raise ValidationError
    decision = Decision(**record)
    assert decision.timeframe == "H1"


def test_engine_default_constructs_decision_logger():
    """G5: AIEngine() defaults decision_logger to a real instance (not None)."""
    engine = AIEngine()
    assert isinstance(engine.decision_logger, DecisionLogger)


def test_engine_with_logging_disabled():
    """G5: enable_decision_log=False keeps decision_logger None."""
    engine = AIEngine(enable_decision_log=False)
    assert engine.decision_logger is None
```

**Cross-cutting:** Apply S5 (Pydantic round-trip), S6 (default-on), S7 (patching).

---

### `python/tests/integration/test_strategy_contract.py` (Wave C: NEW — G4 round-trip) — test (integration)

**Analog:**
- For the round-trip mechanics: `python/tests/ai/test_strategy_manager.py:79-87`
- For the consumer entrypoint: `python/dashboard/api/strategy.py:14-29`

**Imports + tests:**
```python
"""G4 producer→consumer round-trip: StrategyManager → api/strategy.py."""
import json
import pytest
from pathlib import Path
from python.ai.regime_detector import RegimeDetector
from python.ai.parameter_adapter import ParameterAdapter
from python.ai.strategy_manager import StrategyManager
from python.dashboard.api.strategy import read_strategy_config


def test_strategy_export_then_dashboard_read(tmp_path, monkeypatch):
    """G4: StrategyManager writes; dashboard reads the same file."""
    monkeypatch.setattr(
        "python.dashboard.api.strategy.STRATEGY_CONFIG_DIR", tmp_path
    )
    manager = StrategyManager(strategy_dir=tmp_path)
    manager.export_strategy(
        RegimeDetector(adx_trend_threshold=42.0),
        ParameterAdapter(max_position_size=0.25),
        filepath=tmp_path / "strategy_test.json",
    )

    config = read_strategy_config()
    assert config["regime_detector"]["adx_trend_threshold"] == 42.0
    assert config["parameter_adapter"]["max_position_size"] == 0.25


def test_strategy_manager_uses_canonical_dir():
    """G4: StrategyManager.strategy_dir matches STRATEGY_CONFIG_DIR (one const)."""
    from python.config import STRATEGY_CONFIG_DIR
    manager = StrategyManager()
    assert manager.strategy_dir == STRATEGY_CONFIG_DIR
```

**Cross-cutting:** Apply S7 (patching).

---

### `python/tests/integration/test_config_no_duplicates.py` (Wave C: NEW — G3 + G4 regression) — test (regression guard)

**Analog:** None (new test category — mechanical grep). RESEARCH.md §G3 validation strategy.

**Content:**
```python
"""G3 + G4 regression: config.py contains exactly one definition of each path constant.

Catches future refactors that accidentally re-introduce the duplicate-definition
class of bug (Phase 4 WR-05).
"""
from pathlib import Path
import re

CONFIG_SRC = Path(__file__).resolve().parents[2] / "config.py"


def test_ai_log_dir_defined_once():
    src = CONFIG_SRC.read_text()
    matches = re.findall(r"^AI_LOG_DIR\s*=", src, re.MULTILINE)
    assert len(matches) == 1, f"AI_LOG_DIR defined {len(matches)} times (G3 regression)"


def test_strategy_config_dir_defined_once():
    src = CONFIG_SRC.read_text()
    matches = re.findall(r"^STRATEGY_CONFIG_DIR\s*=", src, re.MULTILINE)
    assert len(matches) == 1, f"STRATEGY_CONFIG_DIR defined {len(matches)} times"


def test_ai_strategy_dir_removed():
    """G4: AI_STRATEGY_DIR must be deleted (consolidated into STRATEGY_CONFIG_DIR)."""
    src = CONFIG_SRC.read_text()
    assert "AI_STRATEGY_DIR" not in src, "AI_STRATEGY_DIR still in config.py (G4 regression)"


def test_ai_log_dir_resolves_project_root_relative():
    """S1: AI_LOG_DIR must resolve to <repo>/logs/ai regardless of CWD."""
    from python.config import AI_LOG_DIR
    repo_root = Path(__file__).resolve().parents[3]
    expected = (repo_root / "logs" / "ai").resolve()
    # Tolerate env-var override; only enforce when default is in effect
    import os
    if not os.getenv("FUTRA_AI_LOG_DIR"):
        assert AI_LOG_DIR.resolve() == expected


def test_strategy_config_dir_resolves_project_root_relative():
    from python.config import STRATEGY_CONFIG_DIR
    repo_root = Path(__file__).resolve().parents[3]
    expected = (repo_root / "configs" / "strategies").resolve()
    import os
    if not os.getenv("FUTRA_STRATEGY_CONFIG_DIR"):
        assert STRATEGY_CONFIG_DIR.resolve() == expected
```

**Cross-cutting:** Apply S1.

---

## Producer ↔ Consumer Contract Anchors

This is the single most important section for Phase 5 planning — every fix is "make file A match file B's existing convention." The table below names the **canonical side** (the side that does NOT change) and the **conforming side** (the side that is rewritten in this phase).

| Gap | Contract surface | Canonical side (no change) | Conforming side (rewrite in Phase 5) | Anchor pattern |
|-----|------------------|----------------------------|--------------------------------------|----------------|
| G1 | `trade_log.jsonl` JSON schema | `python/dashboard/api/trades.py:36-65` + `equity.py:40-59` (event-typed reader) | `ea/include/Logger.mqh` + EA call-sites | EA emits `event`, `direction`, `close_price`, `profit` to match `Trade` model (`models.py:38-48`) |
| G2 | `decision_log.jsonl` filename + record shape | `python/dashboard/api/decisions.py:12` (`AI_LOG_DIR / "decision_log.jsonl"`) + `Decision` model (`models.py:51-60`) | `python/ai/decision_logger.py:29-35, 81-91, 130-142` (single-file mode + `timeframe` field) | Writer record key-set ⊇ Pydantic `Decision` required fields |
| G3 | `AI_LOG_DIR` path constant | `python/config.py:18` (`IPC_DIR` pattern — project-root-relative) | `python/config.py:47, 109` (two duplicate defs) | S1 — single constant, `Path(__file__).parent.parent / ...` default |
| G4 | Strategy directory env var | `.env.example:42` (`FUTRA_STRATEGY_CONFIG_DIR`) + `dashboard/api/strategy.py:8` | `python/ai/strategy_manager.py:9, 32` + `python/config.py:48, 110` | One symbol (`STRATEGY_CONFIG_DIR`), one env var (`FUTRA_STRATEGY_CONFIG_DIR`), one project-root-relative default |
| G5 | `AIEngine` ↔ `DecisionLogger` wiring | `python/ai/engine.py:35-36` (existing default-on `or RegimeDetector()` pattern) | `python/ai/engine.py:31, 37` (`decision_logger=None` → enabled by default) | S6 — `decision_logger = DecisionLogger()` when not explicitly disabled |
| BL-01 | `ParameterAdapter` mutable state lifecycle | `python/ai/parameter_adapter.py:54-56` (fix already in place) | `python/tests/ai/test_parameter_adapter.py` + `test_strategy_manager.py` (NO regression test exists) | S8 — instance dicts shadow class dicts; regression test asserts independence |

## No Analog Found

None. Every file in Phase 5 has an in-tree analog. The only "novel" file is `python/ai/__main__.py` (production entry point) and even that mirrors the engine-receiving service-loop pattern in `python/validation/paper_trading.py`.

## Metadata

**Analog search scope:**
- `python/config.py` (full)
- `python/ai/{decision_logger,engine,strategy_manager,parameter_adapter}.py` (all full)
- `python/dashboard/api/{trades,equity,decisions,strategy}.py` (all full)
- `python/dashboard/models.py` (full)
- `python/ipc/ipc_writer.py` (full — atomic-write reference)
- `python/validation/paper_trading.py` (lines 1-50 — entry-point analog)
- `python/tests/ai/{test_decision_logger,test_strategy_manager,test_engine}.py` (all read)
- `python/tests/dashboard/{test_trades,test_decisions,test_equity,conftest}.py` (all read)
- `ea/include/{Logger,Common,OrderManager,PositionManager}.mqh` (all read)
- `.env.example` (full)
- `deploy/start-dashboard.ps1` (lines 120-179)

**Files scanned:** 25

**Pattern extraction date:** 2026-05-29

**No re-reads performed:** every file read once; large files (RESEARCH.md, MILESTONE-AUDIT.md) read with offset/limit pagination.
