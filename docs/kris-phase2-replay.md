# Phase 2: saved live-smoke verification replay

Completed 2026-11-15 against the Phase 1 working tree based on PR #7 (`3d9d645`).
This is deterministic verification of existing synthetic-observation runs, not a
new experiment or a real-data accuracy result. No production source was changed
in this phase.

## Independent reproduction

Existing checker-0.3 replay bundles were discovered. Their comparison was
reproduced independently from fresh copies of the original smoke bundles under
`runs/phase2-checker03-verification/`. Original reports and traces were not used
as output destinations. The verification script and machine-readable summaries
are saved there with each copied bundle's detailed audit and comparison.
The verification script refuses to replace an existing destination.

| Original run | Package | Checker 0.2 | Checker 0.3 | Released direction |
| --- | --- | --- | --- | --- |
| First smoke | E1 | Fail: rows unavailable | Unchanged | None |
| First smoke | E2 | Fail: method unavailable | Unchanged | None |
| First smoke | E3 | Fail: method unavailable | Unchanged | None |
| First smoke | E4 | Pass | Unchanged | A_to_B |
| Second smoke | E1–E3 | Pass, original prediction abstained | Unchanged | None |
| Second smoke | E4 | Fail: summary rounding mismatch | Pass | A_to_B |

The second-smoke E4 check also contains the observed row-value rounding issue.
The scoped tolerance resolves numeric representation differences; evidence
bindings, original predictions and categorical identities remain unchanged.
First-smoke E1–E3 still fail because unavailable evidence is not repaired by
numeric tolerance. First-smoke E4 supplied no claims: its pass is not evidence
of checked supporting citations.

## Acceptance evidence

- Independently audited both original experiment journals and both new replay
  journals: all passed, with no findings.
- Recomputed all eight checks directly from saved evidence, predictions and
  contexts; each equals the runner's new saved check.
- Repeated each replay: identical results and no journal events appended.
- All original bundle file hashes were identical before/after, including raw
  replies, saved predictions and historical checks.
- All copied non-S2 execution events were identical before/after replay.
- Zero new model or ANM calls. Model generation, socket creation and ANM execution
  were patched to raise during replay; none was invoked.
- Regenerated label-free analysis exports using the new S2 results.

Artifact entry points (local, ignored runtime evidence):
`runs/phase2-checker03-verification/summary.json`, `verify.py`, and each copied
bundle's `phase2-verification.json` and `phase2-analysis.jsonl`.
One initial verification attempt stopped on a verification-script API mismatch
before replay; its copy was retained separately as `*-incomplete-attempt`.
The corrected complete verification passed both bundles.

The native audit checks recorded artifact integrity and handshake invariants;
it does not independently establish causal correctness or dataset eligibility.
No additional production changes required a repeat of Phase 1's full checks
(569 tests plus lint/format, demos, ANM handshake and builds). Phase 2 adds direct
artifact checks rather than claiming those tests were rerun here.

Next: Phase 3 fixture-backed loader/export boundary validation, followed by
orientation/evaluator joins and scorer acceptance fixtures.
