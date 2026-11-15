# Phase 4: A/B reference orientation and evaluator-only joins

`evaluation/joins.py` adds opt-in `join_evaluator_records`. It runs after inference
using separate label-free exports, private mapping exports, retained original-order
RuntimePair records and provisional evaluator metadata from Phase 3. No predictor,
ANM or runtime runner imports it. It computes reference agreement, not metrics.

## Direction convention

The existing `original_to_runtime_column_order` export lists original column
indices at runtime positions A then B. The reference `cause_column` is the
original column index of the cause, before randomization.

| Column order at (A, B) | Original cause column | Runtime reference |
| --- | --- | --- |
| (0, 1) | 0 | A_to_B |
| (0, 1) | 1 | B_to_A |
| (1, 0) | 0 | B_to_A |
| (1, 0) | 1 | A_to_B |

Tests use fixed seeds 0 and 1 for D0101 to exercise both known orientations and
hand-written expected references. They inspect matching numeric row orientation
across E2–E4 as well as the shared mapping across E1–E4. Changing only the
reference label changes the evaluator result, never messages, mappings or arrows.

## Join checks

- Require exact runtime/evaluator/mapping/analysis case sets and one mapping per case.
- Revalidate the strict two-column permutation and nonnegative integer mapping seed.
- Recompute the original RuntimePair source digest from independently retained data.
- Replay seeded orientation without using the reference label, then check the mapping
  ID binds case, order and seed. Compare every analysis row's mapping ID exactly.
- Retain the independently scheduled slot validation from Phase 3; no inner joins
  that silently discard missing cases or failure rows.
- Require unique primary attempt IDs. S2/simple-gate rows must reference the exact
  S1 parent for their manifest/case/package and match its package digest/run ID.
  Derived answers cannot invent/reverse an answer or release a failed parent.
- Join by identities, never record positions. A two-case test deliberately gives
  runtime, mappings, labels and exports different record orders and distinct weights.

The result is a new tuple of **private evaluator dictionaries**, preserving every
analysis row and adding join version, mapped reference, weight, group, split and
`reference_agreement`. Agreement is null for all nonanswers, including original
abstentions, failures, suppressed S2 answers and unavailable method-only outputs.
It is true/false only for a supplied direction. Existing `causal_correctness`
remains null: agreement with an observational reference is not causal proof.
Do not feed these enriched dictionaries back into runtime construction.

## Trust boundaries

Matching hashes cannot establish that the dataset owner's original reference,
source grouping, eligibility or sanitized names are correct. The caller must
retain authentic original-order RuntimePairs and execute the artifact audit
before joining; self-consistently forged source/labels cannot be detected here.
This utility validates mapping against selection-v1 conventions, not arbitrary
future randomization algorithms. It does not re-audit evidence bytes behind an
export package digest or infer the expected schedule from observed output.
Faizah's actual schema acceptance remains pending; adapters should map her
reference orientation explicitly to the provisional cause_column field.

## Verification

`tests/test_evaluator_joins.py` covers the four-cell direction truth table,
reference-independent execution, failures/abstentions, missing/duplicate/extra
mappings or labels, wrong hashes/IDs/seeds, coherent swapped mappings, mutated
original data, wrong-row mappings, parent substitution/content binding, unique
attempts and multi-case record reordering.

```bash
PYTHONPATH=src uv run --extra anm pytest tests/test_evaluator_joins.py -q
PYTHONPATH=src bash scripts/check.sh
```

These tests use synthetic observations, actual evidence/ANM/checker plumbing and
scripted model responses. They require no live calls. Weighted scoring fixtures
are Phase 5; this phase does not implement Faizah's scorer or bootstrap.

Completed checks: **30 new tests, 719 full-suite tests**, Ruff lint/format, both
demos, synthetic ANM handshake and wheel/sdist builds passed. No live calls,
commits or publication were performed.
