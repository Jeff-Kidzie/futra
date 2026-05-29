# Phase 5: Close v1.0 integration gaps — Research

**Researched:** 2026-05-29
**Domain:** Cross-phase integration / data-contract reconciliation between EA (MQL5), AI engine (Python), and Dashboard (FastAPI + SvelteKit)
**Confidence:** HIGH — all findings verified against current source files at the line numbers given.

## Summary

Phase 5 is integration cleanup, not new feature work. The v1.0 audit identified five blocking data-contract mismatches (G1–G5) plus one tech-debt item (BL-01) that cumulatively make four DASH/AI requirements unsatisfiable in production. Phase 4 tests pass because they fabricate producer-side data; production won't have that luxury.

The fixes are small and well-scoped — each gap is a single contract decision (one schema, one filename, one env var, one wiring point) — but they share files (G2/G3/G5 all touch `python/config.py` and the AI logger; G4 touches `strategy_manager.py` whose call-site interacts with BL-01's fixed `ParameterAdapter`). **Sequencing matters more than complexity.**

**One important verification finding:** BL-01 was already partially fixed in commit `2dfd5e1` (the instance-level dict copy in `ParameterAdapter.__init__` at lines 54–56 is present). The audit reports it as unfixed because the audit was authored before re-verification. The remaining work for BL-01 is **regression test coverage** to lock the fix in, not a code change.

**Primary recommendation:** Execute fixes in three sequential waves: (Wave A) config cleanup + schema decision = G3 + G1 contract definition; (Wave B) producer-side rewrites + consumer alignment = G1 EA-side + G2 + G4 + G5; (Wave C) regression coverage = BL-01 multi-instance test + integration tests for every gap. Out-of-scope warnings (G6, G7, G8) are flagged but not included unless trivially included in Wave A config work.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-08 | All trade results and errors are logged with retcode, comment, and context for debugging | G1 — EA `LogTrade` already emits the data; the dashboard reader is what's broken. Fix is contract alignment, not new logging. |
| AI-04 | AI decision log records every parameter decision: regime detected, confidence, chosen parameters, and reasoning | G2 + G3 + G5 — writer works, but filename mismatch + duplicate config + no production wiring all break reads. Pydantic `Decision.timeframe` field is also un-emitted by the writer (hidden sub-gap). |
| AI-05 | Strategy parameter export/import as JSON/YAML for versioning and A/B testing different models | G4 — writer and reader use distinct env vars + defaults. BL-01 regression coverage required for A/B testing to actually be safe (the fix is in place, but no test enforces it). |
| DASH-02 | Trade history with deal details (entry/exit price, profit, duration, symbol, direction) | G1 — derives from the same schema fix as DATA-08. |
| DASH-03 | AI decision log display showing regime, confidence, parameters chosen, and reasoning per trade | Same as AI-04 (G2 + G3 + G5 + timeframe sub-gap). |
| DASH-04 | Equity curve and drawdown charting on dashboard | G1 — equity.py reads the same `trade_log.jsonl` whose schema doesn't match. CR-02 (within-window accumulation) was fixed in 9eb5e3c; G1 supersedes that fix. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trade event emission | EA (MQL5) | — | Only the EA observes the OrderSend result; Python cannot derive trade events from anywhere else. |
| Trade log schema definition | EA (MQL5) | Dashboard (Python) | Producer owns the canonical shape; consumer must conform. Decision is "match consumer expectations" vs. "rewrite consumer" — researched below. |
| AI decision emission | Python AI engine | — | Decision context exists only in Python (regime, confidence, reasoning). |
| AI decision filename convention | Python AI engine | Dashboard (Python) | Same module owns the file path constant; dashboard imports it. Single source of truth = `python/config.py`. |
| Config defaults (paths, dirs) | `python/config.py` | — | Centralized; both AI and dashboard import. Duplicate G3 violates this. |
| Production orchestration (AI engine loop) | New script (not yet existing) | `deploy/start-dashboard.ps1` | G5 + G8 — currently no production entry point wires DecisionLogger into AIEngine. |
| ParameterAdapter state lifecycle | `python/ai/parameter_adapter.py` | `strategy_manager.py` (call site) | Fix lives in adapter; tests must cover multiple adapters in one process. |

## Standard Stack

This phase introduces zero new libraries. All work is within existing stack:

| Library | Version | Purpose | Already in use |
|---------|---------|---------|----------------|
| Python `json` (stdlib) | 3.10+ | JSONL emission and parsing | yes |
| Python `pathlib` (stdlib) | 3.10+ | Path handling for log dirs | yes |
| Python `pytest` | from requirements.txt | Integration test runner | yes — 50 AI tests + 66 dashboard tests pass |
| Python `pydantic` v1/v2 | from FastAPI dependency | Response model validation | yes — `Decision`, `Trade`, `EquityPoint` defined in `python/dashboard/models.py` |
| MQL5 stdlib (FileOpen/FileWrite) | MT5 build 4100+ | JSONL file emission from EA | yes |

**Alternatives Considered:** none. This is a contract-reconciliation phase, not a stack decision.

## Architecture Patterns

### System Architecture Diagram (data flows affected by Phase 5)

```
[Producer]                          [File Contract]                        [Consumer]
                                                                          
EA (MQL5):                          MQL5/Files/Futra/                     Dashboard:
  Logger.mqh LogTrade   ── writes ──> trade_log.jsonl ─── reads ────> api/trades.py G1
                                       (one schema)                       api/equity.py G1
                                                                          
AI engine (Python):                 {AI_LOG_DIR}/                         
  decision_logger.py    ── writes ──> decision_log.jsonl ─ reads ───> api/decisions.py G2
                                       (one filename)                     (timeframe field G2-sub)
                                                                          
AI engine (Python):                 {AI_STRATEGY_DIR}/                    
  strategy_manager.py   ── writes ──> strategy_*.json ── reads ─────> api/strategy.py G4
                                       (one dir, one env var)             
                                                                          
Production orchestrator (NEW):                                            
  start-engine.py       ── creates ──> AIEngine(                            
                                          decision_logger=                  
                                          DecisionLogger(...)) ── G5
                                       ── loops ──> engine.run_once()       
```

Decision points after Phase 5:
1. Single trade-log schema with `event` field (G1)
2. Single `decision_log.jsonl` filename (G2) at single `AI_LOG_DIR` (G3)
3. Single `STRATEGY_CONFIG_DIR` env var (G4)
4. AI engine entry point exists and wires DecisionLogger (G5)
5. `ParameterAdapter` per-instance dicts are regression-tested (BL-01)

### Recommended File Touch Map

```
python/
├── config.py                       # G3 fix (remove duplicate AI_LOG_DIR), G4 fix (one env var)
├── ai/
│   ├── decision_logger.py          # G2 fix (filename), timeframe field add
│   ├── engine.py                   # G5 fix (default-on logger OR keep optional + add entry script)
│   ├── strategy_manager.py         # G4 fix (import renamed const)
│   └── parameter_adapter.py        # BL-01 — already fixed, NO CODE CHANGE NEEDED
├── dashboard/
│   ├── api/
│   │   ├── trades.py               # G1 fix — schema reader (entry/exit pairing)
│   │   ├── equity.py               # G1 fix — schema reader, G7 fix (use FUTRA_INITIAL_BALANCE)
│   │   ├── decisions.py            # G2 fix (filename), latest-day or globbed-merge
│   │   └── strategy.py             # G4 fix (import renamed const)
│   └── models.py                   # Decision.timeframe Optional OR DecisionLogger emits it
├── tests/
│   ├── ai/
│   │   ├── test_decision_logger.py # update fixture filename, add timeframe assertion
│   │   ├── test_strategy_manager.py # add BL-01 multi-instance regression
│   │   └── test_engine.py          # add live-logger integration if G5 default-on chosen
│   ├── dashboard/
│   │   ├── test_trades.py          # REPLACE fabricated fixtures with EA-shaped fixtures
│   │   ├── test_decisions.py       # REPLACE fabricated fixtures with DecisionLogger-emitted fixtures
│   │   └── test_equity.py          # REPLACE fabricated fixtures (CR-02 test stays, just reshape data)
│   └── integration/                # NEW directory — producer→consumer round-trip tests
│       ├── test_trade_log_contract.py     # EA-emitting code path → trades/equity
│       ├── test_decision_log_contract.py  # DecisionLogger → api/decisions
│       └── test_strategy_contract.py      # StrategyManager → api/strategy
ea/include/
└── Logger.mqh                      # G1 — EA-side schema change (add event, open/close, profit, close_price)

deploy/
└── start-engine.ps1                # G5 + G8 — NEW production entry point (or extend start-dashboard.ps1)
.env.example                        # G4 add/rename env vars, G6 add MT5_DEMO_* (optional)
```

### Anti-Patterns to Avoid

- **Producer-side fabrication in tests** — every Phase 4 test that writes `{"event": "trade_open", ...}` directly to a JSONL file is a fabricated fixture; the actual producer (`Logger.mqh`) emits a completely different shape. Phase 5 tests must use the *real* writer code path, even if that means a Python helper that mimics `Logger.mqh`'s exact StringFormat output character-for-character.
- **Adding a translator layer instead of fixing the schema** — do not add a "translate trade_log entries to dashboard format" module. The decision is which side moves; the gap should disappear, not be papered over.
- **Mutating class-level dicts via `.update()`** — even though `ParameterAdapter.__init__` now copies (lines 54–56), any new code that does `SomeClass.SOME_DICT.update(...)` on a class attribute will silently regress. The regression test must catch this category.
- **Hardcoded defaults that diverge from `config.py`** — e.g., `equity.py:19 initial_balance: float = 10000.0` and `equity.py:99 compute_equity_curve(days=days)` (no initial_balance argument passed). This is G7 — flag it but defer unless trivially co-fixed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSONL parsing | Custom regex-based line parser | `json.loads()` per line, skip on `JSONDecodeError` | Already the pattern in `trades.py`, `decisions.py`, `equity.py`. Consistent error handling. |
| Schema validation on log entries | Manual dict-key checks | Pydantic `Decision` / `Trade` model `.model_validate()` (or just trust the producer + skip-on-error) | Pydantic already in the stack; failures surface as 500s on the endpoint, which is the desired loudness. |
| Atomic file writes (for strategy JSON exports) | Direct `open("w")` | `os.replace(tmp, final)` pattern from `python/ipc/ipc_writer.py:42` | This pattern is already used elsewhere in the codebase for safe writes against polling readers. |
| MQL5 JSON emission | Imported MQL5 JSON library | Existing `StringFormat` pattern in `Logger.mqh` | The codebase already builds JSON by hand in MQL5 (no MT5 native JSON); just extend the format string. Don't introduce a dependency. |
| Multi-day decision log aggregation (if writer keeps daily rotation) | Custom file-glob aggregator at the dashboard | Decide at G2 — either writer goes single-file (no rotation needed) or reader globs `ai_decisions_*.jsonl` and merges. Pick one. | Two valid answers; the cost of "wrong" is a config flag, not engineering work. |

## Runtime State Inventory

Phase 5 is mostly code/config edits, but **two categories of runtime state exist** and must be addressed in the plan:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | (1) `trade_log.jsonl` files in any active MT5 `MQL5/Files/Futra/` directories — written with the OLD flat schema (no `event` field). (2) Any existing `ai_decisions_YYYY-MM-DD.jsonl` files at the old (or correct) path. | (1) Trade log: per producer-side fix, old entries will be unreadable by the new reader; recommend deleting before testing (cheap — no live trading was happening). (2) Decision log: same — purge before validating new pipeline. |
| Live service config | None — no n8n/Datadog/external services involved | None |
| OS-registered state | None — `deploy/start-dashboard.ps1` is the only orchestration script and it's in git. If G5 produces a new `start-engine.ps1`, no OS task registration is implied (PowerShell scripts run on demand). | None — unless future work wraps these as Windows services, which is out of scope. |
| Secrets/env vars | `FUTRA_AI_STRATEGY_DIR` (currently writer-only, undocumented in `.env.example`) and `FUTRA_STRATEGY_CONFIG_DIR` (currently reader-only, documented). G4 collapses to one. Any operator who explicitly set the writer var will lose effect unless the renamed var is honored. | Plan must (a) decide a canonical name, (b) update `.env.example`, (c) communicate the rename. Since no operator has set this in production (no production exists yet — v1.0 not shipped), the impact is theoretical. |
| Build artifacts | None — no compiled binaries or pip-installed packages. `frontend/build/` is regenerated. | None |

**Nothing found in:** Live service config (verified — no external services); OS-registered state (verified — only `start-dashboard.ps1`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All Python edits + tests | ✓ assumed (Phase 1-4 tests pass) | — | — |
| pytest | Test execution | ✓ | per requirements.txt | — |
| pydantic | Dashboard model validation | ✓ | FastAPI-bundled | — |
| MT5 terminal + MQL5 compiler | G1 EA-side change verification | ✗ likely missing on planning machine | — | Recommend: design G1 fix as a Python-side test that **encodes the exact** `StringFormat` template from `Logger.mqh:30-37` as a string-template fixture, then asserts dashboard reader parses it. EA-side compile + execution verification is a manual gate done by the operator on Windows + MT5. |
| File-based IPC (`MQL5/Files/Futra/`) | G1 round-trip integration test | ✗ requires MT5 install | — | Test against `python/ipc/ipc_writer.py` pattern (atomic write to a `tmp_path`) — same I/O semantics. |

**Missing dependencies with no fallback:** None blocking.

**Missing dependencies with fallback:**
- MT5 + MQL5 compile chain → use string-template fixtures derived from the literal `Logger.mqh` source. Document that final EA verification is a manual step (operator runs the recompiled EA on demo MT5 and grep-checks `trade_log.jsonl`).

## Gap-by-Gap Research

---

### G1: Trade log schema mismatch — EA flat schema vs. dashboard event-typed reader

**Affects:** DATA-08, DASH-02, DASH-04

#### Current state

EA `Logger.mqh:27-56` emits the following per `LogTrade()` call (verified):

```mql5
string jsonLine = StringFormat(
   "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\","
   "\"volume\":%.2f,\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,"
   "\"retcode\":%d,\"comment\":\"%s\",\"timestamp\":\"%s\"}",
   result.ticket, result.symbol, result.type,
   result.volume, result.price, result.sl, result.tp,
   result.retcode, result.comment, timestamp
);
```

Keys emitted: `ticket, symbol, type, volume, price, sl, tp, retcode, comment, timestamp`. **No `event` field. No `profit`. No `close_price`. No `direction` (only `type` which is "buy" / "sell").**

`Logger.mqh` is called from:
- `OrderManager.mqh:114` (OpenBuyOrder) and `:190` (OpenSellOrder) — opens
- `PositionManager.mqh:82` (ClosePosition with `comment="Position closed"`) — closes
- `PositionManager.mqh:166` (ModifySLTP with `comment="SL/TP modified"`) — modifications

Both open and close currently write to the same `LogTrade()` and produce the same flat schema with no event discriminator — the only difference is the `comment` string.

Dashboard `trades.py:36-65` (verified):

```python
if entry.get("event") == "trade_open":
    open_trades[entry["ticket"]] = entry
elif entry.get("event") == "trade_close":
    ticket = entry["ticket"]
    if ticket in open_trades:
        ...
        closed_trades.append({
            "ticket": ticket,
            "symbol": op["symbol"],
            "direction": op["direction"],
            "entry_price": op["price"],
            "exit_price": entry.get("close_price", 0),
            "profit": entry.get("profit", 0),
            ...
        })
```

Reader expects: `event ∈ {"trade_open", "trade_close"}`, `direction`, `close_price`, `profit`. None of these are emitted by the EA.

Dashboard `equity.py:40-59` (verified): same `entry.get("event") == "trade_close"` gate, reads `profit` and `timestamp`. Same gap.

**Quantification of severity:** every single trade dashboard query against a real EA log returns `[]`. The Phase 4 tests pass because `python/tests/dashboard/test_trades.py:32-43` and `test_equity.py:30-37` write the fabricated `event`-typed entries directly. There is **zero** production validation of the reader.

#### Recommended fix

**Move the producer (EA) to emit the dashboard's schema.** Rationale:

1. **EA already has the data.** `TradeResult` (Common.mqh:29-41) carries ticket, symbol, type, volume, price, sl, tp, retcode, comment, timestamp. The only missing fields are `event` (compile-time literal "trade_open"/"trade_close"), `direction` (= type), `profit` (available only on close — from `PositionGetDouble(POSITION_PROFIT)` before close, or from order history after), and `close_price` (= the execution price of the closing OrderSend, already in `result.price`).
2. **MQL5 changes are cheaper than dashboard changes** — `Logger.mqh` is ~115 lines, has no external consumers besides the file, and the change is a parameter addition to `LogTrade()` and two new format strings.
3. **Three Phase 4 readers depend on this schema** (`trades.py`, `equity.py`, and indirectly drawdown). Rewriting them is more total code churn than rewriting the EA logger.
4. **The dashboard schema is semantically richer** — it distinguishes open from close, which is what users want to see. The EA's "every result is a trade row" view is operationally noisy (modifications produce phantom rows).

**Canonical schema (single line per event):**

```json
// trade_open
{
  "event": "trade_open",
  "ticket": 12345,
  "symbol": "EURUSD",
  "direction": "buy",         // renamed from "type" for consumer compat
  "volume": 0.10,
  "price": 1.08500,
  "sl": 1.08000,
  "tp": 1.09000,
  "retcode": 10009,
  "comment": "Futra",
  "timestamp": "2026-05-29T10:15:00Z"
}

// trade_close
{
  "event": "trade_close",
  "ticket": 12345,            // SAME ticket as the open it pairs with
  "symbol": "EURUSD",
  "direction": "buy",         // matches the open direction (the closing order is opposite, but conceptually the trade was a buy)
  "volume": 0.10,
  "close_price": 1.08800,
  "profit": 30.00,            // realized P&L from PositionGetDouble(POSITION_PROFIT) at close time
  "retcode": 10009,
  "comment": "Position closed",
  "timestamp": "2026-05-29T12:30:00Z"
}

// modify (kept as informational; readers ignore — Phase 4 readers already filter by event)
{
  "event": "trade_modify",
  "ticket": 12345,
  "sl": 1.08200,
  "tp": 1.09200,
  "retcode": 10009,
  "timestamp": "2026-05-29T11:00:00Z"
}

// error (replace existing LogError shape — keep level/context/details for backward compat with operator log-grep habits, but add event for filter symmetry)
{
  "event": "error",
  "level": "error",
  "context": "OpenBuyOrder",
  "errorCode": 10004,
  "details": "Requote",
  "timestamp": "2026-05-29T10:15:00Z"
}
```

**Important EA-side detail:** the close-side ticket must be the **position ticket being closed**, not the order ticket of the closing order. `PositionManager.mqh:72` currently sets `logEntry.ticket = result.order` — this is the closing order's ticket, not the position's. The fix must `logEntry.ticket = ticket` (the parameter passed into `ClosePosition`) so the open/close pair joins correctly in `trades.py:37-40`.

#### Files to modify

- `ea/include/Logger.mqh` — replace `LogTrade(TradeResult&)` signature with `LogTradeOpen(TradeResult&)`, `LogTradeClose(TradeResult&, double profit)`, `LogTradeModify(ulong ticket, double sl, double tp, int retcode)`, `LogError(...)` (unchanged or extend with event field). Or keep `LogTrade(TradeResult&, string event_type)` overloads — simpler.
- `ea/include/OrderManager.mqh:114, 190` — change `LogTrade(tradeResult)` to `LogTradeOpen(tradeResult)`.
- `ea/include/PositionManager.mqh:82` — change `LogTrade(logEntry)` to `LogTradeClose(logEntry, PositionGetDouble(POSITION_PROFIT))`. **And fix the ticket** (line 72): `logEntry.ticket = ticket;` instead of `result.order`.
- `ea/include/PositionManager.mqh:166` — change `LogTrade(logEntry)` to `LogTradeModify(...)` or just append `event: "trade_modify"`.
- `python/dashboard/api/trades.py` — likely **no change** (already reads the target schema correctly). Verify ticket-pairing still works against the EA's now-corrected ticket.
- `python/dashboard/api/equity.py` — likely **no change**. CR-02 fix from 9eb5e3c stays. But once G1 is live, the reader will actually find `trade_close` entries.
- `python/tests/dashboard/test_trades.py` and `test_equity.py` — **replace fabricated fixtures** with a helper that produces strings character-for-character identical to `Logger.mqh`'s `StringFormat` output.
- `python/dashboard/models.py:38-48` `Trade` — verify all required fields are present in the new EA emission (currently requires `entry_price, exit_price, profit, open_time, close_time, duration` — all derived in `trades.py`, OK).

#### Files to read first (closest analog patterns)

- `python/ai/decision_logger.py:108-152` — Python's parallel pattern: structured dict → `json.dumps` → append-to-JSONL. The EA must produce a string that, when read by `json.loads`, yields the equivalent dict. The Python emitter is the canonical reference for what each field should look like.
- `python/ipc/ipc_writer.py:17-49` — atomic write pattern using `os.replace`. The EA uses append + `FILE_SHARE_READ`, not atomic-rename. This is acceptable for append-only JSONL but worth noting if the format string ever produces a partial line on a power-loss event. **Not a Phase 5 concern.**
- `python/tests/ai/test_decision_logger.py:25-36` — example of testing JSONL emission and `json.loads` round-trip. Reuse the assertion style for G1's new EA-emitter tests.

#### Validation strategy (no fabricated fixtures)

Create a Python helper that **executes the literal `StringFormat` template** from `Logger.mqh` (copy-pasted into the test file as a Python f-string equivalent), then writes the resulting line to a temp `trade_log.jsonl`, then calls `trades.read_trades()` and `equity.compute_equity_curve()` against that file. Two new test files:

- `python/tests/integration/test_trade_log_contract.py`:
  - `test_ea_trade_open_format_parses` — emit a string using the *new* EA format template; assert `read_trades` returns expected dict with all required fields.
  - `test_ea_open_close_pair_join` — emit one open + one close with matching ticket; assert one element in `read_trades` output with correct `entry_price` and `exit_price`.
  - `test_unmatched_close_is_dropped` — emit a close without preceding open; assert empty result (current `trades.py:36-40` behavior).
  - `test_equity_curve_from_ea_emitted_closes` — emit known sequence of closes; assert equity curve matches expected accumulation.

The format-string template must be **literally copy-pasted from `Logger.mqh`** into the test as the source-of-truth — if the EA changes, the test fails and gets updated as one atomic commit.

**Manual gate:** after automated tests pass, operator recompiles the EA, runs one demo trade, and `Get-Content trade_log.jsonl | ConvertFrom-Json` returns valid objects. Document in 05-SUMMARY.md.

#### Risks/landmines

- **Ticket pairing depends on close emitting the position ticket, not the closing order ticket.** `PositionManager.mqh:72` currently does the wrong thing — this must be fixed as part of G1, or trade pairs will never join.
- **`profit` source on close** — `PositionGetDouble(POSITION_PROFIT)` returns the *floating* profit at the moment of the call. It must be read *before* the position is closed (i.e., right after `PositionSelectByTicket`), not after. Otherwise the position is gone and the call returns 0.
- **Modify events also flow through `LogTrade` currently** (PositionManager.mqh:166). After splitting into `LogTradeOpen` / `LogTradeClose` / `LogTradeModify`, the reader filters by `event` — modify rows are silently ignored, which is correct. But operators who grep `trade_log.jsonl` for raw debugging will see new line shapes.
- **Phase 4 verification (04-VERIFICATION.md) was post-G1 fabricated fixtures.** Re-running `/gsd-verify-work 04` after G1 will need the same fabricated-vs-real distinction acknowledged.
- **Backward compatibility with existing `trade_log.jsonl`** — if any operator has rows from the OLD format on disk, the new reader will silently skip them (no `event` field, `entry.get("event")` returns None, neither branch matches). Recommend purge-before-deploy.

---

### G2: AI decision log filename mismatch — daily rotation vs. single file

**Affects:** AI-04, DASH-03

#### Current state

Writer `python/ai/decision_logger.py:31-35` (verified):

```python
def _get_log_path(self) -> Path:
    """Get today's log file path. Rotates daily."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != self._current_date:
        self._current_date = today
        self._file_path = self.log_dir / f"ai_decisions_{today}.jsonl"
    return self._file_path
```

Reader `python/dashboard/api/decisions.py:12` (verified):

```python
DECISION_LOG_PATH = AI_LOG_DIR / "decision_log.jsonl"
```

Writer produces e.g. `ai_decisions_2026-05-29.jsonl`, reader looks for `decision_log.jsonl`. **Never matches.**

Phase 2 02-02-SUMMARY.md line 24 records the daily rotation as a locked decision: *"Decision logger uses daily file rotation (ai_decisions_YYYY-MM-DD.jsonl) for human-readable per-day logs"*. So writer-side change requires undoing a Phase 2 design decision.

Phase 4 04-RESEARCH.md and 04-01-PLAN.md both reference `decision_log.jsonl` — they assumed the simpler convention. Phase 4 also tests against `decision_log.jsonl` fixtures (`test_decisions.py:11` patches `DECISION_LOG_PATH` to a `tmp_path / "decision_log.jsonl"`).

**Hidden sub-gap (also G2):** the `Decision` pydantic model at `python/dashboard/models.py:51-60` declares `timeframe: str` as a **required** field. The writer record at `decision_logger.py:130-142` **does not emit `timeframe`**. Once the path mismatch is fixed, any production read attempt will raise Pydantic `ValidationError: timeframe field required`.

#### Recommended fix

**Move the writer to single-file mode (no rotation)** and **add `timeframe` to the writer record**. Rationale:

1. **Dashboard is the wider consumer surface** — three dashboard reader endpoints already reference `decision_log.jsonl`-style single-file expectations. Changing the writer is a localized fix in `decision_logger.py`; changing the reader propagates through dashboard tests and documentation.
2. **Daily rotation is a feature without a customer.** Phase 2 chose it for "human-readable per-day logs," but the dashboard reader needs all decisions in one stream. No one is grepping daily files manually in production. If size becomes an issue (months from now), introduce logrotate-style external rotation.
3. **Single file is the convention everywhere else** — `trade_log.jsonl` (also a JSONL stream from a long-running producer) uses a single file. Symmetry > localized cleverness.

**Alternative (rejected):** keep daily rotation, change reader to glob `ai_decisions_*.jsonl` and merge. Rejected because it complicates pagination (offsets across files), requires sort-by-timestamp instead of sort-by-line-order, and adds a globbing fragility (what if filenames have a typo? what about midnight UTC race conditions?). Simpler to drop rotation.

**Canonical:** `{AI_LOG_DIR}/decision_log.jsonl` — one append-only file, infinite lifetime within a deployment.

**Writer record additions:**
```python
record = {
    "timestamp": timestamp,
    "symbol": symbol,
    "timeframe": timeframe,    # NEW — passed in from AIEngine.timeframe
    "regime": regime,
    ...
}
```

`AIEngine.evaluate_symbol` (engine.py:91-103) must pass `timeframe=self.timeframe` into `decision_logger.log_decision(...)`. The `DecisionLogger.log_decision()` signature must add `timeframe: str` as a required parameter (no default — fail loud on misuse).

#### Files to modify

- `python/ai/decision_logger.py:29-35` — replace `_get_log_path` with constant `self.log_dir / "decision_log.jsonl"`. Delete `_current_date` / `_file_path` instance state.
- `python/ai/decision_logger.py:81-91` — add `timeframe: str` parameter to `log_decision`.
- `python/ai/decision_logger.py:130-142` — add `"timeframe": timeframe` to the record dict.
- `python/ai/engine.py:91-103` — pass `timeframe=self.timeframe` into `decision_logger.log_decision(...)`.
- `python/tests/ai/test_decision_logger.py` — every `logger.log_decision(...)` call needs a `timeframe="H1"` argument. The test that asserts files glob `*.jsonl` (lines 21-22, 28-29, 42-43, etc.) is fine as-is; the test that asserts a single file is created becomes simpler.
- `python/tests/dashboard/test_decisions.py:11-15` — the `temp_decision_log` fixture already patches the right file path; no change.

#### Files to read first (closest analog patterns)

- `python/dashboard/api/trades.py:12` — `TRADE_LOG_PATH = IPC_DIR / "Futra" / "trade_log.jsonl"`. Same single-file pattern. Mirror this in `decisions.py`.
- `python/ai/decision_logger.py:108-152` — current `log_decision` writes append-mode (`open(log_path, "a")`). Stays the same.
- `python/dashboard/models.py:51-60` `Decision` — review whether `timeframe` should be required vs. Optional. Recommend required (loud failure on writer misconfiguration).

#### Validation strategy (no fabricated fixtures)

New file `python/tests/integration/test_decision_log_contract.py`:

- `test_decision_logger_writes_to_dashboard_path` — instantiate `DecisionLogger(log_dir=tmp_path)`, call `log_decision(...)`, assert `(tmp_path / "decision_log.jsonl").exists()` AND `read_decisions()` (with patched `DECISION_LOG_PATH`) returns the record.
- `test_decision_logger_round_trip_pydantic` — call `log_decision(...)`, read the file, parse each line through `Decision(**entry)` — assert no `ValidationError`. This catches the timeframe gap and any future field mismatches.
- `test_decision_logger_multi_call_appends` — call `log_decision(...)` three times across simulated date changes (or just back-to-back); assert all three lines in the same file.

#### Risks/landmines

- **Existing `ai_decisions_YYYY-MM-DD.jsonl` files** on dev/test machines will be orphaned after the change. Recommend purge or one-time migration script. Test environments don't care.
- **Pydantic validation on bad timeframe values** — `Decision.timeframe: str` accepts any string. If the writer ever passes an empty string or wrong value, the reader silently shows garbage. The plan should require `timeframe in {"M15", "H1", "H4", "D1"}` via Pydantic `Literal` or a validator — but this is enhancement, not blocking.
- **No production AIEngine instance exists yet** (G5 — see below), so the writer's `timeframe` parameter is hypothetical until G5 is wired. Land G2 first; G5 inherits the new signature for free.
- **`02-02-SUMMARY.md` records the rotation as a deliberate decision.** The plan must explicitly note this is a Phase 5 override of a Phase 2 decision (a single sentence in 05-SUMMARY.md suffices — no need to amend Phase 2 docs).

---

### G3: Duplicate `AI_LOG_DIR` definition in `config.py`

**Affects:** AI-04, DASH-03

#### Current state

`python/config.py:47` (Phase 2 definition — verified):

```python
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", str(Path(__file__).parent / "ai" / "decisions")))
```

Default: `<repo>/python/ai/decisions/` (project-root-relative, since `__file__ = config.py` lives at `python/`).

`python/config.py:109` (Phase 4 definition — verified):

```python
# AI log directory (Phase 2) — may not exist until Phase 2 is executed
AI_LOG_DIR = Path(os.getenv("FUTRA_AI_LOG_DIR", "logs/ai"))
```

Default: `logs/ai/` (CWD-relative — meaningless until you know where the dashboard process was launched from).

Line 109 wins (executes second). Both `decision_logger.py:11` and `dashboard/api/decisions.py:8` import `AI_LOG_DIR`, so both get the CWD-relative `logs/ai`. The decision logger then `mkdir(parents=True, exist_ok=True)` at `decision_logger.py:25` and writes there. The dashboard reads from `logs/ai/decision_log.jsonl` (CWD-relative). If both processes are launched from the same CWD (e.g., the project root), this *accidentally works* — but if the AI engine runs from `python/` while the dashboard runs from the project root, the paths diverge silently.

`.env.example:40` documents `FUTRA_AI_LOG_DIR=logs/ai` (matches line 109).

Phase 4 04-REVIEW.md WR-05 already flagged this; not fixed.

#### Recommended fix

**Keep one definition; delete the other.** Recommend keeping **line 109's default value** but moving it to the top of the file (next to other path constants near line 47) AND making the default project-root-relative instead of CWD-relative.

```python
# At line 47 area (consolidate with other config):
AI_LOG_DIR = Path(os.getenv(
    "FUTRA_AI_LOG_DIR",
    str(Path(__file__).parent.parent / "logs" / "ai"),
))
```

Rationale:
- `.env.example` documents `FUTRA_AI_LOG_DIR=logs/ai` (Phase 4's value, simpler to type, matches the operator's mental model).
- Project-root-relative default (`Path(__file__).parent.parent`) eliminates CWD ambiguity.
- Co-located with other path constants for grepability.

**Delete line 109.** Keep all other Phase 4 additions (lines 100–110 minus the duplicate) — these are dashboard-specific and belong below.

#### Files to modify

- `python/config.py` — remove line 109 entirely. Update line 47 with the project-root-relative default (as shown above). One-line change.
- `.env.example:40` — no change needed (value is `logs/ai`, still resolves correctly with the new default).

#### Files to read first

- `python/config.py:18` — `IPC_DIR = Path(os.getenv("FUTRA_IPC_DIR", str(Path(__file__).parent.parent / "ipc")))` — this is the exact project-root-relative pattern to mirror.

#### Validation strategy

- `python/tests/integration/test_config_no_duplicates.py` (new):
  - `test_ai_log_dir_defined_once` — `grep_count("AI_LOG_DIR\\s*=", "python/config.py") == 1`. Mechanical assertion that prevents regression.
  - `test_ai_log_dir_resolves_project_relative` — assert `AI_LOG_DIR.is_absolute()` is False but the resolved path equals `<repo>/logs/ai` regardless of CWD.

#### Risks/landmines

- **Any operator who set `FUTRA_AI_LOG_DIR` explicitly is unaffected** (env var overrides default in both old and new definitions).
- **Decision logger and dashboard reader now reliably agree** — but verify by running the integration test from G2 from both `/python/` and `/` CWDs.
- **Phase 4 review WR-05 stays informational after this fix** — mark as closed in the audit-derived debt list during /gsd-complete-milestone.

---

### G4: Strategy directory env var mismatch

**Affects:** AI-05

#### Current state

`python/ai/strategy_manager.py:9, 32` (verified):

```python
from ..config import AI_STRATEGY_DIR
# ...
def __init__(self, strategy_dir: Path | None = None):
    self.strategy_dir = strategy_dir or AI_STRATEGY_DIR
    self.strategy_dir.mkdir(parents=True, exist_ok=True)
```

`python/dashboard/api/strategy.py:8, 16` (verified):

```python
from ...config import STRATEGY_CONFIG_DIR
# ...
def read_strategy_config() -> dict:
    path = STRATEGY_CONFIG_DIR
```

`python/config.py:48` (writer-side):

```python
AI_STRATEGY_DIR = Path(os.getenv("FUTRA_AI_STRATEGY_DIR", str(Path(__file__).parent / "ai" / "strategies")))
```

Default: `<repo>/python/ai/strategies/`. Env var: `FUTRA_AI_STRATEGY_DIR`. **Undocumented in `.env.example`.**

`python/config.py:110` (reader-side):

```python
STRATEGY_CONFIG_DIR = Path(os.getenv("FUTRA_STRATEGY_CONFIG_DIR", "configs/strategies"))
```

Default: `configs/strategies/` (CWD-relative — same problem as G3). Env var: `FUTRA_STRATEGY_CONFIG_DIR`. Documented in `.env.example:42`.

Two distinct constants, two distinct env var names, two distinct defaults, never reconciled.

#### Recommended fix

**Collapse to one constant, one env var.** Recommend:
- **Constant name:** `STRATEGY_CONFIG_DIR` (consumer-side wins because `.env.example` already documents `FUTRA_STRATEGY_CONFIG_DIR` — operator-facing naming is harder to change than internal naming).
- **Env var name:** `FUTRA_STRATEGY_CONFIG_DIR` (same reason).
- **Default value:** project-root-relative `configs/strategies` — `Path(__file__).parent.parent / "configs" / "strategies"`.

```python
# python/config.py (single canonical definition near line 48):
STRATEGY_CONFIG_DIR = Path(os.getenv(
    "FUTRA_STRATEGY_CONFIG_DIR",
    str(Path(__file__).parent.parent / "configs" / "strategies"),
))
```

Delete `AI_STRATEGY_DIR` entirely. Update `strategy_manager.py:9, 32` to import and use `STRATEGY_CONFIG_DIR`.

**Alternative (rejected):** keep `AI_STRATEGY_DIR` as the canonical name. Rejected because `.env.example` and Phase 4 docs use `STRATEGY_CONFIG_DIR` — renaming the operator-facing env var is more user-visible than renaming the internal symbol.

#### Files to modify

- `python/config.py:48` — delete `AI_STRATEGY_DIR` line entirely.
- `python/config.py:110` — replace with the canonical definition (move/update).
- `python/ai/strategy_manager.py:9` — `from ..config import STRATEGY_CONFIG_DIR`.
- `python/ai/strategy_manager.py:32` — `self.strategy_dir = strategy_dir or STRATEGY_CONFIG_DIR`.
- `.env.example:42` — already documents `FUTRA_STRATEGY_CONFIG_DIR=configs/strategies`, no change.

#### Files to read first

- `python/config.py:18` — `IPC_DIR` pattern (project-root-relative). Mirror.
- `python/tests/ai/test_strategy_manager.py:12` — fixture uses `tmp_path / "strategies"` directly; not affected by the env var rename.
- `python/dashboard/api/strategy.py:14-29` — `read_strategy_config()` globs `*.json` and picks newest by mtime. Works with any directory.

#### Validation strategy

New file `python/tests/integration/test_strategy_contract.py`:

- `test_strategy_export_then_dashboard_read` — instantiate `StrategyManager(strategy_dir=tmp_path)`, call `export_strategy(detector, adapter)` to produce a JSON file, then monkeypatch `STRATEGY_CONFIG_DIR` to `tmp_path` and call `read_strategy_config()`. Assert the returned dict matches what was exported. This is the round-trip the audit said never existed.
- `test_strategy_manager_uses_canonical_dir` — assert `StrategyManager().strategy_dir == STRATEGY_CONFIG_DIR` (same constant).
- `test_only_one_strategy_dir_constant_exists` — `grep_count("STRATEGY.*DIR\\s*=", "python/config.py") == 1` and `grep("AI_STRATEGY_DIR", "python/config.py") == 0`. Mechanical regression guard.

#### Risks/landmines

- **`AI_STRATEGY_DIR` is referenced in `02-02-SUMMARY.md` and `02-02-PLAN.md`** as the locked Phase 2 name. Plan must note "Phase 5 supersedes Phase 2's AI_STRATEGY_DIR naming for v1.0 consumer alignment." No retroactive Phase 2 doc edit needed.
- **Any operator who set `FUTRA_AI_STRATEGY_DIR`** (none, since v1.0 hasn't shipped) loses effect. Acceptable.
- **Default value change** from CWD-relative `configs/strategies` to project-root-relative — this could move where strategy files appear in dev environments. Verify by deleting any existing dev strategy files and re-running export.
- **Phase 4 04-REVIEW.md** also notes the dashboard side's CWD-relative default as a problem (lines 314-322 of 04-REVIEW.md); fixing it project-root-relative kills two birds.

---

### G5: AIEngine `decision_logger=None` default — no production wiring

**Affects:** AI-04, DASH-03

#### Current state

`python/ai/engine.py:31, 37` (verified):

```python
class AIEngine:
    def __init__(
        self,
        symbols: list[str] | None = None,
        timeframe: str = AI_DEFAULT_TIMEFRAME,
        regime_detector: RegimeDetector | None = None,
        parameter_adapter: ParameterAdapter | None = None,
        decision_logger: DecisionLogger | None = None,   # line 31
    ):
        ...
        self.decision_logger = decision_logger  # None → logging disabled    line 37
```

Grep verification: `AIEngine(` appears in **one file only** — `python/tests/ai/test_engine.py`. There is **zero production code** that constructs `AIEngine`. `python/validation/paper_trading.py:32-37` accepts an `engine` parameter and expects the caller to provide one, but no caller exists.

Grep verification: `DecisionLogger(` appears only in `python/tests/ai/test_decision_logger.py`. Same — no production constructor.

`deploy/start-dashboard.ps1` orchestrates **only FastAPI + Caddy** (verified lines 132-175). It does not instantiate or run the AI engine. F1 (live trading) and F3 (paper trading) flows are documented but have no production entry point — this is G8 in the audit (warning, not blocker).

#### Recommended fix

**Two-part fix, both required:**

1. **Default `DecisionLogger` to ON in `AIEngine.__init__`** when not explicitly passed `None`. Change the parameter semantics from "optional → logging disabled" to "sentinel-required → logging disabled":

```python
# python/ai/engine.py
_LOGGING_DISABLED = object()  # sentinel

def __init__(
    self,
    ...,
    decision_logger: DecisionLogger | None | object = _LOGGING_DISABLED,
):
    if decision_logger is _LOGGING_DISABLED:
        from .decision_logger import DecisionLogger
        decision_logger = DecisionLogger()  # default-on
    self.decision_logger = decision_logger  # explicit None still disables
```

Simpler alternative (recommended): instantiate by default, leave `None` as the explicit disable:

```python
def __init__(
    self,
    ...,
    decision_logger: DecisionLogger | None = None,
    enable_decision_log: bool = True,  # NEW
):
    if decision_logger is None and enable_decision_log:
        decision_logger = DecisionLogger()
    self.decision_logger = decision_logger
```

Tests passing `decision_logger=None` (e.g., `test_engine_works_without_logger` at `test_engine.py:177-189`) get a real logger writing to `AI_LOG_DIR/decision_log.jsonl` — they'd need to pass `enable_decision_log=False` to preserve the no-write semantics. That's a 1-line test edit and the **right** default for production safety.

2. **Add a production entry-point script** that constructs the engine and runs the loop:

```python
# python/ai/__main__.py  (or python/scripts/run_engine.py)
"""Production entry point: run the AI engine loop with decision logging on."""
import logging
import time
from .engine import AIEngine
from .decision_logger import DecisionLogger
from ..config import PAPER_TRADING_INTERVAL_SECONDS  # reuse for now

logging.basicConfig(level=logging.INFO)

def main():
    engine = AIEngine()  # uses defaults; decision_logger=DecisionLogger() auto-injected
    while True:
        engine.run_once()
        time.sleep(PAPER_TRADING_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
```

Optionally wire into `deploy/start-dashboard.ps1` as a separate `Start-Process python -ArgumentList "-m", "python.ai", ...` block — closes G8 partially. **Flag G8 as out-of-scope per phase brief; leave the wire-up for v1.1 unless trivially co-fixed.**

Recommendation: **do part (1) — default-on** — that closes G5 by itself. Part (2) is optional v1.0 inclusion; document the gap clearly in SUMMARY if deferred.

#### Files to modify

- `python/ai/engine.py:25-37` — change init signature, add default-on instantiation.
- `python/tests/ai/test_engine.py:177-189` (`test_engine_works_without_logger`) — pass `enable_decision_log=False` to preserve semantics. Existing tests at lines 129-175 (`test_engine_logs_decision_when_logger_provided`, `test_engine_passes_features_to_logger`) already pass an explicit `mock_logger`, so unaffected.
- `python/ai/__main__.py` (NEW, optional for G5 minimum, required if also closing G8) — entry-point script.
- `deploy/start-dashboard.ps1` (optional, G8 territory) — add engine launch block.

#### Files to read first

- `python/ai/decision_logger.py:23-27` — `DecisionLogger.__init__` calls `mkdir(parents=True, exist_ok=True)` so default instantiation is safe even if the log dir doesn't exist.
- `python/validation/paper_trading.py:32-37` — example of an "engine-receiving" service object pattern. Mirror for `__main__`.
- `python/tests/ai/test_engine.py:192-199` `test_existing_engine_tests_still_pass` — currently asserts `engine.decision_logger is None`. **This test must update** to assert `isinstance(engine.decision_logger, DecisionLogger)` after default-on flip.

#### Validation strategy

In `python/tests/integration/test_decision_log_contract.py` (same file as G2's tests):

- `test_engine_default_constructs_decision_logger` — `engine = AIEngine()`; assert `isinstance(engine.decision_logger, DecisionLogger)`.
- `test_engine_with_logging_disabled` — `engine = AIEngine(enable_decision_log=False)`; assert `engine.decision_logger is None`.
- `test_engine_run_once_writes_decisions` — mock MT5/features, call `engine.run_once()`, assert `(AI_LOG_DIR / "decision_log.jsonl").exists()` AND contains the symbol(s) evaluated. This is the end-to-end producer-side smoke test.

#### Risks/landmines

- **`test_engine_works_without_logger` (line 177-189)** currently checks the *opposite* of the new default. Updating it is correct, but read the assertion carefully — the test doesn't actually verify "no log file is created," it just verifies "no crash." After the flip, no behavioral change is being missed.
- **`test_existing_engine_tests_still_pass` (line 192-199)** asserts `engine.decision_logger is None` — this assertion **inverts** under the new default. Replace with `isinstance(engine.decision_logger, DecisionLogger)`.
- **First-run side effect:** instantiating `DecisionLogger()` calls `mkdir(parents=True, exist_ok=True)` on `AI_LOG_DIR` — creates `<repo>/logs/ai/` on first import. This is benign but worth noting in 05-SUMMARY.md.
- **G2 must be fixed first** — otherwise default-on still writes to a path the dashboard can't read.
- **G8 deferral risk** — with G5 alone, the operator still has to manually `python -m python.ai` to run the engine. F1 and F3 flows remain undocumented. Acceptable for v1.0 per phase brief, but should be explicit in 05-SUMMARY.md → "Known gap: production AI engine orchestration not yet automated; operators run by hand or via systemd/Task Scheduler of their choice."

---

### BL-01: ParameterAdapter class-level dict mutation (already partially fixed)

**Affects:** AI-05 (compounds G4)

#### Current state (verified — different from audit claim)

`python/ai/parameter_adapter.py:18-39` defines class-level dicts (`SL_MULTIPLIERS`, `TP_MULTIPLIERS`, `LOT_MULTIPLIERS`).

`python/ai/parameter_adapter.py:54-56` (verified — **fix is in place**):

```python
self.SL_MULTIPLIERS = dict(self.__class__.SL_MULTIPLIERS)
self.TP_MULTIPLIERS = dict(self.__class__.TP_MULTIPLIERS)
self.LOT_MULTIPLIERS = dict(self.__class__.LOT_MULTIPLIERS)
```

Verified via git: commit `2dfd5e1` (`fix(02-ai-engine): resolve code review findings (BL-01, WR-01..05, IN-01..02)`) introduced these lines on 2026-05-26. The audit (2026-05-28) reports BL-01 as unfixed — **this is a stale audit claim**.

`python/ai/strategy_manager.py:155-160` (verified — uses `.update()` but on instance dicts):

```python
if "sl_multipliers" in par:
    adapter.SL_MULTIPLIERS.update(par["sl_multipliers"])
if "tp_multipliers" in par:
    adapter.TP_MULTIPLIERS.update(par["tp_multipliers"])
if "lot_multipliers" in par:
    adapter.LOT_MULTIPLIERS.update(par["lot_multipliers"])
```

Because `__init__` now shadows the class attributes with instance attributes (via `self.SL_MULTIPLIERS = dict(...)`), `adapter.SL_MULTIPLIERS.update(...)` mutates only the instance dict, not the class dict. The bug is closed.

**However**, no regression test exists. The Phase 2 02-REVIEW.md test list (line 287) explicitly calls out the missing edge case: *"Strategy application with multiple independent adapter instances (BL-01)"*. Verified by grepping the test directory — no `cross.contamin|multiple.adapter|instance.level` test exists in `python/tests/`.

The audit lists BL-01 as unfixed because the code review report itself was not updated after the commit. The fix is real; the verification is missing.

#### Recommended fix

**No code change.** **Add regression test coverage** in `python/tests/ai/test_parameter_adapter.py` AND `python/tests/ai/test_strategy_manager.py`:

#### Files to modify

- `python/tests/ai/test_parameter_adapter.py` — add test:

```python
def test_instance_multipliers_are_independent():
    """Regression for BL-01: applying multiplier overrides to one adapter must
    NOT affect another. Class-level dicts must be shadowed by instance-level
    copies in __init__."""
    a1 = ParameterAdapter()
    a2 = ParameterAdapter()
    a1.SL_MULTIPLIERS.update({"trending": 99.0})
    assert a1.SL_MULTIPLIERS["trending"] == 99.0
    assert a2.SL_MULTIPLIERS["trending"] == 1.0, "Cross-contamination via class dict"
    assert ParameterAdapter.SL_MULTIPLIERS["trending"] == 1.0, "Class dict mutated"
```

Repeat for `TP_MULTIPLIERS` and `LOT_MULTIPLIERS`. Optionally one combined test.

- `python/tests/ai/test_strategy_manager.py` — add the end-to-end test the 02-REVIEW.md called out:

```python
def test_apply_strategy_does_not_cross_contaminate(manager, tmp_path):
    """Regression for BL-01: applying a strategy to adapter A must not
    affect adapter B's multipliers."""
    detector = RegimeDetector()
    adapter_a = ParameterAdapter()
    adapter_b = ParameterAdapter()
    
    # Export with custom multipliers
    custom_adapter = ParameterAdapter()
    custom_adapter.LOT_MULTIPLIERS["trending"] = 0.01
    path = manager.export_strategy(detector, custom_adapter,
                                    filepath=tmp_path / "test.json")
    strategy = manager.import_strategy(path)
    
    # Apply only to adapter_a
    manager.apply_strategy(detector, adapter_a, strategy)
    
    assert adapter_a.LOT_MULTIPLIERS["trending"] == 0.01
    assert adapter_b.LOT_MULTIPLIERS["trending"] == 1.0, "BL-01 regression"
```

#### Files to read first

- `.planning/phases/02-ai-engine/02-REVIEW.md:53-93` — original BL-01 proof-of-concept. Reuse the assertion structure.
- `python/ai/parameter_adapter.py:54-56` — confirm the instance-level copy is still in place when the test is written (paranoia — the fix could be silently removed by another refactor).
- `python/tests/ai/test_strategy_manager.py:124-135` — existing `test_apply_strategy_modifies_instances` is the nearest existing test. Copy structure.

#### Validation strategy

The two tests above are themselves the validation. Both run in the existing unit test suite — no integration test needed.

#### Risks/landmines

- **The fix is fragile to future refactors.** If someone "cleans up" the `__init__` and removes the three `dict(...)` lines, the test catches it. Without the test, the regression returns silently.
- **The audit will need to be updated** — when /gsd-complete-milestone runs, the BL-01 line item should move from "unfixed" to "fixed in 2dfd5e1, regression-tested in Phase 5."
- **No interaction with G4** — G4's env-var rename doesn't touch the multiplier code path. They're truly independent fixes despite sharing the same `strategy_manager.py` file.

---

## Sequencing

Plans must execute in this order because of shared files and contract dependencies.

### Wave A — Config and contract foundation (must come first)

Goal: lock the canonical names and paths before anything that depends on them.

1. **G3 fix:** Remove duplicate `AI_LOG_DIR` in `python/config.py`. Update to project-root-relative default.
2. **G4 fix (config side):** Delete `AI_STRATEGY_DIR` from `python/config.py`. Move `STRATEGY_CONFIG_DIR` definition next to other path constants with project-root-relative default.
3. **G1 contract decision lock:** Write the canonical schema document into the plan itself (the JSON shape above) so all subsequent waves work against one target.

**Files touched:** `python/config.py` only. ~5 line changes. Verifiable by import smoke test: `python -c "from python.config import AI_LOG_DIR, STRATEGY_CONFIG_DIR; print(AI_LOG_DIR, STRATEGY_CONFIG_DIR)"`.

### Wave B — Producer-side and consumer-side rewrites (parallel within wave)

Goal: change every file affected by a single gap, with mechanical updates only.

**Wave B is parallel-safe within itself** — no two tasks touch the same file. Order within the wave does not matter.

4. **G1 fix (producer):** Update `ea/include/Logger.mqh` and call sites in `OrderManager.mqh` and `PositionManager.mqh`. Fix the position-ticket bug in `PositionManager.mqh:72`. *(File set: 3 MQL5 files. No Python overlap.)*
5. **G2 fix (producer + consumer):** Update `python/ai/decision_logger.py` (single-file mode + `timeframe` field) and `python/ai/engine.py` (pass `timeframe`). *(File set: `decision_logger.py`, `engine.py`. No overlap with strategy work.)*
6. **G4 fix (producer-side import):** Update `python/ai/strategy_manager.py:9, 32` to import `STRATEGY_CONFIG_DIR`. *(File set: `strategy_manager.py` only.)*
7. **G5 fix:** Update `python/ai/engine.py:25-37` to default-on the logger. **CONFLICTS WITH STEP 5** — both touch `engine.py`. Merge into a single task that does G2 + G5 in `engine.py` together. *(After merge: file set = `engine.py`, `decision_logger.py`.)*
8. **G7 fix (optional, low cost):** Update `python/dashboard/api/equity.py` to read `FUTRA_INITIAL_BALANCE` from config instead of hardcoded `10000.0`. *(File set: `equity.py`. No conflict.)*

**Effective parallel groups in Wave B:**
- Group B1: G1 EA-side (3 MQL5 files) — independent
- Group B2: G2 + G5 merged (`engine.py`, `decision_logger.py`) — independent of B1, B3
- Group B3: G4 producer (`strategy_manager.py`) — independent
- Group B4: G7 (`equity.py`) — independent

### Wave C — Test coverage and regression locks (after B)

Goal: prove every fix, lock against regression, supersede fabricated fixtures.

9. **G1 tests:** Replace fixtures in `test_trades.py`, `test_equity.py`. Create `tests/integration/test_trade_log_contract.py`.
10. **G2 tests:** Update `test_decision_logger.py` to pass `timeframe`. Create `tests/integration/test_decision_log_contract.py` (which also covers G5's default-on test).
11. **G3 tests:** Create `tests/integration/test_config_no_duplicates.py`.
12. **G4 tests:** Update `test_strategy_manager.py` if needed. Create `tests/integration/test_strategy_contract.py`.
13. **BL-01 tests:** Add regression tests to `test_parameter_adapter.py` and `test_strategy_manager.py`.

Wave C can run in any order — tests are independent. Recommend bundling by gap (one task per gap) for clean SUMMARY traceability.

### Dependency graph

```
[Wave A: G3, G4-config]
       │
       ├─► [Wave B1: G1 EA-side]            ─┐
       ├─► [Wave B2: G2+G5 merged]          ─┼─► [Wave C: all tests]
       ├─► [Wave B3: G4 producer]           ─┤
       └─► [Wave B4: G7 (optional)]         ─┘

[BL-01 tests] — independent, can run any time (Wave A or C)
```

### Why this order

- **Wave A first** because every downstream import in Wave B references the canonical constants. Doing them out of order means double-edits in B.
- **G2 + G5 merge** because both edit `engine.py`. Separating them creates merge conflicts even in a serial workflow.
- **Wave C last** because the tests assert against the *fixed* shapes; running them earlier means writing assertions twice.
- **G1 EA-side is parallel-isolated** in MQL5 — Python work in B2/B3 cannot touch `ea/include/*`, so no conflict.

### Out-of-scope per phase brief

- **G6** (MT5_DEMO_* in `.env.example`) — trivially co-fixable in Wave A (just add 3 lines to `.env.example`). Recommend inclusion as a 1-task addition; flag explicitly.
- **G8** (production orchestration script) — explicitly deferred. G5 fix gives operators a default-on logger; running the engine remains manual. Document in 05-SUMMARY.md.
- **Phase 3 CR-01, Phase 4 CR-03, CR-04, WR-02, etc.** — explicitly deferred to v1.1 per phase brief. Do not include.
- **Phase 1 + Phase 2 VERIFICATION.md backfill** — separate `/gsd-verify-work 01` and `/gsd-verify-work 02` workflows. Not a Phase 5 deliverable.

## Common Pitfalls

### Pitfall 1: Reader-side schema fix instead of producer-side (G1)

**What goes wrong:** Plan rewrites `trades.py` to handle the flat EA schema, leaving the EA emitter unchanged.
**Why it happens:** Python is "easier" to edit than MQL5. Confirmation bias toward dashboard-side changes.
**How to avoid:** The phase brief and this research are explicit — **producer (EA) moves**. The dashboard reader is the canonical schema target. Trace every plan task back to "does this update the EA Logger.mqh or its call sites?" — if no plan task covers EA changes, the plan is wrong.
**Warning signs:** Plan has zero MQL5 file edits. Plan introduces a "schema translation" module.

### Pitfall 2: Fixing G2 without G5 (or vice versa)

**What goes wrong:** Decision log filename is fixed but `AIEngine` is never wired with a logger in production, so the file never gets written. Or the engine defaults to logging-on but writes to the wrong filename.
**Why it happens:** They look independent. They are not — G2 + G5 together close DASH-03/AI-04; either alone is half a fix.
**How to avoid:** Plan must explicitly tie G2 + G5 (both edit `engine.py`) into one work unit. Integration test must exercise the full chain: AIEngine instantiation → DecisionLogger writes → DECISION_LOG_PATH file → `api/decisions.py` returns the row.

### Pitfall 3: Missing `timeframe` field in DecisionLogger record

**What goes wrong:** G2 closes the filename gap, but the dashboard reader still 500s because `Decision.timeframe` is required by Pydantic and the writer doesn't emit it.
**Why it happens:** The audit doesn't call out this sub-gap. It's only visible by reading `dashboard/models.py` and `decision_logger.py` side-by-side.
**How to avoid:** Plan task for G2 must include "add `timeframe` parameter to `log_decision` and propagate through engine." Test must round-trip through Pydantic model.
**Warning signs:** Production `/api/decisions` returns 500 with `ValidationError: timeframe field required`.

### Pitfall 4: Position-ticket vs. order-ticket conflation (G1)

**What goes wrong:** EA close emits `logEntry.ticket = result.order` (the closing order's ticket), but the trade open was logged with the position's ticket. `trades.py:37-40` joins on ticket — no match, no closed-trades displayed.
**Why it happens:** MQL5 uses the same `ticket` name for both order and position objects. Easy to use the wrong one.
**How to avoid:** Explicit fix in `PositionManager.mqh:72` — `logEntry.ticket = ticket` (the position ticket passed into `ClosePosition`). Integration test must include an open + close with the same ticket and assert pairing.

### Pitfall 5: CWD-relative path defaults silently diverge (G3, G4)

**What goes wrong:** `AI_LOG_DIR = Path("logs/ai")` resolves relative to the launching process's CWD. AI engine launched from `python/` writes to `python/logs/ai/`; dashboard launched from project root reads from `./logs/ai/`. Both create files; neither sees the other.
**Why it happens:** Phase 4 author used CWD-relative defaults for brevity. Phase 2 used project-root-relative. Inconsistent.
**How to avoid:** All path constants in `config.py` use `Path(__file__).parent.parent / "..."` pattern. Same as existing `IPC_DIR` on line 18. Lock this in a `test_config_no_cwd_relative_paths` regression test.

### Pitfall 6: Treating BL-01 as "fix and forget" without test coverage

**What goes wrong:** Plan does nothing on BL-01 because "it's already fixed." A future refactor of `ParameterAdapter.__init__` silently removes the instance-dict copy. Cross-contamination returns. No test catches it.
**Why it happens:** Verified fixes without test coverage are invisible to the next reviewer.
**How to avoid:** Plan must include a BL-01 regression test task in Wave C. The test from 02-REVIEW.md (lines 60-69) is the template.

## Project Constraints (from CLAUDE.md)

**None** — verified by absence: `./CLAUDE.md` does not exist in the project root. No project-specific directives override default behavior. The only relevant directive surfaces from `PROJECT.md:58`:

- **TDD constraint:** *"all code must be built with tests first and must be testable locally."* This phase satisfies it by treating Wave C (test additions) as a hard gate on completion. Every code change in Wave A/B must have a corresponding test in Wave C — no exceptions.

## Code Examples

### Example: EA-side `LogTradeClose` (G1 producer fix)

Source: derived from `Logger.mqh:27-56` and `PositionManager.mqh:13-92`.

```mql5
// New in Logger.mqh
void LogTradeClose(TradeResult &result, double profit)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"event\":\"trade_close\",\"ticket\":%I64u,\"symbol\":\"%s\","
      "\"direction\":\"%s\",\"volume\":%.2f,\"close_price\":%.5f,"
      "\"profit\":%.2f,\"retcode\":%d,\"comment\":\"%s\",\"timestamp\":\"%s\"}",
      result.ticket, result.symbol, result.type,
      result.volume, result.price, profit,
      result.retcode, result.comment, timestamp
   );
   // ... append to TRADE_LOG_FILE (same FileOpen/FileSeek/FileWrite/FileClose pattern as existing LogTrade)
}

// Updated call in PositionManager.mqh:70-82
double profitAtClose = PositionGetDouble(POSITION_PROFIT);  // BEFORE OrderSend
// ... existing OrderSend code ...
TradeResult logEntry;
ZeroMemory(logEntry);
logEntry.ticket    = ticket;          // FIX: position ticket, not result.order
logEntry.symbol    = symbol;
logEntry.type      = (posType == POSITION_TYPE_BUY) ? "buy" : "sell";  // FIX: position direction, not closing order's
logEntry.volume    = volume;
logEntry.price     = result.price;    // execution price of the close
logEntry.retcode   = result.retcode;
logEntry.comment   = "Position closed";
logEntry.timestamp = TimeCurrent();
LogTradeClose(logEntry, profitAtClose);
```

### Example: DecisionLogger single-file mode (G2 fix)

Source: derived from `decision_logger.py:23-35, 130-142`.

```python
class DecisionLogger:
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or AI_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "decision_log.jsonl"   # NEW — constant path
        # DELETED: self._current_date, self._file_path

    # DELETED: _get_log_path()

    def log_decision(
        self,
        symbol: str,
        timeframe: str,                    # NEW — required, no default
        regime: str,
        confidence: float,
        ...
    ) -> Path:
        ...
        record = {
            "timestamp": timestamp,
            "symbol": symbol,
            "timeframe": timeframe,        # NEW
            "regime": regime,
            ...
        }
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as e:
            logger.error(f"Failed to write decision log: {e}")
        return self.log_path
```

### Example: AIEngine default-on logger (G5 fix)

Source: derived from `engine.py:25-37`.

```python
def __init__(
    self,
    symbols: list[str] | None = None,
    timeframe: str = AI_DEFAULT_TIMEFRAME,
    regime_detector: RegimeDetector | None = None,
    parameter_adapter: ParameterAdapter | None = None,
    decision_logger: DecisionLogger | None = None,
    enable_decision_log: bool = True,       # NEW
):
    self.symbols = symbols or DEFAULT_SYMBOLS
    self.timeframe = timeframe
    self.detector = regime_detector or RegimeDetector()
    self.adapter = parameter_adapter or ParameterAdapter()
    if decision_logger is None and enable_decision_log:
        decision_logger = DecisionLogger()  # default-on for production
    self.decision_logger = decision_logger
    self.logger = logging.getLogger(__name__)
```

### Example: BL-01 regression test

Source: derived from `02-REVIEW.md:60-69` (the proof-of-concept).

```python
# python/tests/ai/test_parameter_adapter.py
def test_instance_multipliers_independent():
    """BL-01 regression: instance-level dict copies must shadow class dicts."""
    a1 = ParameterAdapter()
    a2 = ParameterAdapter()
    a1.SL_MULTIPLIERS.update({"trending": 99.0})
    assert a1.SL_MULTIPLIERS["trending"] == 99.0
    assert a2.SL_MULTIPLIERS["trending"] == 1.0
    assert ParameterAdapter.SL_MULTIPLIERS["trending"] == 1.0
    # Repeat for TP_MULTIPLIERS, LOT_MULTIPLIERS
```

## State of the Art

| Old Approach (pre-Phase 5) | Current Approach (post-Phase 5) | When Changed | Impact |
|-----------------------------|----------------------------------|--------------|--------|
| EA emits flat `TradeResult` JSONL; dashboard guesses at event types | EA emits event-typed JSONL matching dashboard reader expectations | Phase 5 G1 | DASH-02 / DASH-04 / DATA-08 actually work |
| Daily-rotated `ai_decisions_YYYY-MM-DD.jsonl` | Single `decision_log.jsonl` | Phase 5 G2 | DASH-03 reader works; supersedes Phase 2 design decision |
| Two `AI_LOG_DIR` definitions (line 47 + line 109) | One canonical project-root-relative `AI_LOG_DIR` | Phase 5 G3 | Phase 4 WR-05 closed |
| `AI_STRATEGY_DIR` (writer) + `STRATEGY_CONFIG_DIR` (reader) | Single `STRATEGY_CONFIG_DIR` | Phase 5 G4 | AI-05 writer/reader symmetric; `.env.example` consistent |
| `AIEngine(decision_logger=None)` default | `AIEngine(enable_decision_log=True)` default | Phase 5 G5 | Decision log written by default in production |
| `ParameterAdapter` class-level dicts mutated via `.update()` | Instance-level dict copies in `__init__` (existing fix in 2dfd5e1) | Phase 2 commit `2dfd5e1`, regression-tested in Phase 5 | A/B testing is actually safe |

**Deprecated/outdated:**
- `LogTrade(TradeResult&)` single-entry-point in `Logger.mqh` — replaced by event-specific functions (`LogTradeOpen`, `LogTradeClose`, optionally `LogTradeModify`).
- `_get_log_path()` daily rotation method in `DecisionLogger` — removed; constant path used instead.
- `AI_STRATEGY_DIR` constant and `FUTRA_AI_STRATEGY_DIR` env var — removed; merged into `STRATEGY_CONFIG_DIR` / `FUTRA_STRATEGY_CONFIG_DIR`.
- Fabricated `{"event": "trade_open"}` test fixtures in Phase 4 tests — replaced by EA-shape-derived fixtures or integration tests.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Operator running v1.0 has no existing `trade_log.jsonl` data they need preserved [ASSUMED — true for pre-shipment but worth confirming] | G1 Runtime State Inventory | Low — v1.0 hasn't shipped; only dev/test data on disk. If wrong, the plan needs a one-time data migration step. |
| A2 | `PositionGetDouble(POSITION_PROFIT)` read BEFORE the closing `OrderSend` returns the floating P&L of the position about to close [ASSUMED — based on MT5 documentation knowledge, not tested in this session] | G1 risks | Medium — if MT5 semantics differ, `profit` is 0 or stale. Mitigation: have the EA test on demo MT5 emit known-profit closes and grep `trade_log.jsonl`. |
| A3 | Daily rotation has no downstream consumers other than the broken dashboard reader [VERIFIED — grepped for `ai_decisions_` in codebase, only producer-side references found] | G2 recommendation | Low — verified. |
| A4 | Operator has not explicitly set `FUTRA_AI_STRATEGY_DIR` in any production environment [ASSUMED — v1.0 hasn't shipped] | G4 recommendation | Low — pre-shipment. If wrong, document the rename in the v1.0 release notes. |
| A5 | `DecisionLogger()` default-on does not introduce noticeable I/O latency in the AIEngine loop [ASSUMED — each cycle writes one JSON line per symbol, well under 1ms] | G5 recommendation | Very low — single file append per cycle. If wrong, switch to background-thread logging in v1.1. |
| A6 | BL-01 fix at `parameter_adapter.py:54-56` survives all current Phase 2 tests (no test asserts the OLD class-level-dict behavior) [VERIFIED — 50 AI tests pass on current head] | BL-01 | None — verified. |
| A7 | The audit's "BL-01 unfixed" claim is stale (the audit was authored 2026-05-28; the fix is in commit 2dfd5e1 from 2026-05-26) [VERIFIED — `git blame` confirms] | BL-01 | None — verified. |
| A8 | Pydantic `Decision` model uses default-permissive extras handling (extra fields in the writer record are silently dropped) [ASSUMED — standard Pydantic v1/v2 default, not explicitly tested] | G2 sub-gap | Low — if Pydantic config has `extra="forbid"`, any extra writer field 500s. Mitigation: explicit reader-side `Decision.model_validate(entry, strict=False)` or matching the writer record exactly to the model. |
| A9 | Phase 5 will not introduce VERIFICATION.md backfill for phases 1 and 2 — those are separate `/gsd-verify-work` workflows [VERIFIED — phase brief explicit] | Out of scope | None — verified. |

**Confirm-before-execution items (from this log):** A2 (MT5 POSITION_PROFIT timing) — recommend that the planner add a "manual gate" test step where the operator runs the recompiled EA on demo MT5 and confirms a known-profit close lands in `trade_log.jsonl` with the right `profit` field. A8 (Pydantic extras) — planner should add an explicit `assert response.status_code == 200` integration test against a writer-emitted record to surface this if it bites.

## Open Questions

1. **Should `trade_modify` events be filtered out of `trade_log.jsonl` entirely, or emitted as informational rows?**
   - What we know: `trades.py:36-40` filters by `event ∈ {trade_open, trade_close}`. Modify rows are silently ignored — current correct behavior.
   - What's unclear: operators may want to grep modify events for SL/TP adjustment debugging.
   - Recommendation: keep emitting `trade_modify` rows (with `event: "trade_modify"`); dashboard ignores them. Cost is one extra line per modify, benefit is unchanged operator workflow.

2. **Should `LogError` rows also gain an `event: "error"` field for filter symmetry?**
   - What we know: Phase 4 readers don't filter on errors today. Errors are emitted on the same `trade_log.jsonl` file (Logger.mqh:61-85).
   - What's unclear: future dashboards may want an error-row endpoint.
   - Recommendation: add `event: "error"` for forward-compatibility. Zero cost, prevents future contract mismatch.

3. **Is the audit's `WR-05` (Phase 4) the same as G3, and does closing G3 close WR-05?**
   - What we know: WR-05 (04-REVIEW.md:286-300) is verbatim G3. Yes, closing G3 closes WR-05.
   - Recommendation: have `/gsd-complete-milestone v1.0` mark both as closed; no separate fix needed.

4. **Should G5's `enable_decision_log: bool` parameter default to True (recommended) or be a global env-var flag (`FUTRA_AI_LOG_ENABLED`)?**
   - What we know: Test code (`test_engine_works_without_logger`) explicitly tests the None path.
   - What's unclear: which production operator preference. Phase 1 / 2 docs don't address this.
   - Recommendation: bool parameter default-True. Env var is over-engineering for v1.0; if a future operator wants global disable, add it in v1.1 without API change (just intercept in __init__).

5. **Does the planner want to include G7 (FUTRA_INITIAL_BALANCE wiring) in Phase 5 or defer to v1.1?**
   - What we know: Audit flags G7 as warning, not blocker. Fix is ~5 lines in `equity.py`. Phase brief says "Optional inclusion if low-cost; flag explicitly."
   - Recommendation: include in Wave B as task B4. Low cost, closes a documented gap, no risk of scope creep.

6. **Does the planner want to include G6 (MT5_DEMO_* in `.env.example`) in Phase 5?**
   - What we know: 3-line addition to `.env.example`. No code change.
   - Recommendation: include as a Wave A trailing micro-task. Closes BACK-05 partial → satisfied.

## Sources

### Primary (HIGH confidence)
- `ea/include/Logger.mqh:1-115` (read at full)
- `ea/include/Common.mqh:1-66` (read at full — TradeResult struct definition, IPC constants)
- `ea/include/OrderManager.mqh:1-200` (read at full — both LogTrade call sites)
- `ea/include/PositionManager.mqh:1-220` (read at full — LogTrade call sites, position-ticket bug)
- `python/ai/decision_logger.py:1-153` (read at full)
- `python/ai/engine.py:1-129` (read at full)
- `python/ai/strategy_manager.py:1-164` (read at full)
- `python/ai/parameter_adapter.py:1-144` (read at full — BL-01 fix verified at lines 54-56)
- `python/config.py:1-124` (read at full — G3 + G4 duplicate verified)
- `python/dashboard/api/trades.py:1-86` (read at full)
- `python/dashboard/api/equity.py:1-101` (read at full)
- `python/dashboard/api/decisions.py:1-55` (read at full)
- `python/dashboard/api/strategy.py:1-37` (read at full)
- `python/dashboard/models.py:1-84` (read at full — timeframe required field verified at line 54)
- `python/dashboard/main.py:1-101` (read at full — routes registration)
- `python/dashboard/api/__init__.py:1-103` (read at full — daily_pnl hardcoded at line 68)
- `python/tests/ai/test_decision_logger.py:1-110` (read at full)
- `python/tests/ai/test_strategy_manager.py:1-136` (read at full — BL-01 test gap confirmed)
- `python/tests/ai/test_engine.py:1-200` (read at full — G5 test inversions identified)
- `python/tests/dashboard/test_trades.py:1-133` (read at full — fabricated fixtures verified)
- `python/tests/dashboard/test_decisions.py:1-90` (read at full — fabricated fixtures verified)
- `python/tests/dashboard/test_equity.py:1-121` (read at full — CR-02 regression test verified)
- `python/tests/dashboard/conftest.py:1-70` (read at full)
- `python/validation/paper_trading.py:1-147` (read at full)
- `python/ipc/ipc_writer.py:1-50` (read at full — atomic write pattern reference)
- `deploy/start-dashboard.ps1:1-179` (read at full — orchestration scope verified)
- `.env.example:1-51` (read at full)
- `.planning/v1.0-MILESTONE-AUDIT.md:1-334` (read at full — primary contract)
- `.planning/REQUIREMENTS.md:1-137` (read at full)
- `.planning/STATE.md:1-93` (read at full)
- `.planning/ROADMAP.md:1-140` (read at full)
- `.planning/PROJECT.md:1-90` (read at full — TDD constraint surfaced)
- `.planning/phases/02-ai-engine/02-REVIEW.md:1-325` (read at full — BL-01 source-of-truth)
- `.planning/phases/02-ai-engine/02-02-SUMMARY.md:1-62` (read at full — Phase 2 locked decisions)
- `.planning/config.json:1-15` (read at full — `nyquist_validation: false` verified)
- Git history: `git blame python/ai/parameter_adapter.py:54-56` → commit 2dfd5e1 (BL-01 fix authorship)
- Git log: `git log --oneline python/ai/parameter_adapter.py` → 2026-05-26 fix commit before 2026-05-28 audit

### Secondary (MEDIUM confidence)
- Phase 4 04-REVIEW.md and 04-RESEARCH.md referenced via grep results (lines verified but full files not re-read this session — relied on grep -n output for line numbers).
- Phase 4 04-VERIFICATION.md referenced via grep results (verified the existence of WR-05 mention and the post-fix verification claim).

### Tertiary (LOW confidence)
- MQL5 `PositionGetDouble(POSITION_PROFIT)` exact semantics at the moment of position close — based on MQL5 docs knowledge (not re-verified in this session via official MetaQuotes documentation). Flagged in Assumption A2.
- Pydantic v1 vs. v2 extras handling default — assumed permissive (`extra="ignore"`); not verified against the project's pydantic version in `requirements.txt`. Flagged in Assumption A8.

## Metadata

**Confidence breakdown:**
- G1 schema reconciliation: HIGH — full source files read, contract gap mechanically verified.
- G2 filename + timeframe sub-gap: HIGH — both sides verified; Pydantic model verified.
- G3 duplicate AI_LOG_DIR: HIGH — both definitions verified at exact lines.
- G4 strategy env var: HIGH — both env vars verified in code and `.env.example`.
- G5 decision_logger default: HIGH — engine signature and zero production callers verified by grep.
- BL-01: HIGH — fix verified in-place via Read + git blame; audit claim stale.
- Sequencing: HIGH — based on file-overlap analysis.
- Validation strategy: HIGH — integration tests designed against real producers (no MT5 dependency).
- Out-of-scope items: HIGH — phase brief explicit.

**Research date:** 2026-05-29
**Valid until:** Phase 5 completion (no library version dependencies; code-only research is stable).
