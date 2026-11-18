# Pilot Readiness Implementation Plan

**Goal:** Fix pilot-affecting defects and supply a bounded real-data pilot path without held-out execution or final reporting.

**Architecture:** Reuse native selection, ANM, runner, checker, audit and exports. Keep reference labels and source metadata in evaluator-only files. No new causal method or checker support rule.

**Tech stack:** Existing Python/Pydantic/httpx/NumPy environment.

**Specification:** User's pilot-only request, following the codebase review of main `1dd84b4`.

## Scope and decisions

- Preserve existing local thinking-option changes and smoke plan; do not commit them incidentally.
- Work on `codex/pilot-readiness` in the current checkout; no push, merge or live generation.
- Fix paired-context/mapping validation before calls and independently in native audit.
- Make method-only export validity independent of model failure. Preserve legacy model-validity metadata explicitly.
- Preserve failed Track A generations and count every attempted call in token completeness.
- Pilot ingestion uses hashed source files and explicit reviewed source groups/names, with separate evaluator records; never infer gold from column order.
- Pilot scoring includes failures in fixed denominators and does not present confidence intervals or significance claims.
- Pilot method settings remain explicitly exploratory; development calibration and held-out freeze occur later.

## Tasks and verification

1. **Paired-package isolation** — `evaluation/integration.py`, `evaluation/audit_native.py`, `tests/test_native_integration_runner.py`. Require consistent selected source/mapping/labels/units across packages, and independently check public context/mapping in saved artifacts. Dependency: existing native packages. Verify: `uv run --extra anm pytest tests/test_native_integration_runner.py -q`.
2. **Export validity and Track A failures** — `evaluation/export.py`, `pipeline.py`, corresponding existing tests. Reproduce successful ANM with failed model and truncated generation at each Track A stage, then fix. Dependency: task 1 for complete native test path. Verify: `uv run --extra anm pytest tests/test_native_integration_runner.py tests/test_pipeline.py -q`.
3. **Pilot data and scoring boundary** — new `discovery/loader.py`, `evaluation/scoring.py`, pilot entry point and focused tests. Consume a frozen snapshot plus reviewed manifest, emit runtime/evaluator files, run existing native matrix and score only after execution. Dependency: tasks 1–2 and official source-format inspection. Verify: new loader/scorer/pilot tests and offline end-to-end run.
4. **Contracts, instructions and final check** — regenerate `schemas/*.json`; update README, roadmap status and a pilot guide with actual readiness and deferred work. Verify: `bash scripts/check.sh`, native v1/v2 audits, schema export comparison, diff review.

## Execution record

- Baseline from preceding review: 587 tests on main, 593 with preserved local changes; full checks passed. Three reproduced defects confirmed on untouched main.
- Completed tasks 1–4. Regression tests failed first for changed paired context,
  model-dependent ANM metadata, lost truncated generations and undercounted usage;
  the fixes pass. The prior truncation test now excludes the independent ANM-only
  baseline from its assertion about model failures.
- User selected preparation from the official dataset. Frozen 218 source files;
  selected 17 pairs across seven source groups, with explicit notes/exclusions
  and all 108 metadata entries accounted for. No live-model outputs informed selection.
- Added strict ingestion and weighted post-run scoring; loader/scorer and full
  offline entry-point tests failed before implementation and now pass.
- `bash scripts/check.sh`: 617 tests pass, lint/format pass, both Track A demos,
  real synthetic ANM handshake, wheel and source build pass. All eight exported
  schemas match runtime contracts. Native v1/v2 demos pass independent audits.
- Full real-cohort offline validation: 136 scripted generations, 68 S2 checks,
  zero ANM errors, passing native audit. Repeated execution adds zero calls.
  Explicit post-run scoring yields 17 complete condition summaries; filenames
  label these as scripted pipeline checks, not live performance evidence.
- Fresh read-only reviewer found no important defects. Minor presentation note:
  score summaries do not embed model provenance; guide requires distinctly named
  scripted artifacts and retaining the adjacent run/session provenance.
- No live real-data generations, commits, pushes, held-out runs or final report.
  Existing user changes remain preserved. Commands and deferred scope are in
  `docs/pilot_run.md`.
- Follow-up requested by user: first live pilot completed in `runs/real-pilot-01/`.
  136 live generations, 68 S2 checks, zero execution/ANM failures, audit passed,
  cache resume zero calls. Post-run scoring retains all 17 cases across all 17
  condition/package rows. E4 arrows identical across S0/S1/S2/ANM; weighted
  selective accuracy 40.0%, coverage 89.0%. No settings were retuned or predictions
  repaired; held-out work and final report remain deferred.

## Deferred after pilot

- Held-out data execution and final protocol freeze.
- Source-group bootstrap intervals and inferential comparison plots.
- Final report and presentation.
- Optional robustness studies, new discovery methods, model training and unrestricted prose verification.
