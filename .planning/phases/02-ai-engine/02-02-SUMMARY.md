---
phase: 02-ai-engine
plan: 02
subsystem: ai-engine
tags: [ai, decision-logging, strategy-management, tdd]
dependency:
  requires: [02-01]
  provides: [decision-logging, strategy-export-import]
  affects: []
tech-stack:
  added: [JSONL logging, JSON strategy config]
  patterns: [TDD RED/GREEN, daily log rotation, schema validation, round-trip fidelity]
key-files:
  created:
    - python/ai/decision_logger.py
    - python/ai/strategy_manager.py
    - python/tests/ai/test_decision_logger.py
    - python/tests/ai/test_strategy_manager.py
  modified:
    - python/config.py
    - python/ai/engine.py
    - python/tests/ai/test_engine.py
decisions:
  - "Decision logger uses daily file rotation (ai_decisions_YYYY-MM-DD.jsonl) for human-readable per-day logs"
  - "Features snapshot limited to 6 most diagnostic keys (not all 10) to keep log lines concise"
  - "Strategy schema versioned at 1.0.0 with STRATEGY_SCHEMA_VERSION constant for future migration"
  - "DecisionLogger is optional in AIEngine — None disables logging without code changes"
metrics:
  duration: "~10 min"
  completed: "2026-05-26"
  tests: 20 passed (8 logger + 8 strategy + 4 engine)
---

# Phase 02 Plan 02: Decision Logging + Strategy Management Summary

**One-liner:** JSONL decision logging with human-readable reasoning per AI parameter choice, plus JSON strategy config export/import with full round-trip fidelity for versioning and A/B testing.

## What Was Built

**Decision Logger (`decision_logger.py`):** Structured JSONL logging of every AI parameter decision. Each line contains: ISO8601 timestamp, symbol, regime, confidence, SL/TP/lot, volatility, ATR, 6-key feature snapshot, and human-readable reasoning explaining the parameter choice. Daily file rotation, auto-created directories, IOError-safe.

**Strategy Manager (`strategy_manager.py`):** Export/import of RegimeDetector thresholds and ParameterAdapter settings as versioned JSON files. Schema validation enforces required keys (raises ValueError on missing). Round-trip fidelity verified: export → import → apply produces identical predict/adapt output. Supports multiplier overrides.

**Engine Integration (`engine.py`):** AIEngine now accepts optional DecisionLogger parameter. When provided, every evaluate_symbol() call logs the full decision context. Logging failure does not crash the engine (IOError-safe). Backward compatible — None is the default.

**Config Extensions (`config.py`):** Added AI_LOG_DIR, AI_STRATEGY_DIR, AI_DEFAULT_TIMEFRAME, AI_DEFAULT_EQUITY constants with environment variable overrides.

## Deviations from Plan

None - plan executed exactly as written.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: log-tampering | python/ai/decision_logger.py | JSONL logs are append-only with no integrity verification (T-02-07 accepted) |
| threat_flag: config-injection | python/ai/strategy_manager.py | Imported JSON validated against schema before apply (T-02-06 mitigated) |

## Self-Check: PASSED

All 50 AI tests pass (30 from Plan 01 + 20 from Plan 02). Decision log format verified. Strategy round-trip verified. Engine + logger imports verified without MT5.
