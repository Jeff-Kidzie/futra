---
phase: 05-close-v1-0-integration-gaps-trade-log-schema-ai-log-path-str
plan: 01
subsystem: config
tags: [config, paths, env-vars, gap-closure, foundation, wave-a]
dependency_graph:
  requires: []
  provides:
    - "python.config.AI_LOG_DIR (canonical project-root-relative)"
    - "python.config.STRATEGY_CONFIG_DIR (canonical project-root-relative)"
    - "documented MT5_DEMO_LOGIN, MT5_DEMO_PASSWORD, MT5_DEMO_SERVER env vars"
  affects:
    - "python/ai/decision_logger.py (consumer of AI_LOG_DIR — already correct)"
    - "python/dashboard/api/decisions.py (consumer of AI_LOG_DIR — already correct)"
    - "python/dashboard/api/strategy.py (consumer of STRATEGY_CONFIG_DIR — already correct)"
    - "python/ai/strategy_manager.py (still imports stale AI_STRATEGY_DIR — Wave B / plan 05-04 will rewire)"
tech-stack:
  added: []
  patterns:
    - "S1 project-root-relative path constant — Path(__file__).parent.parent / ... mirrors IPC_DIR (config.py:18)"
key-files:
  created: []
  modified:
    - "python/config.py"
    - ".env.example"
decisions:
  - "Keep STRATEGY_CONFIG_DIR as the canonical symbol (consumer-side naming wins because .env.example already documents FUTRA_STRATEGY_CONFIG_DIR — operator-facing rename is more visible than internal symbol rename). Phase 5 supersedes Phase 2 02-02-SUMMARY's AI_STRATEGY_DIR naming for v1.0 consumer alignment."
  - "Make both defaults project-root-relative via Path(__file__).parent.parent / ... — eliminates CWD divergence between AIEngine (launched from python/) and Dashboard (launched from <repo>/). Mirrors the established IPC_DIR pattern at line 18."
metrics:
  duration: "~10 min"
  tasks_completed: 2
  files_modified: 2
  commits: 2
  completed: "2026-05-29"
---

# Phase 5 Plan 01: Trade Log Schema / AI Log Path / Strategy Dir — Config Foundation Summary

**One-liner:** Locked the v1.0 config foundation — one canonical project-root-relative `AI_LOG_DIR`, one `STRATEGY_CONFIG_DIR`, deleted duplicate `AI_STRATEGY_DIR`, and documented `MT5_DEMO_*` env vars — so Wave B producer/consumer rewrites can import stable names without double-editing.

## What Was Done

This is the Wave A foundation plan for Phase 5's integration-gap closure. Two atomic tasks closed three v1.0 milestone audit gaps (G3, G4-config-side, G6) that every Wave B plan transitively depends on.

### Task 1 — `python/config.py` consolidation (commit `a8a6061`)

Three structural edits, all in `python/config.py`:

1. **Replaced line 47** (`AI_LOG_DIR` single-line, default `python/ai/decisions/`) with the canonical multi-line form mirroring `IPC_DIR` at line 18:
   ```python
   AI_LOG_DIR = Path(os.getenv(
       "FUTRA_AI_LOG_DIR",
       str(Path(__file__).parent.parent / "logs" / "ai"),
   ))
   ```

2. **Replaced line 48** (`AI_STRATEGY_DIR` — old Phase 2 producer-side name) with the canonical `STRATEGY_CONFIG_DIR` definition (project-root-relative). The symbol `AI_STRATEGY_DIR` was fully deleted; the operator-facing env var `FUTRA_STRATEGY_CONFIG_DIR` is unchanged from `.env.example`.

3. **Deleted lines 108-110** (the duplicate `AI_LOG_DIR = ... "logs/ai"` + `STRATEGY_CONFIG_DIR = ... "configs/strategies"` block under Dashboard Configuration). Those defaults were CWD-relative — when `python/` was the launch directory, they pointed at `python/logs/ai`, not `<repo>/logs/ai`. Silent divergence.

Net result: `grep -c "^AI_LOG_DIR\s*=" python/config.py` returns 1; `grep -c "^STRATEGY_CONFIG_DIR\s*=" python/config.py` returns 1; `AI_STRATEGY_DIR` and `FUTRA_AI_STRATEGY_DIR` are entirely absent from `python/config.py`.

### Task 2 — `.env.example` MT5_DEMO_* documentation (commit `379a7f8`)

Appended a `# --- Paper Trading (Phase 3) ---` block at the end of `.env.example` documenting `MT5_DEMO_LOGIN`, `MT5_DEMO_PASSWORD`, `MT5_DEMO_SERVER`. These three env vars were referenced from `python/config.py:85-87` but operators had no template — every existing `.env.example` block was preserved byte-for-byte.

## Acceptance Verification

All plan acceptance criteria pass (commands run from worktree root):

```
grep -c "^AI_LOG_DIR\s*=" python/config.py            → 1
grep -c "^STRATEGY_CONFIG_DIR\s*=" python/config.py   → 1
grep -c "AI_STRATEGY_DIR" python/config.py            → 0
grep -c "FUTRA_AI_STRATEGY_DIR" python/config.py      → 0
grep -c "^MT5_DEMO_LOGIN=" .env.example               → 1
grep -c "^MT5_DEMO_PASSWORD=" .env.example            → 1
grep -c "^MT5_DEMO_SERVER=" .env.example              → 1
grep -c "Paper Trading" .env.example                  → 1
```

Smoke imports verified from both CWDs:
- From `<repo>/` (worktree root): `AI_LOG_DIR.resolve()` ends in `logs/ai`, `STRATEGY_CONFIG_DIR.resolve()` ends in `configs/strategies`.
- From `<repo>/python/` (subdirectory): both resolve to the same path. CWD divergence eliminated.

Downstream consumer imports unchanged (verified via `python -c`):
- `python.ai.decision_logger.DecisionLogger` (uses `AI_LOG_DIR`) — OK
- `python.dashboard.api.decisions.DECISION_LOG_PATH` (computed from `AI_LOG_DIR`) — OK, resolves to `<repo>/logs/ai/decision_log.jsonl`
- `python.dashboard.api.strategy.STRATEGY_CONFIG_DIR` — OK, resolves to `<repo>/configs/strategies`

IPC_DIR regression guard: `grep "IPC_DIR" python/config.py` returns the original line 18 unchanged.

## Deviations from Plan

None — plan executed exactly as written. No Rules 1-3 fixes were needed; no Rule 4 architectural decisions arose. No authentication gates.

## Expected Wave B Handoff (Not a Deviation)

Importing `python.ai.strategy_manager` currently fails with `ImportError: cannot import name 'AI_STRATEGY_DIR' from 'python.config'`. This is **expected and intentional**:

- The plan's `done` criteria list (decision_logger.py, dashboard/api/decisions.py, dashboard/api/strategy.py) explicitly excludes `strategy_manager.py` from the smoke-import set.
- The plan brief states: *"Wave B rewrites edit code that imports these constants. Without this foundation, Wave B would either double-edit imports or reintroduce drift."*
- Plan 05-04 (Wave B producer rewire) owns the two-line edit in `strategy_manager.py` (`from ..config import AI_STRATEGY_DIR` → `from ..config import STRATEGY_CONFIG_DIR`; `self.strategy_dir = strategy_dir or AI_STRATEGY_DIR` → `STRATEGY_CONFIG_DIR`).

The full test suite (which exercises `strategy_manager`) will be broken until plan 05-04 lands. Plan 05-06 will then add the regression-guard tests (`test_config_no_duplicates.py`) that mechanically prevent this duplicate-definition class of bug from reappearing.

## Threat Flags

No new security-relevant surface introduced. The change is purely path-constant deduplication; no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Commits

| Hash      | Type | Description                                                                         |
| --------- | ---- | ----------------------------------------------------------------------------------- |
| `a8a6061` | feat | consolidate AI_LOG_DIR + STRATEGY_CONFIG_DIR project-root-relative (G3 + G4-config) |
| `379a7f8` | docs | document MT5_DEMO_* env vars in .env.example (G6)                                   |

## Requirements Touched (partial — closure pending downstream waves)

- **DATA-08** — config foundation for trade log consumers (G1 still pending Wave B)
- **AI-04** — config foundation for AI decision log producer/consumer (G2 + G5 still pending Wave B)
- **AI-05** — `STRATEGY_CONFIG_DIR` canonical name locked; strategy_manager rewire pending Wave B
- **DASH-02, DASH-03, DASH-04** — same as DATA-08 / AI-04

Plan 05-01 alone does not satisfy any of these requirements end-to-end — it removes the config foundation as a blocker. Closure of each requirement requires the corresponding Wave B / Wave C plans.

## Self-Check: PASSED

- `python/config.py` exists in worktree — FOUND
- `.env.example` exists in worktree — FOUND
- Commit `a8a6061` exists in git log — FOUND
- Commit `379a7f8` exists in git log — FOUND
- All plan acceptance criteria and overall `<verification>` block commands return success (OK / counts as specified).
