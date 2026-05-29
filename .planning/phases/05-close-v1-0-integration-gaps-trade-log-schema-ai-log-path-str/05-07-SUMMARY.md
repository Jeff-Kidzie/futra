---
phase: 05-close-v1-0-integration-gaps-trade-log-schema-ai-log-path-str
plan: 07
subsystem: ai
tags: [regression-test, bl-01, parameter-adapter, strategy-manager, gap-closure]
requires:
  - python/ai/parameter_adapter.py:54-56 (instance dict shadowing — pre-existing, commit 2dfd5e1)
  - python/ai/strategy_manager.py:155-160 (apply_strategy mutation call site — pre-existing)
provides:
  - python/tests/ai/test_parameter_adapter.py::test_instance_multipliers_are_independent (BL-01 instance-level regression)
  - python/tests/ai/test_strategy_manager.py::test_apply_strategy_does_not_cross_contaminate (BL-01 cross-contamination regression)
affects:
  - AI-05 strategy isolation guarantee (now test-locked)
tech-stack:
  added: []
  patterns:
    - "Capture-class-default-before-mutation regression pattern (S8) — capture ParameterAdapter.<DICT>['trending'] into a local before any instance is constructed; assert all subsequent observations equal that captured value"
key-files:
  created: []
  modified:
    - python/tests/ai/test_parameter_adapter.py (+51 lines — one new test at end of file)
    - python/tests/ai/test_strategy_manager.py (+54 lines — one new test at end of file)
decisions:
  - "Used class-attribute capture (ParameterAdapter.SL_MULTIPLIERS['trending']) instead of literal expected values (1.0/1.5/1.0) so the test stays correct if defaults drift; literal failure messages still call out BL-01 explicitly."
  - "Task 2 instantiates StrategyManager and adapters inline rather than reusing the file's `manager`/`detector`/`adapter` fixtures. Rationale: the test needs two pristine adapter instances and the existing `adapter` fixture is parameterized (max_position_size=0.2, default_sl_pips=60.0). Inline construction keeps the regression assertion semantically clean and matches the plan's task spec."
metrics:
  duration_minutes: 7
  completed_at: "2026-05-29T02:00:26Z"
  tasks: 2
  files_modified: 2
  files_created: 0
  production_code_changed: false
---

# Phase 5 Plan 07: BL-01 Regression Test Coverage Summary

**One-liner:** Adds two regression tests (one unit, one integration) that lock the Phase 2 BL-01 ParameterAdapter instance-dict-shadowing fix (commit 2dfd5e1) against silent reintroduction by future refactors; zero production code changes.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add `test_instance_multipliers_are_independent` to test_parameter_adapter.py | `61f5633` | python/tests/ai/test_parameter_adapter.py |
| 2 | Add `test_apply_strategy_does_not_cross_contaminate` to test_strategy_manager.py | `4d2657d` | python/tests/ai/test_strategy_manager.py |

## Must-Haves Verification

All four truths from the plan frontmatter are now test-asserted:

| Truth | Asserted In | Evidence |
|-------|-------------|----------|
| Mutating one ParameterAdapter's SL_MULTIPLIERS does NOT affect another instance's | `test_instance_multipliers_are_independent` | Line `a1.SL_MULTIPLIERS["trending"] = 99.0` + `assert a2.SL_MULTIPLIERS["trending"] == class_sl_trending_default` |
| Mutating one instance's SL_MULTIPLIERS does NOT affect class-level ParameterAdapter.SL_MULTIPLIERS | Same test | Line `assert ParameterAdapter.SL_MULTIPLIERS["trending"] == class_sl_trending_default` |
| Same isolation holds for TP_MULTIPLIERS and LOT_MULTIPLIERS | Same test | TP + LOT assertions parallel the SL ones (six total assertions across the three dicts) |
| apply_strategy on adapter A leaves adapter B's defaults intact | `test_apply_strategy_does_not_cross_contaminate` | Line `assert adapter_b.LOT_MULTIPLIERS["trending"] == b_trending_before` after `manager.apply_strategy(detector_for_apply, adapter_a, strategy)` |

## Artifacts Verification

| Artifact (from plan) | Provided | Contains |
|---------------------|----------|----------|
| `python/tests/ai/test_parameter_adapter.py` provides "BL-01 regression test asserting instance-level dict shadowing of class-level dicts" | Yes | `test_instance_multipliers_are_independent` (verified by `grep -c "def test_instance_multipliers_are_independent" == 1`) |
| `python/tests/ai/test_strategy_manager.py` provides "BL-01 cross-contamination regression: apply_strategy on adapter A does not affect adapter B" | Yes | `test_apply_strategy_does_not_cross_contaminate` (verified by `grep -c "def test_apply_strategy_does_not_cross_contaminate" == 1`) |

## Key Links Verification

| From | To | Via | Pattern |
|------|----|----|---------|
| test_parameter_adapter.py | parameter_adapter.py:54-56 (instance dict copy in __init__) | Regression assertion that a1 mutation leaves a2 and class dicts at their captured defaults | `test_instance_multipliers_are_independent` |
| test_strategy_manager.py | strategy_manager.py:apply_strategy + parameter_adapter.py:54-56 | Two adapters, apply_strategy on one, verify the other untouched | `test_apply_strategy_does_not_cross_contaminate` |

## Verification

### Per-task acceptance criteria

**Task 1:**
- `grep -c "def test_instance_multipliers_are_independent" python/tests/ai/test_parameter_adapter.py` → `1` (pass)
- `grep -c "BL-01 regression" python/tests/ai/test_parameter_adapter.py` → `7` (pass, ≥1)
- `pytest python/tests/ai/test_parameter_adapter.py::test_instance_multipliers_are_independent -q` → exit 0 (pass)
- `pytest python/tests/ai/test_parameter_adapter.py -q` → 12/12 passed (pass)

**Task 2:**
- `grep -c "def test_apply_strategy_does_not_cross_contaminate" python/tests/ai/test_strategy_manager.py` → `1` (pass)
- `grep -c "BL-01 regression" python/tests/ai/test_strategy_manager.py` → `3` (pass, ≥1)
- `pytest python/tests/ai/test_strategy_manager.py::test_apply_strategy_does_not_cross_contaminate -q` → exit 0 (pass)
- `pytest python/tests/ai/test_strategy_manager.py -q` → 9/9 passed (pass)

### Plan-level verification

- `pytest python/tests/ai/test_parameter_adapter.py::test_instance_multipliers_are_independent -v` → PASSED
- `pytest python/tests/ai/test_strategy_manager.py::test_apply_strategy_does_not_cross_contaminate -v` → PASSED
- `pytest python/tests/ai/ -q` → 52 passed in 0.37s (50 baseline + 2 new). No collateral damage.

## Success Criteria

- [x] `test_instance_multipliers_are_independent` asserts a1 mutations do not affect a2 or class.
- [x] `test_apply_strategy_does_not_cross_contaminate` asserts apply_strategy on adapter A leaves adapter B intact.
- [x] Both tests pass on the current head (BL-01 fix is in place at parameter_adapter.py:54-56).
- [x] AI-05 strategy-isolation guarantee is now test-locked.

## Deviations from Plan

None — plan executed exactly as written.

**Notes:**
- The plan said "If `from python.ai.parameter_adapter import ParameterAdapter` is already imported at the top of the test file, the redundant inline `from ...` inside the test body is harmless." The file *does* import ParameterAdapter at the top (line 3), and the inline import remains as the plan's safety belt.
- Task 2 used the plan-provided alternative of inline `StrategyManager(strategy_dir=tmp_path)` construction rather than the `manager` fixture, because the test needs two pristine `ParameterAdapter()` instances and a custom `RegimeDetector()` for export — pulling the existing fixtures (`adapter` is parameterized with `max_position_size=0.2`, etc.) would muddy the regression intent. Plan explicitly permitted this.

## Authentication Gates

None — task did not require any external services or credentials.

## Production Code Change

**None.** This plan is pure additive test coverage. The BL-01 fix at `python/ai/parameter_adapter.py:54-56` (commit `2dfd5e1`) is the line range protected by these tests. Tests pass with that fix in place; if the three `dict(self.__class__.X_MULTIPLIERS)` lines were removed:
- `test_instance_multipliers_are_independent` would fail with `"BL-01 regression: a1 mutation leaked into a2 SL_MULTIPLIERS"` (and TP / LOT and class-level analogues)
- `test_apply_strategy_does_not_cross_contaminate` would fail with `"BL-01 regression: apply_strategy(adapter_a) leaked into adapter_b.LOT_MULTIPLIERS"`

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access, or schema changes introduced.

## TDD Gate Compliance

Plan was not `type: tdd` (it is `type: execute`). Gate enforcement does not apply: this plan adds regression coverage for a fix that already shipped in Phase 2 commit `2dfd5e1`. Both new tests pass on first run against the existing production code, which is the correct outcome — the tests are designed to fail *if and only if* the production fix is removed.

## Self-Check: PASSED

Verified files exist:
- FOUND: python/tests/ai/test_parameter_adapter.py
- FOUND: python/tests/ai/test_strategy_manager.py

Verified commits exist:
- FOUND: 61f5633 (Task 1)
- FOUND: 4d2657d (Task 2)

Verified test discovery:
- FOUND: `test_instance_multipliers_are_independent` collected and PASSED
- FOUND: `test_apply_strategy_does_not_cross_contaminate` collected and PASSED
- Full AI suite: 52/52 passed (50 baseline + 2 new regression tests)
