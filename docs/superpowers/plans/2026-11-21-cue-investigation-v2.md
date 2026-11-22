# Cue Investigation v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze a separately versioned v2 cue protocol with explicit model-visible consistency rules and no live calls.

**Architecture:** Version-select the config and system instruction during plan preparation and reconstruction. Keep the runner, validator, checker, and analysis semantics shared with v1. Save new v2 plans in separate run directories.

**Tech Stack:** Python 3.12, Pydantic, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-11-21-cue-investigation-v2-design.md`

## Global Constraints

- Preserve v1 files, run artifacts, responses, and failures.
- Keep the pinned model/digest, generation options, conditions, fixtures, schema fields, validation, checker, and scoring unchanged.
- No live inference in this task.

## Review Focus

- A v1 plan must still reconstruct its original request payload under v1 selection.
- A v2 plan must reject any prompt or config mutation, including rehashed payload edits.
- The v2 prompt must state null-direction abstention, non-null answered direction, exact available-cue citation, and unique evidence bases without requiring cue use.
- The 20/170 cell counts and evaluator-only metadata separation must remain intact.
- A scripted pass must not authorize a live full run.

---

### Task 1: Versioned protocol selection

**Files:** Modify `src/causalbridge/evaluation/diagnostic_protocol.py` and `scripts/diagnostic_investigation.py`; create `configs/diagnostic-investigation-v2.json`; test `tests/test_diagnostic_investigation_v2.py`.

**Interfaces:** `prepare(output, *, preflight=False, protocol_version="v1")`; existing `validate_plan(plan)` reconstructs according to the manifest version.

- [ ] Add failing tests for exact v1 compatibility, v2 instruction, preserved config values, and v2 tamper detection.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Implement version selection and the v2 system text without changing v1 request bytes.
- [ ] Run focused and existing diagnostic tests.

### Task 2: Freeze and document

**Files:** Create `docs/experiments/diagnostic-investigation-v2.md`, `docs/team-handoff/diagnostic-investigation-v2.md`; create new ignored `runs/cue-v2-*` directories.

- [ ] Document every difference from v1 and the unchanged acceptance gate and failure accounting.
- [ ] Run frozen dependency sync and offline diagnostic tests.
- [ ] Run v2 scripted smoke and freeze 20-cell preflight and 170-cell full plans.
- [ ] Compare settings, schema, evaluator mapping, and payloads with v1; verify only the version and intended system text differ.
- [ ] Confirm no live run directory was created and no frozen artifact changed.
