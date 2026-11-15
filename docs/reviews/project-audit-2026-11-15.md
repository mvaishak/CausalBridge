# Project audit — 15 November 2026

## Verdict and scope

**Strong implementation foundation; promising but unfinished verification evidence;
weak evidence of improved causal-direction performance; not ready for a frozen
held-out research claim.** These are qualitative assessments, not rubric scores.

Reviewed main `7085d2f` (PR #9 merged), open PR #10 `a8ba5ba` (pilot/data/scorer),
and open PR #11 `80c4431` (our compatibility fix and consumer tests). Code review
covered runtime/evaluator boundaries, selection and mapping, native execution/
export/audit/storage, pilot loader/scoring/launcher, Track A orchestration and
benchmark documentation, and the ANM implementation. It is not an exhaustive
security/formal-correctness audit or a fresh independent rerun of every experiment.

Evidence includes prior local full checks on unchanged code: PR #11 has 830 tests
passing and one explicitly skipped pilot-API module on main; the isolated combined
pilot/main/compatibility tree passes 870 tests and all repository checks. PR #11
CI passed Python 3.12/3.13 at implementation head. Counts refer to different trees,
not a decline from the separately reported 639-test ANM validation checkout.
No new full suite was needed for this documentation-only audit.

## Important confirmed finding: scorer mapping identity is not checked

In PR #10, `score_pilot` checks that an external mapping has order [0,1] or [1,0],
that its source digest equals the evaluator record, and that analysis rows repeat
its mapping ID. It does **not** verify that this ID actually binds that order,
case and seed, or match the order against independently retained selection receipts.
See `src/causalbridge/evaluation/scoring.py`, mapping loop before row indexing.

**Reproduction:** use the native synthetic acceptance artifacts and actual pilot
scorer. Reverse only D0201's external column-order list, retaining the same valid
mapping ID, source digest, labels and all 136 analysis rows. No exception occurs;
E4/S1 selective accuracy changes from **0.625 to 0.375**. Only copies of in-memory
mapping records were modified. Machine-readable proof is local at
`runs/project-audit-20261115/scorer-mapping-finding.json`.

This is a scoring-integrity gap, **not evidence the real pilot has incorrect
mapping or scores**. The native journal audit does not independently certify a
separately supplied evaluator mapping file. Happy-path arithmetic tests passing
do not cover this malformed-mapping case. Our strict evaluator join already
checks the binding, but the pilot scorer entry point bypasses that utility.

Before closing real-pilot scoring acceptance, require strict mapping validation
against retained original runtime/selection receipts (or route scoring through
our validated evaluator join). Add a regression reversing order while leaving
its ID unchanged; it must fail before metrics are computed. Review boolean
permutations and exact seed/type validation at the same boundary. Fix the current
pilot scorer owner path; do not introduce a competing scorer.

No production fix to PR #10 was made during this audit. Treat this as a PR #10
review blocker and keep the raw-artifact gate open.

## Strength by workstream

| Workstream | Assessment | Evidence and limitation |
| --- | --- | --- |
| Track A exact tools | Strong software foundation | Independent rational/engine confirmation, observational witnesses and 50 cases across ten graph groups; human review and final live benchmark not established here |
| E1–E4 packaging / orientation | Strong within tested contracts | Matched samples/context, seeded label-independent A/B mapping, source hashes and four-cell reference truth table |
| Execution / recovery | Strong within tested runtime | Durable hash-chained records, stored failures, explicit retries, source/config identity, cached S2 and zero-call resume checks |
| Our external integration | Substantial and tested | Actual loader/scorer accepted via explicit adapters, 17 metric targets and three fixed group draws; one compatibility fix in PR #11; scorer mapping gap remains downstream |
| Evidence checker | Useful bounded mechanism | Typed claim/binding checks and numeric tolerances; five real-pilot rejections reported, not independently re-audited here; no broad prose or causal-truth verification |
| ANM numerical implementation | Strong reported fidelity | Uploaded independent report and code review reconcile 192 comparisons and 96 swaps, max discrepancy about 9.68e-16; raw validation/source bundle unavailable locally for fresh reproduction |
| ANM statistical reliability | Failed frozen gate | Locked recovery 65.6%, stability 68.8%, minimum family 25%; numerical correctness does not imply reliable direction recovery |
| Data / scorer | Useful exploratory implementation, acceptance incomplete | Pinned source manifest, reviewed pilot groups and weighted metrics exist on PR #10; mapping-integrity fix, final split audit and bootstrap still pending |
| Scientific conclusions | Preliminary | 17 dependent pairs in seven groups; uncalibrated pilot threshold; no held-out result or established E4 improvement |
| Reproducibility / documentation | Good infrastructure, incomplete shared evidence | Frozen hashes and detailed reports, but important ignored run bundles and some validation code are absent from accessible Git checkouts |

## Interpretation of the reported experiments

The pilot guide and user summary report 136 live generations, 68 cached checker
evaluations, no execution/ANM failures and a passing audit. E4 S1/S2/ANM predictions
match: 14 directional answers, six reference-correct, eight wrong, three abstentions;
weighted coverage about 89%, selective accuracy 40%. This establishes no incremental
E4 directional benefit. Agreement is consistent with ANM following but does not by
itself isolate the LLM's causal dependence on the method card.

The five rejected outputs outside E4 are a mechanism signal, not yet a measured
net benefit: manually check true violations/false rejections and correct versus
wrong answers suppressed. Empty-claim passes certify no checked supporting claim.
Reported arrow/reasoning contradictions need a separate specified rubric; the
current verifier is not a general free-text entailment checker.

The uploaded `anm-independent-validation.md`, `anm-validation-decision.md` and
`anm-validation-code-review.md` were read directly for this audit. They carefully
separate 48 operational datasets, 36 construction-direction-scored cases and the
32 compatible recovery cases. Twelve nonidentified controls must not receive
ordinary directional accuracy. The locked panel has 16 datasets and repeated split
outcomes; swaps/splits are not new independent examples. Function shapes overlap
between development/validation combinations, and uncertainty has only four shape
clusters. These limitations are acknowledged in the report.

Failing the frozen gate is a legitimate engineering progression decision, not a
statistical proof that ANM generally fails. Positive margin AUC (.800/.714) is not
confidence calibration. The report does not prove a particular preprocessing fix,
regressor change or threshold adjustment will repair the method, nor explain each
real-pilot error. A transparent negative result can support a Responsible Data
Science contribution, but claims of reliable ANM-assisted direction improvement
are not currently supported.

## Evidence gaps and release priorities

1. Correct the PR #10 scorer's external mapping validation and regression-test it.
2. Make the saved real pilot and prepared runtime/evaluator/selection records
   available; independently audit and rescore them. The current reported metrics
   remain reported rather than independently confirmed by this checkout.
3. Review/merge PR #10 and PR #11 in a tested combination; neither is merged at
   this snapshot. Our compatibility fix does not repair the separate scorer issue.
4. Anish/data owners define, version and validate ANM/preprocessing development
   changes. Preserve old traces and failed gate; no silent repair or test tuning.
5. Finish source-separated development/evaluation rules, process-error taxonomy,
   weighted/group-bootstrap uncertainty choices, and final configuration freeze.
6. Validate revised integration, then execute held-out evaluation and Track A live
   benchmark as agreed. Finish plots, error cases, reproducibility package and report.

Kris's core packaging/runner/auditor/adapter work is implemented; remaining ownership
is accurate integration acceptance, configuration freeze and audited execution.
Statistical ANM repair and source audit are teammate responsibilities. New research
experiments are choices, not hidden implementation obligations assigned to Kris.

No live model calls, threshold changes, original pilot rewrites, or production
source edits were made in this audit. Knowledge-bank changes record these findings;
they do not imply the missing raw pilot or ANM run has now been reproduced.
