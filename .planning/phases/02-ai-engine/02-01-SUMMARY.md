---
phase: 02-ai-engine
plan: 01
subsystem: ai-engine
tags: [ai, regime-detection, parameter-adaptation, tdd]
dependency:
  requires: []
  provides: [regime-detection, adaptive-parameters, ipc-params]
  affects: [02-02]
tech-stack:
  added: [TA-Lib 0.6.8, scikit-learn-ready interface]
  patterns: [TDD RED/GREEN, rule-based ML interface, IPC atomic write]
key-files:
  created:
    - python/ai/__init__.py
    - python/ai/features.py
    - python/ai/regime_detector.py
    - python/ai/parameter_adapter.py
    - python/ai/engine.py
    - python/tests/ai/__init__.py
    - python/tests/ai/conftest.py
    - python/tests/ai/test_features.py
    - python/tests/ai/test_regime_detector.py
    - python/tests/ai/test_parameter_adapter.py
    - python/tests/ai/test_engine.py
decisions:
  - "Default lot size set to 0.10 (not 0.01) so volatile multiplier (0.5x) produces lot below trending — 0.01 floor would nullify the reduction"
  - "Rule-based regime detection chosen over ML per PITFALLS.md #1 — interpretable thresholds, sklearn-compatible interface for later swap-in"
  - "NaN features → safe default (quiet, 0.0) — no garbage classification on insufficient data"
metrics:
  duration: "~15 min"
  completed: "2026-05-26"
  tests: 30 passed (7 features + 8 regime + 11 adapter + 4 engine)
---

# Phase 02 Plan 01: AI Engine Core Summary

**One-liner:** Rule-based regime detection (4 market states) with adaptive SL/TP/position sizing, orchestrated into a per-symbol evaluation pipeline that writes EA-compatible IPC params files.

## What Was Built

**Feature Engineering (`features.py`):** 10 technical indicators computed from OHLCV DataFrames using TA-Lib — ATR, historical volatility, RSI, MACD, ADX, SMA ratio, Bollinger Band width, close-to-SMA distance, volume ratio. Graceful NaN degradation for DataFrames with < 50 bars.

**Regime Detector (`regime_detector.py`):** Rule-based classifier using ADX, volatility, and Bollinger Band width thresholds. Four regimes: trending, ranging, volatile, quiet — each with confidence score 0.0-1.0. Stateless, deterministic, sklearn-compatible interface.

**Parameter Adapter (`parameter_adapter.py`):** Regime-aware SL/TP/lot sizing with volatility scaling. Regime multipliers for SL (0.7x-1.5x), TP (0.7x-1.5x), and lot size (0.5x-1.0x). Low-confidence fallback to conservative defaults. Kelly-adjacent fractional position sizing capped at max_position_size.

**AI Engine (`engine.py`):** Orchestration loop running the full pipeline per symbol: fetch OHLCV → compute features → detect regime → adapt parameters → write IPC params file. Per-symbol error isolation (MT5Error in one symbol doesn't halt others).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Default lot size nullified volatile multiplier**
- **Found during:** Task 3 (parameter adapter tests)
- **Issue:** default_lot=0.01 equals the floor of 0.01, so volatile regime (0.5x multiplier) produces 0.005 → floored back to 0.01, making volatile lot identical to trending lot
- **Fix:** Changed DEFAULT_LOT_SIZE from 0.01 to 0.10 so volatile (0.05) is above the 0.01 floor
- **Files modified:** python/ai/parameter_adapter.py
- **Commit:** 6232d6d

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: ipc-write | python/ai/engine.py | Engine writes to IPC directory — same trust boundary as Phase 1 data pipeline |

## Self-Check: PASSED

All 30 tests pass. All modules import without MT5 connection. IPC contract verified.
