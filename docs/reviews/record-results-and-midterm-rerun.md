# Recorded results and midterm rerun readiness

**Status update — 20 November 2026:** this directory preserves the original
17-pair results package. Current delivery is on
[`codex/postmerge-track-b-evaluation-20261119` at `d773118`](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-execution-audit.md).
Track A's live 50-question evaluation and the larger integrated Track B panel
(38 pairs, 304 real-model responses) are complete. The 17-pair repeatability
plan is historical/optional; do not launch duplicate inference from these notes.
The 38-pair panel uses already opened labels and is exploratory, not a fresh holdout.

Historical preparation record follows.

19 November 2026. Work prepared in an isolated codex/pilot-record-results worktree
from main 7c7198d. Existing local branches and untracked drafts were preserved.
This package is prepared for a draft results PR. PR #12 was subsequently closed
as superseded with user authorization; no merge or rerun is claimed.

## Completed package

The original 17-pair pilot was copied from the available archive without deleting
the Downloads copy. All 218 pinned source files match the manifest. The native
audit used an explicit read-only mapping for the producer's saved method paths;
original journals, requests, results and hashes were not rewritten. Every original
selected sample reproduces and all 17 saved score rows reproduce exactly.

The results directory is artifacts/record-results-2026-11-19/. Full local
reproduction outputs are listed below; the GitHub package publishes aggregate
audit/process summaries and excludes evaluator joins and local path records:

- report.md and generation-costs.csv/json: resources by package and S0/S1.
- baseline-comparisons.csv/json: explicit S0, S1, S2, SIMPLE_GATE and ANM-only results.
- accuracy-coverage.png/svg: exact saved weighted rates, with no-answer accuracy
  left undefined and coincident baselines labeled together.
- process-controls.json: 14 unchanged directional E4/S1 controls passed; four
  fixed artificial perturbations each rejected on all 14 eligible parents.
- anm-independent-recount.json: all 7,125 archived file hashes/lengths verified;
  114 saved validation directions checked against saved scores/thresholds;
  primary recount is 13 correct, 13 wrong, 12 abstentions. This uses retained
  reference labels, not independent causal-label adjudication or numerical refits.
- audit.json, diagnosis.json, evaluator.json and provenance.json: evaluation
  bindings, regenerated private metadata and reproducibility records.
- model-readiness.json: read-only service check; no generation was requested.

Measured resources are 128,270 input tokens, 22,896 output tokens and 1,537.17
seconds (25.62 minutes) summed client generation latency across 136 unique calls.
Resume contributes zero new calls. Generation/parsing/binding failures are zero.
Checker/ANM wall times and local dollar cost are unmeasured. Derived baselines
reuse work; zero extra generation must not be presented as zero end-to-end compute.

The artificial mechanism checks are separate from natural-error rates: E4 method
removal is rejected by schema validation; stale sample identity, reversed method
attribution and an unavailable row index yield their expected specific codes.
Altered proposals receive explicitly synthetic matching proposal bindings so
those citation tests do not merely fail an old proposal digest. Original caches
remain untouched. Three original abstentions are excluded from this directional
control population, with the denominator disclosed.

## Interpretation of Anish's update

The merged records support the reported outcomes. Existing synthetic/numerical
checks and this saved-record audit do not establish useful real-world direction
recovery. No new numerical error has been demonstrated here. The 38-pair ANM
study differs from the 17-pair live LLM pilot and is not a matched improvement
estimate. Preserve the primary split instead of selecting a favorable secondary one.

The supported current research focus is evidence sensitivity and the boundary
between citation fidelity and causal-direction correctness, with Track A's exact
witness as an analytical anchor. Keep E4 as a descriptive negative result.
Do not launch another parameter grid or substitute a new method merely to obtain
a positive midterm score. A preprocessing/method change needs a specific diagnosed
failure mechanism, a versioned protocol and honest outcome-informed evaluation.

## Before rerunning

1. Decide the rerun's purpose. With the same opened cohort/settings it is a
   repeatability run, not a fresh test. If the original configuration is unchanged,
   the audited original results can already be presented as midterm findings.
2. Pin actual main plus the reviewed results code, model digest/runtime, prompts,
   output schema, source hashes, sample/display/mapping seeds, ANM configuration,
   threshold, primary seed, schedule and bounded budget. Use a new output path.
3. Consider an explicit zero-based row-index presentation only as a new prompt
   version justified by the two observed index errors. Retain old comparisons;
   do not silently repair or replace the pilot. Make uncertainty and method
   caveats visible without demanding agreement with ANM.
4. Confirm the callable model service and its digest, then smoke-test one matched
   pair before scaling to 136 calls. The saved localhost:11435 endpoint was not
   reachable in this environment; that is not evidence that another teammate's
   service is unavailable. No model/service was started or generation requested.
5. If time permits, close the Track A live-model gap with the existing benchmark
   and its hidden/evaluator separation. Human annotation stays deferred until
   after the midterm if feasible; no human-validation claim is made.

PR #12's mapping fix is already in current main along with later corrections.
See pr12-after-main-integration.md. It was closed as superseded on 19 November 2026; it was not merged.
The old branch is not a prerequisite for this package or rerun preparation.
