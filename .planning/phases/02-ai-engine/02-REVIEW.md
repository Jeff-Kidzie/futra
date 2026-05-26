---
phase: 02-ai-engine
reviewed: 2026-05-26T22:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - python/ai/__init__.py
  - python/ai/features.py
  - python/ai/regime_detector.py
  - python/ai/parameter_adapter.py
  - python/ai/engine.py
  - python/ai/decision_logger.py
  - python/ai/strategy_manager.py
  - python/config.py
  - python/tests/ai/__init__.py
  - python/tests/ai/conftest.py
  - python/tests/ai/test_features.py
  - python/tests/ai/test_regime_detector.py
  - python/tests/ai/test_parameter_adapter.py
  - python/tests/ai/test_engine.py
  - python/tests/ai/test_decision_logger.py
  - python/tests/ai/test_strategy_manager.py
  - .planning/phases/02-ai-engine/02-01-SUMMARY.md
  - .planning/phases/02-ai-engine/02-02-SUMMARY.md
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 02: AI Engine Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 18 (12 source/test + 2 config + 2 SUMMARY + 2 init)
**Tests:** 50 passed, 0 failed
**Status:** issues_found — 1 BLOCKER, 5 WARNING, 4 INFO

## Summary

Phase 2 delivers a well-structured AI engine with regime detection, parameter adaptation, decision logging, and strategy management. All 50 tests pass. The implementation follows TDD discipline and the architecture is clean with good separation of concerns.

However, one **BLOCKER** was found: `StrategyManager.apply_strategy()` mutates class-level multiplier dictionaries on `ParameterAdapter`, causing cross-contamination across all adapter instances globally. This must be fixed before shipping.

Additionally, there are five warnings covering NaN handling in the regime detector, NaN-to-None conversion gaps in the engine, dead config constants, JPY pip approximation issues, and an incomplete round-trip test.

---

## Blockers

### BL-01: StrategyManager.apply_strategy() mutates class-level dicts — cross-contamination across all ParameterAdapter instances

**File:** `python/ai/strategy_manager.py:156-160`
**Severity:** BLOCKER
**Issue:** `apply_strategy()` calls `adapter.SL_MULTIPLIERS.update()`, `adapter.TP_MULTIPLIERS.update()`, and `adapter.LOT_MULTIPLIERS.update()`. These dictionaries are defined as **class-level** attributes on `ParameterAdapter` (lines 18-39 of `parameter_adapter.py`), not instance-level. Since `dict.update()` mutates in-place, applying a strategy to one adapter instance permanently changes the multiplier defaults for **all** ParameterAdapter instances — past, present, and future.

**Proof of concept:**
```python
a1 = ParameterAdapter()
a2 = ParameterAdapter()

# Apply strategy that overrides trending lot multiplier
mgr.apply_strategy(None, a1, {
    "parameter_adapter": {"lot_multipliers": {"trending": 0.01}, ...}
})
# a2 is now corrupted:
assert a2.LOT_MULTIPLIERS["trending"] == 0.01  # FAILS — actually 0.01!
```

**Fix:** Copy the class dict into an instance-level dict before mutating, or create a deep copy and assign to the instance attribute:

```python
# In ParameterAdapter.__init__() — make instance-level copies of class dicts:
self.SL_MULTIPLIERS = dict(self.__class__.SL_MULTIPLIERS)
self.TP_MULTIPLIERS = dict(self.__class__.TP_MULTIPLIERS)
self.LOT_MULTIPLIERS = dict(self.__class__.LOT_MULTIPLIERS)
```

Alternative fix in `strategy_manager.py:apply_strategy()` — copy before update:

```python
if "sl_multipliers" in par:
    adapter.SL_MULTIPLIERS = {**adapter.SL_MULTIPLIERS, **par["sl_multipliers"]}
if "tp_multipliers" in par:
    adapter.TP_MULTIPLIERS = {**adapter.TP_MULTIPLIERS, **par["tp_multipliers"]}
if "lot_multipliers" in par:
    adapter.LOT_MULTIPLIERS = {**adapter.LOT_MULTIPLIERS, **par["lot_multipliers"]}
```

**Impact:** Multiple engine instances with different strategy configurations will silently share the same multiplier values. Last-applied strategy wins. This breaks the A/B testing use case described in AI-05.

---

## Warnings

### WR-01: RegimeDetector volatile regime confidence relies on implementation-defined NaN behavior

**File:** `python/ai/regime_detector.py:74-75`
**Severity:** WARNING
**Issue:** When `volatility_20` is NaN but `bb_width_pct` triggers the volatile regime, the confidence formula uses NaN arithmetic:

```python
confidence = min(0.9, 0.6 + min((vol - self.vol_high) * 2.0, 0.3))
```

`(NaN - 0.25) * 2.0` = NaN, `min(NaN, 0.3)` is implementation-defined (Python docs: "the result for min() and max() is implementation-defined"), producing NaN on many runtimes. While CPython 3.13 coincidentally yields 0.9 from `min(0.9, 0.6 + NaN)`, the confidence calculation does not correctly factor in `bb_width_pct` as a volatility signal — it's meaningless arithmetic on NaN that happens not to crash.

**Fix:** Keep NaN out of the confidence calculation. Use available data:

```python
# VOLATILE: confidence derived from whichever signal is valid
vol_contrib = 0.0
if not pd.isna(vol):
    vol_contrib = min((vol - self.vol_high) * 2.0, 0.3)
bb_contrib = 0.0
if not pd.isna(bb):
    bb_contrib = min((bb - self.bb_high) / self.bb_high, 0.3)
confidence = min(0.9, 0.6 + max(vol_contrib, bb_contrib))
```

**Impact:** On non-CPython runtimes (PyPy, future CPython), confidence may be NaN instead of a valid float. Even on CPython, the confidence value 0.9 does not meaningfully reflect the degree of volatility indicated by `bb_width_pct`.

---

### WR-02: AIEngine passes NaN values to ParameterAdapter.adapt() instead of None

**File:** `python/ai/engine.py:55-56`
**Severity:** WARNING
**Issue:** The engine extracts volatility and ATR with `.get(key, None)`, which returns `None` only when the key is *absent*. When `compute_features()` returns NaN for a feature (e.g., partial data edge cases), the key exists with value `float("nan")`, and `.get()` returns NaN — not None.

```python
volatility = features.get("volatility_20", None)  # → NaN, not None!
atr_pips = features.get("atr_14", None)           # → NaN, not None!
```

The adapter's type contract (`volatility: float | None`) expects `None` for missing data. Passing NaN violates this contract. Currently, the adapter handles NaN "safely" because `NaN > 0 is False`, but this is accidental correctness.

**Fix:** Explicitly convert NaN to None:

```python
import pandas as pd

volatility = features.get("volatility_20", None)
if volatility is not None and pd.isna(volatility):
    volatility = None
atr_pips = features.get("atr_14", None)
if atr_pips is not None and pd.isna(atr_pips):
    atr_pips = None
```

**Impact:** Values semantically identical to "missing" are treated as present (NaN ≠ None), which could lead to surprising behavior if adapter logic changes.

---

### WR-03: Engine hardcodes equity and timeframe; AI_DEFAULT_EQUITY and AI_DEFAULT_TIMEFRAME from config are unused

**File:** `python/ai/engine.py:27,64` and `python/config.py:48-49`
**Severity:** WARNING
**Issue:** `config.py` defines `AI_DEFAULT_EQUITY = float(os.getenv("FUTRA_AI_EQUITY", "10000.0"))` and `AI_DEFAULT_TIMEFRAME = os.getenv("FUTRA_AI_TIMEFRAME", "H1")`, but `engine.py` imports only `DEFAULT_SYMBOLS` from config. The engine hardcodes `equity=10000.0` (line 64) and `timeframe="H1"` (line 27 init default). Environment variables `FUTRA_AI_EQUITY` and `FUTRA_AI_TIMEFRAME` have no effect on the AI engine.

**Fix:** Import and use the config constants:

```python
from ..config import DEFAULT_SYMBOLS, AI_DEFAULT_TIMEFRAME, AI_DEFAULT_EQUITY

class AIEngine:
    def __init__(self, ..., timeframe: str = AI_DEFAULT_TIMEFRAME, ...):
        ...
    def evaluate_symbol(self, symbol: str) -> dict | None:
        ...
        adapted = self.adapter.adapt(..., equity=AI_DEFAULT_EQUITY)
```

**Impact:** The env-var-override mechanism documented in config.py is dead code for the engine — users who set `FUTRA_AI_EQUITY` or `FUTRA_AI_TIMEFRAME` get no effect.

---

### WR-04: to_ipc_params() pip-to-percentage conversion inaccurate for JPY pairs

**File:** `python/ai/parameter_adapter.py:127-128`
**Severity:** WARNING
**Issue:** `sl_percent = adapted["sl_pips"] * 0.01` assumes 1 pip ≈ 0.01% of price (true for most non-JPY forex at ~1.0000). For JPY pairs like USDJPY (~150.00), 1 pip ≈ 0.0067% of price — a 33% error. The code comment acknowledges this as "approximation" but provides no mechanism to override per-symbol.

**Fix:** Add a symbol-aware conversion or accept pip value as a parameter:

```python
def to_ipc_params(self, adapted: dict, symbol: str, pip_multiplier: float = 0.01) -> dict:
    sl_percent = adapted["sl_pips"] * pip_multiplier
    tp_percent = adapted["tp_pips"] * pip_multiplier
```

Or auto-detect JPY pairs:

```python
pip_multiplier = 0.001 if "JPY" in symbol.upper() else 0.01
```

**Impact:** SL/TP percentages written to IPC will be ~33% understated for JPY pairs, causing the EA to use tighter stops than intended.

---

### WR-05: Round-trip test does not verify TP and lot_size equality

**File:** `python/tests/ai/test_strategy_manager.py:89-111`
**Severity:** WARNING
**Issue:** `test_round_trip_produces_identical_output` verifies regime, confidence, and `sl_pips` equality after round-trip, but does **not** assert `tp_pips` or `lot_size` equality. The comment on line 111 reads `# sl_pips verified` but the assertion only checks `sl_pips`. A regression in TP or lot sizing multipliers would pass undetected.

**Fix:** Add assertions for TP and lot:

```python
orig_params = adapter.adapt("trending", 0.8, 0.15)
new_params = new_adapter.adapt("trending", 0.8, 0.15)
assert orig_params["sl_pips"] == new_params["sl_pips"]
assert orig_params["tp_pips"] == new_params["tp_pips"]
assert orig_params["lot_size"] == new_params["lot_size"]
```

**Impact:** Test gap — a bug in TP or lot multiplier import/application would pass the existing round-trip test.

---

## Info

### IN-01: IOError is legacy exception name — prefer OSError

**File:** `python/ai/decision_logger.py:149`
**Severity:** INFO
**Issue:** `except IOError as e:` — In Python 3.3+, `IOError` is an alias for `OSError`. While functional, using the canonical `OSError` is clearer and avoids confusion for new developers.

**Fix:**
```python
except OSError as e:
```

---

### IN-02: Empty test package init file

**File:** `python/tests/ai/__init__.py`
**Severity:** INFO
**Issue:** The file is empty (0 bytes). While functionally correct for package discovery, adding a docstring follows project convention (see `python/ai/__init__.py`) and helps with tooling.

**Fix:**
```python
"""Tests for Futra AI Engine — regime detection, parameter adaptation, and feature engineering."""
```

---

### IN-03: Unused config constants

**File:** `python/config.py:48-49`
**Severity:** INFO
**Issue:** `AI_DEFAULT_EQUITY` and `AI_DEFAULT_TIMEFRAME` are defined but never imported or referenced in `python/ai/engine.py` (see WR-03). These are effectively dead code.

**Fix:** Either use them in `engine.py` (recommended — see WR-03 fix) or remove them from config.py.

---

### IN-04: Dead-code division guard in _build_reasoning

**File:** `python/ai/decision_logger.py:61`
**Severity:** INFO
**Issue:** `rr_ratio = tp_pips / sl_pips if sl_pips > 0 else 0` — The `sl_pips > 0` guard is dead code because `ParameterAdapter.adapt()` floors SL at 10.0 pips. The guard is harmless defensive coding, but removes it would eliminate a branch and clarify intent.

**Fix:** Either simplify to `rr_ratio = tp_pips / sl_pips` or keep the guard with a comment noting it's for defense-in-depth against future changes.

---

## Test Quality Assessment

**Coverage:** All 50 tests pass. Tests cover:
- Feature computation (7 tests): keys, ranges, edge cases (NaN degradation, small input, non-mutation)
- Regime detection (8 tests): all 4 regimes, NaN input, statelessness, confidence bounds
- Parameter adaptation (10 tests + 1 bonus): all 4 regime behaviors, low-confidence fallback, equity scaling, ATR/volatility factors, position caps, IPC format
- Engine orchestration (8 tests): full pipeline, error handling, per-symbol isolation, logging integration, backward compatibility
- Decision logging (8 tests): file creation, JSON validity, timestamp format, reasoning quality, append behavior, directory auto-creation, feature snapshot, custom paths
- Strategy management (8 tests): export validity, threshold fidelity, adapter settings, metadata, import, round-trip, validation errors, in-place application

**Edge Cases Tested:** NaN features, low bar counts, missing data, low confidence, extreme equity, empty directories, file-not-found, missing keys.

**Missing Edge Cases:**
1. Volatile regime with NaN volatility + valid bb_width (WR-01)
2. JPY pair pip conversion (WR-04)
3. Round-trip TP/lot equality (WR-05)
4. Strategy application with multiple independent adapter instances (BL-01)
5. Concurrency/locking around log file access (accepted per T-02-07)
6. Very large feature snapshot values (overflow testing)

---

## Plan Deviation Check

| Requirement | Status | Notes |
|---|---|---|
| DEFAULT_LOT_SIZE changed from 0.01 → 0.10 | Documented | Documented in 02-01-SUMMARY.md as intentional (prevents volatile floor nullification) |
| Plan 02-01 listed 29 tests; implemented 30 | Documented | Bonus test `test_to_ipc_params_produces_correct_format` added beyond plan |
| AI_DEFAULT_EQUITY/AI_DEFAULT_TIMEFRAME not used in engine | Undocumented | Defined in config.py but not imported in engine.py — see WR-03 |
| Plan says Mock import`; implementation uses MagicMock | Immaterial | MagicMock is a subclass of Mock, functionally equivalent |
| Plan has DEFAULT_LOT_SIZE = 0.01 in code template | Acceptable | Template in plan doc is reference, not spec — implementation uses 0.10 as corrected |

All must_have truths from both plans are satisfied. No unaddressed deviations.

---

## Security Assessment

| Threat | Status | Notes |
|---|---|---|
| T-02-06: config-injection via strategy JSON | Mitigated | `import_strategy()` validates required keys before apply |
| T-02-07: log tampering | Accepted | JSONL is append-only, no integrity verification |
| T-02-08: information disclosure via logs | Accepted | Logs contain no credentials or PII |
| T-02-09: DoS via log write failure | Mitigated | `IOError` caught; engine continues |
| T-02-10: elevation via strategy import | Mitigated | Path construction uses `pathlib.Path`, no code execution |

No new security vulnerabilities found. All threats from the threat model are addressed. No hardcoded secrets, no eval/exec, no unsafe deserialization.

---

_Reviewed: 2026-05-26T22:00:00Z_
_Reviewer: gsd-code-reviewer (standard depth)_
_Depth: standard_
