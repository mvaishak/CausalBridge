# Implementation record

## Explicit real-validation test — 2026-11-18

- User authorized testing the 38 real validation pairs descriptively, without
  tuning. Added a fixed-config wrapper that freezes the protocol before executing
  only `sample_512`, rejects parameter/split changes, and supplies no invented gate.
- Executed all 38 pairs at three fixed splits (114 original requests), with no
  execution errors. Primary result: 13 correct, 13 wrong, 12 abstain; 48.1% weighted
  answered accuracy. Secondary results and all small-sample cases remain reported.
- Cached reconciliation verifies schedule, original bindings and source-column
  scoring. The original roster/pilot data are unchanged, but the validation
  outcomes are now opened and must not guide tuning under an untouched-holdout claim.
- Full checks pass 996 tests without skips, plus lint/format, demos, handshake and
  builds. This test does not establish reliable real-data recovery; no LLM calls.

## Fixed synthetic success panel — 2026-11-18

- Responded to the request to test broader pairs by fixing all generators/seeds,
  noise laws/scales, sizes, splits and demonstration criteria before new fits.
  Added a reproducible example, two plans and schedule/metric integrity tests.
- The unchanged producer succeeds on compatible fresh confirmation datasets at
  n=512: 26 correct, zero wrong, six abstentions; all four families pass the
  predeclared floors. Retained all 88 datasets, 352 evaluations and 176 swaps,
  including controls and n=128 failures. No post-outcome case removal or tuning.
- Cached reconciliation verifies every generated sample, truth, original request,
  numerical record and swap. Additional post-outcome raw-sign/stability summaries
  are marked descriptive, not retroactively added to the gate.
- Tested the larger-sample policy on the same four real development pairs only.
  One primary pair becomes correct but other splits remain at zero accuracy;
  synthetic success is not claimed as real-data repair. All 38 validation pairs
  remain unused and no candidate is frozen for production.
- Full checks pass 992 tests without skips plus lint/format, demos, handshake and
  builds. Detailed results/reproduction commands are in `anm_synthetic_panel.md`.

## Anish: targeted adequacy diagnosis and commit — 2026-11-18

- Inspected per-case MSE versus HSIC. Reference-direction MSE is lower for pairs
  12/99, yet the baseline HSIC score still selects the wrong direction. Prediction
  error alone is therefore not a demonstrated explanation or a causal selector.
- Added the separately versioned, fixed 199-permutation/alpha=0.05 exploratory
  adequacy protocol, diagnostic example and numerical/error tests. It uses saved
  baseline samples and verifies its HSIC scores against production before testing.
- Executed 72 directional checks on 12 dependent real split outcomes and 24
  control outcomes. Primary weighted coverage falls to 33.3%, but answered accuracy
  remains zero at all three splits. Original file hashes are unchanged. No gate
  parameters were selected from these outcomes, and no production repair is claimed.
- Reviewed source assumptions for the four development pairs. Survey row weights,
  catchment confounding and school clustering/selection are limitations; no single
  causal explanation is established and frozen references/exclusions stay unchanged.
- User authorized committing the complete replay/study/follow-up work on the
  feature branch, including PR #14 as an explicit merge dependency. No real
  candidate/criteria are invented and all 38 real validation pairs remain unused.
- Final full check: 987 tests pass without skips, 91% statement coverage;
  lint/format, demos, ANM handshake and builds pass. No remote push/new PR is
  requested. All run artifacts remain ignored; reproducible plans and aggregate
  findings are in the shared documentation.

## Anish: ANM-only development and frozen-validation workflow — 2026-11-18

- Brought reviewed PR #14 `a29dc4b` onto the existing Anish feature branch through
  an uncommitted merge. Backed up and restored the existing additive replay/docs
  changes; the original numerical producer, data manifest and roster are unchanged.
- Added `discovery/study.py`, a fixed development plan and protocol/integrity
  tests. New numerical inputs are label-free; evaluator joins/scoring happen later.
  Code supports development baseline/comparisons, explicit candidate criteria,
  frozen source/environment identities and a single-use validation start marker.
- Executed 72 real-data development fits and 24 baseline-control fits in the final
  source-frozen run. No real validation fits or LLM calls. All six primary metric
  cells have zero correct answers. The candidate-freeze/validation path is tested
  with synthetic fixtures; no real candidate or acceptance targets were invented.
- Independent decoding and four post-outcome swap checks confirm that the baseline
  errors are not repaired by reversing a mistaken A/B mapping. Preliminary source
  annotation revisions have identical numerical results and do not count as new
  independent examples. Full details: `anm_development.md` and ignored run outputs.
- All changes remain local/uncommitted, and PR #14 is not altered by this work.

## PR #14 review corrections — 2026-11-18

- Restored the complete reviewed diagnosis corrections from Kris's `cf64934`,
  including original experiment journal/result binding, status-aware agreement
  counts and regression tests. Updated both handoff diagnosis commands.
- Added one-manifest S1-parent validation before pilot scoring for S2/simple-gate
  records. Native export corruption tests cover missing/wrong parents, manifest,
  package/run/attempt substitution, reversed arrows, failed/abstaining parents and
  contradictory release outcomes. Valid metric oracles stay unchanged.
- Extracted loader source-group constraints for shared roster validation. Scorable
  records must pass the existing data-audit eligibility rules on pinned numeric
  files; overlap, constant/nonfinite/short/blank data and unpinned data are rejected.
- Checker execution errors have separate counts/weights and are excluded from
  completed correct/wrong suppression totals. Completed checker abstentions are
  not model abstentions.
- Full verification: 947 tests, no skips; lint/format, demos, ANM handshake and
  builds pass. Snapshot/roster and retained scripted-pilot checks pass read-only.
  No ANM tuning, LLM calls, manifest changes or historical result edits.
- PR #14 is the proposed consolidated main integration; overlapping #10/#12 must
  be reviewed as superseded or retargeted after it lands, not merged blindly.

## Anish: roadmap numerical inference and ANM producer — 2026-11-14

- Publication follow-up: CI caught an unformatted Python snippet in the newly
  added `docs/anm_producer.md`. Applied Ruff to the documentation, rechecked
  formatting/lint, and pushed a documentation-only correction. The first failed
  run stopped before pytest; it was not a numerical-test failure.

- Audited all remote branches. PRs #1-#3 supply graph/witness generation and a
  seven-case pilot. PR #4 supplies Track B predictor/checker/contracts. After the
  user requested latest main, created a fresh `CausalBridge-Anish` clone at
  `48d6cda` and feature branch `codex/anish-anm-provenance`. The old checkout is
  preserved. Implementation remained local until Anish authorized committing and
  pushing this feature branch. No PR or teammate message is part of publication.
- Used `docs/planning/Detailed_Implementation_Roadmap.pdf` for scope and
  `docs/track_b_integration_contract.md` plus its merged Python schemas for the
  exact interface. No predictor, verifier, schema, structural graph, or benchmark
  source changes were needed.
- Carried forward the local Track A numerical engine/tests from `db26886` while
  preserving merged graph helpers. Added exact rational propensity-reweighting
  tests for all merged pilot numeric labels and the +0.30/-0.30 witness with all
  four observational P(X,Y) cells equal to 0.25. Existing oracle tags are not edited.
- Added `discovery/anm_requests.py`: normalized numeric rows, explicit validated
  config, deterministic split, exact ANMRequestBinding and pre-execution sample/
  config/request/manifest files. Files are exclusive and fsynced. No result is
  read or computed to create the original. No reference labels enter the API.
- Added `discovery/anm.py`: held-out bidirectional RBF kernel ridge regression,
  median-bandwidth biased HSIC, margin/threshold semantics, typed method errors,
  reproducibility records, exclusive execution markers and artifact verification.
  NumPy is optional/lazy. Threshold defaults to null; it is not fitted on test data.
- Added display-only numeric summaries matching the merged NumericSummary schema.
  Added `anm-run`, explicit Track A engine selection and a synthetic handshake
  through the existing predictor/checker, with separate evidence/S1/S2 receipts.
- Added 143 tests to the 267-test merged baseline: 81 carried-forward engine/graph
  cases, 2 independent pilot checks, and 60 ANM/request/verifier-integration cases.
  Tests prove request persistence before numerical execution, no result-derived
  fallback, closed threshold boundaries, sample/config/count/seed/mapping/version
  binding, original-file preservation, correct display/method sample separation,
  and S2 operation without new model/method calls.
- During development, formatting/import issues (including a missing Path import
  in one new test) were corrected before final verification. Core focused tests
  and the combined suite pass. Exact results are in `verification.md`.
- Added the ANM optional dependency/lockfile and full-check/CI coverage. Updated
  the shared README, handoff, inventory, integration contract and producer guide.
- Final local checks: 410 tests pass on Python 3.12 and 3.13; 94% total coverage;
  lint, format, lock check, both Track A demos, computed synthetic handshake,
  source/wheel builds and isolated base/ANM-extra wheel runs pass.
- Remaining team work: real data/pair mapping, E1-E4 runner/cache integration,
  development-selected/frozen tau, scorer and live-model evaluation. These are
  not replaced by synthetic fixtures or claimed as completed experiments.

## Historical Vaishak implementation

Plan: `docs/superpowers/plans/2026-10-27-vaishak-implementation.md`.

- User authorized assumptions and end-to-end execution; use ordinary project practices
  while RTK.md and PROCESS.md are absent (confirmed in chat).
- Empty Git repository has no baseline code or commits. Work in the supplied
  checkout on `codex/vaishak-verifier`; a second worktree needs an initial commit
  and adds no useful isolation here. Preserve both original PDFs.
- No local Ollama executable or server detected. Exercise the live adapter with
  HTTP transport tests; do not describe scripted outputs as model results.
- Preflight: schemas feed tools/contracts; request and result carry the same query,
  operation and evidence digest. Pipeline uses those exact interfaces.
- Task 1: complete. Visible-only schemas, projection, causal assumptions and
  validation; initial 15 schema tests passed after missing-module RED.
- Task 2: complete. General capability/evidence/conclusion contracts, replaceable
  backend protocol and development reference calculations; 42 tests passed.
- Task 3: complete. Strict JSON lifecycle, Ollama transport, CLI, 8 fixture cases,
  exported schemas, lockfile, CI and integration documentation; 60 tests passed.
- Serena's active project has no language servers. Its editing calls failed with
  that explicit error; continued using normal file editing tools.
- Independent read-only review found 2 Important issues: malformed benchmark root
  types crashed ingestion, and Pydantic error strings exposed rejected nested
  values. Six regression tests failed first, then passed after explicit root-type
  validation and `hide_input_in_errors=True` at the shared model boundary.
- Final integration check found operation mismatch was classified after missing
  evidence in the pipeline. A regression test failed first; shared
  `check_operation` now runs before evidence requirements. Full suite: 67 passed.
- Build configuration excludes the supplied source PDFs from package archives;
  the originals remain untouched in the project folder.
- Review scope decisions: live model behavior requires the user's chosen runtime;
  benchmark results require the team's generated data; natural-language parsing
  and numerical backend correctness remain explicit trust boundaries. These match
  the design. No research-results claim is made. No deferred minor findings.
- Local completion keeps the feature branch and supplied checkout for the user.
  No remote repository is configured, so nothing is pushed or published.
- Final checks: locked sync, lockfile consistency, Ruff lint and formatting,
  67 tests, 8 demo cases, JSON schema export, source/wheel build and an isolated
  wheel-install smoke run passed. See `docs/verification.md` for evidence and limits.

## Anish: ANM baseline replay preparation — 2026-11-17

- Pulled latest main (`dbbf8db`) and created
  `codex/anish-anm-baseline-reproduction`. Changes remain local and uncommitted.
- Inspected all published branches: the independent-validation source/bundle
  described by the three external reports is absent. PR #13 is merged into the
  open PR #12 branch, not main; no dependency-branch code was copied into this work.
- Added `discovery/replay.py` to verify durable producer artifacts and optionally
  replay exact inputs/configuration in a fresh output directory. No independent
  reference, statistical benchmark, tuning harness or LLM experiment is invented.
- Added failure/preservation tests in `tests/test_anm_replay.py`, and updated the
  shared producer, verification and handoff documentation.
- Checked and replayed all 17 saved ANM attempts from the prior scripted-pilot
  review. Scores/decisions reconcile and original producer hashes remain unchanged.
  Scientific reproduction remains dependent on the original validation bundle.
- Final full check: 846 tests pass, one explicit missing-pilot-API module skip;
  16 new replay tests, lint/format, both Track A demos, synthetic ANM handshake,
  and source/wheel builds pass. Details and local artifact paths are in
  `verification.md`. No GPU, live model or paid API was used.

## Anish: branch commit-review corrections — 2026-11-18

- Addressed Kris's review on commit `b189a8b` (commit comment 210618986).
- Fixed the descriptive real-validation wrapper to require sampling seed 262
  before snapshot validation, data access or fitting. Added seed-999 corruption
  coverage and explicit guards against entering roster validation or execution
  for any rejected configuration.
- Updated `anm_producer.md` to reflect the pushed development branch, merged
  producer, PR #14 dependency, available integration code and opened 38-pair
  validation results. Historical experiment records and their original hashes
  remain unchanged; no numerical study or LLM evaluation was rerun.
- Full `scripts/check.sh`: 997 tests passed, no skips; lint/format, Track A demos,
  synthetic ANM handshake and source/wheel builds passed.

## 2026-11-21 — Controlled diagnostic-following investigation preparation

On `codex/anm-evidence-investigation-20261121`, based on the latest Qwen3 thinking
ablation commit `ecd1b30`, added isolated protocol, durable runner and offline
analysis modules under evaluation. The saved-result diagnosis joins all 408
original/ablation observations and 102 E3/E4 transitions. The new protocol freezes
five experimental directional-cue conditions on 17 opened pairs, both thinking
settings, plus a separate 20-call synthetic preflight. These are not fabricated
ANM results, new benchmark evidence or changes to production verifier behavior.

Validation: 26 new regression cases, full suite 1,053 passed/two existing optional
snapshot skips, Ruff checks, scripted demos, synthetic ANM handshake and package
builds. An offline end-to-end smoke exercised all 190 planned cells. HTTP mock
transport tests additionally exercised model checks, live-preflight gating and
raw-response handling; no real model inference was performed. Failed observations
are retained, and explicit resume recovers saved raw data without retrying failures.

See `docs/experiments/diagnostic-investigation-v1.md`, the shared runner handoff,
and `artifacts/diagnostic-investigation-v1/`. Live execution and the final scientific
interpretation remain for the compute owner. Publication requires separate user
authorization; no commits, pushes or merges were made during preparation.

## 2026-11-21 — Diagnostic-cue v2 output-contract correction

Audited both supplied v1 live-failure archives and verified their included checksum
inventories, request/raw bindings and exact decoder errors. Both complete replies
on the first no-cue synthetic cell passed the supplied JSON Schema but failed the
application's hidden direction/abstention relationship. Earlier transport failures
were separated from these schema failures. No v1 reply was reclassified or repaired.

Added opt-in v2 plans with one generated decision enum and deterministic internal
direction/abstention mapping. V2 rejects legacy extra fields and duplicate JSON keys;
evidence-basis uniqueness is represented in its schema. The model, seeds, budgets,
cohort, five cue arms and thinking settings remain fixed. Preflight now stops before
the next trial after the first saved failure/rejection, with actual completed versus
scheduled counts. Resume retains failures; full-run per-cell handling is unchanged.
Existing v1 plans remain bound to their original source commit; no frozen plan was
silently updated. The v1 config, protocol and artifacts remain unchanged.

Validation: full suite 1,082 passed with two existing optional-snapshot skips;
29 new v2 regression cases plus the existing 26 cue-study tests. V2 scripted smoke
completed 20 preflight and 170 full cells; mock HTTP success/failure/resume tests
passed. Ruff, demos, synthetic ANM handshake and source/wheel builds passed.
These are software checks, not live v2 model findings. Fresh live preflight and
170-cell inference remain pending. Changes are not committed or published.
