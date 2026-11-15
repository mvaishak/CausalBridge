# Phase 3: fixture-backed external handoff validation

This phase adds acceptance boundaries in `evaluation/handoff.py`. It does not
implement dataset ingestion, label conversion, weighted scoring or bootstrap.
Faizah's real loader/scorer acceptance remains open.

## Loader boundary

`validate_loader_handoff(runtime_records, evaluator_records)` returns two separate
validated tuples. The runtime side uses the existing `RuntimePair`: opaque case
ID, two already-sanitized variables, and finite numeric rows in original column
order. No label, weight, group, split or original source field is accepted there,
including extra fields nested in variable records.

The private evaluator shape is a **provisional local adapter target**, not a
claim that Faizah already supplies these names:

| Field | Meaning |
| --- | --- |
| case_id | Same opaque ID as runtime; exact one-to-one case sets |
| source_group | Dataset owner's source-family grouping |
| weight | Positive finite pair weight; booleans/strings rejected |
| split | pilot, development or test |
| cause_column | Strict integer 0 or 1 identifying reference cause in original column order |

Each batch must be nonempty, have unique IDs and matching runtime/evaluator case
sets. A source group cannot span different splits within the supplied batch.
Pass the complete handoff to check all its group assignments; batch-local checks
cannot certify a dataset-wide split when other batches are omitted. Mapping the
reference to randomized A/B is Phase 4, not done implicitly here.

This validator cannot certify eligibility, dataset snapshot integrity, correct
source-family definitions, honest reference labels, or sanitized natural-language
names/units. Those remain data-audit responsibilities. It neither cleans text nor
silently removes extra fields. A loader adapter should explicitly construct the
allowlisted RuntimePair fields, preserving private metadata separately.

## Analysis boundary

`validate_analysis_handoff(rows, expected_slots=...)` accepts only the current
label-free `native-analysis-v2` export shape. Required identities, nullable usage,
failure stages, claim accounting, directions, baseline fields and versions are
validated without adding evaluator labels.

The caller supplies the planned set of `(manifest_id, case_id, package, condition)`
slots **from its independent schedule**, not from the exported rows. For one case
and one replicate/manifest, the current matrix is 16 E1–E4 ×
S0/S1/S2/SIMPLE_GATE rows plus E4/ANM_ONLY: 17 slots. Missing failures, duplicate
slots and extra cases/conditions are rejected. Separate attempts/replicates must
be represented by separate manifests; this boundary does not combine retries.

Failed primary predictions cannot supply arrows, incomplete primary generations
cannot be scorable, and S2's recorded answer must equal a passing recorded
release. Derived S2/simple-gate rows need parent IDs. Only E4 may carry ANM_ONLY.
This does not independently validate parent contents or orientation: the native
artifact audit and Phase 4 mapping/join checks cover those trust boundaries.
ANM_ONLY inherits some parent execution diagnostic fields in the existing export;
its scoring interpretation must use its own condition/method outcome, not treat
those fields as an independent model call.

## Fixtures and acceptance checks

`tests/fixtures/track_b_handoff/loader.json` contains two tiny synthetic pairs and
separate private sentinel metadata. It is not Tuebingen data, an eligible ANM
sample, or a scored experiment.

`tests/test_track_b_handoff.py` checks malformed/private runtime fields, duplicate
and mismatched IDs, invalid weights and group splits, model-instance validation
bypasses, and export completeness/contradictions. Native export checks use actual
ANM/predictor/checker plumbing with scripted responses for successful prediction,
abstention, timeout, malformed JSON, wrong binding and unavailable citations.
Sentinel checks inspect actual model messages and original saved ANM requests.

```bash
PYTHONPATH=src uv run --extra anm pytest tests/test_track_b_handoff.py -q
PYTHONPATH=src bash scripts/check.sh
```

No live model calls are needed. These functions are opt-in acceptance utilities;
existing runtime entry points and saved protocol identities are unchanged.

Completed validation: **120 new boundary cases**, **689 full-suite tests**,
Ruff lint/format, both demos, synthetic ANM handshake and package builds passed.
No live calls, commits or publication were performed.
