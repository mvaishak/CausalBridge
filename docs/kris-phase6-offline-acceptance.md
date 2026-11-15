# Phase 6: offline execution-to-scorer-input acceptance

## Relevance after PR #8

The branch was fast-forwarded to merged PR #8, main `1dd84b4`, before this phase.
PR #8 owns live transport/prompt hardening, numeric claim tolerance and its review
fixes. Duplicate local pre-review copies were replaced by merged versions; our
Phase 3–5 handoff validators, evaluator joins and scoring fixtures remain new.
No changes were made to the separate smoke-fix worktree.

This phase exercises those new boundaries using the existing merged runner,
predictor, checker and independent auditor. It neither replaces that machinery
nor implements Faizah's dataset loader/scorer.

## Runnable acceptance demo

```bash
PYTHONPATH=src uv run --extra anm python -m causalbridge.evaluation.acceptance_demo \
  --fixtures tests/fixtures/track_b_scoring \
  --output runs/phase6-offline-acceptance-new
```

Use a fresh output directory; existing destinations are refused. The demo verifies
resume inside the same source/configuration session. The final local evidence is
under `runs/phase6-offline-acceptance-final/`, with report, audit, original runtime
records, separate evaluator metadata/mappings, label-free exports and private
joined records. The initial run is retained separately as historical local output.

The fixture adapter constructs eight tiny original-order RuntimePairs and separate
private evaluator records. Fixed original cause columns and mapping seed zero
produce the expected references; the scripted responder never reads labels or
metric targets. It responds only to runtime case/package and S1's caution text.

Actual native selection/package construction, original ANM request persistence,
predictor parsing/binding, durable execution, cached S2, label-free export and
strict evaluator joins then run. The resulting private scoring projection is
compared field by field with the Phase 5 input, including real reason codes,
failure stages, outcome, direction, reference agreement, weight/group/split.
Actual UUID attempt IDs are not compared to handwritten fixture IDs; Phase 4
joins enforce the real exact parent IDs, run IDs and package bindings.

| Acceptance observation | Result |
| --- | --- |
| Cases / matched E1–E4 packages | 8 / 32 |
| Scripted primary attempts | 64 |
| Saved S2 outcomes | 32: 20 checks, 12 failed-parent skips |
| Label-free / private joined rows | 136 / 136 |
| New calls from S2 / resume | 0 / 0 |
| Repeat S2 | Same records; no additional journal events |
| Independent native artifact audit | Pass; no findings |
| Scoring-input projection | Exact match to all 136 expected rows |

## Fixture reconciliation

End-to-end execution exposed placeholders in the manually authored Phase 5
projection. They now use the genuine `rows_unavailable` / `row_unavailable` checker
codes, `evidence_consistent` / `prediction_abstained` outcomes, and the actual
ANM error `insufficient_rows` in category `input_validation`. Expected weights,
metrics, H1/H2/H3 differences and group-resample targets did not change.

Three-row method samples intentionally test the typed ANM failure path; they are
not eligible method samples or an ANM performance result. Other repository demos
and tests cover actual successful KRR/HSIC execution. The separate six-row
checker-edge fixture remains a scorer-only oracle, not part of this 136-row demo.

## Tests and limits

`tests/test_offline_acceptance.py` adds 23 tests. They compare actual joined output
with all 17 hand-calculated package/condition metric targets, check schedule and
call accounting, and confirm PR #8 preserves one supplied claim on each of eight
binding-failed primary records without making them scorable. Tests block live
Ollama generation and socket creation. Saved ANM inputs/results are also reused
under a method-execution prohibition, with all file hashes unchanged.

Further tests reject an existing output directory before execution, reject a
changed scoring projection, and prove the independent audit rejects a corrupted
S2 export. The targeted integration and fixture checks passed 63 tests.

This completes **offline acceptance against a synthetic scorer-input oracle**.
It does not certify dataset eligibility, natural model error rates, calibrated
ANM, live real-data execution, Faizah's scorer/intervals, or held-out performance.
Actual teammate handoffs and one real-pair end-to-end run remain separate gates.

Final validation: **800 full-suite tests passed**, including PR #8 review
regressions; Ruff lint/format, both demos, ANM handshake and wheel/sdist builds
passed. Our integration-readiness changes remain local and uncommitted.
