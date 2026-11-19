# Team handoff — 19 November 2026

The original pilot has been independently audited and rescored from saved records.
The resource/baseline package is complete. **No new pilot has been run, and human
annotation remains deferred.** This is a results-code review and reproducibility
check, not independent human adjudication or a second numerical ANM implementation.

## What we can report

| Evidence | Result | Interpretation |
| --- | --- | --- |
| Original pilot | 17 pairs / 7 source groups; 136 model calls; 68 cached S2 checks | Exploratory, already opened cohort |
| Record audit | All 218 pinned source hashes and 17 saved score rows reproduce | Original records retained unchanged |
| E4 | S0, S1, S2, SIMPLE_GATE and ANM-only have identical arrows: 6 correct, 8 wrong, 3 abstentions | No demonstrated direction improvement; weighted answered accuracy 40.0%, coverage 89.0% |
| Natural citation failures | Five outside E4; checking suppresses 3 wrong and 2 correct answers | Citation fidelity does not establish causal correctness |
| Artificial controls | 14 unchanged directional controls pass; 56 fixed perturbations rejected | Bounded mechanism checks, not natural error prevalence |
| ANM real-data validation | Primary 38 cases: 13 correct, 13 wrong, 12 abstentions | Saved-record recount agrees with Anish; tuning has not established reliable real-data recovery |
| Resources | 128,270 input / 22,896 output tokens; 25.62 minutes summed generation time | Checker/ANM time and monetary cost unmeasured |

Numerical correctness and useful causal recovery are separate questions. The
midterm focus should be bounded evidence checking with transparent negative ANM
results. Further parameter or method searches are outside the proposed midterm scope.

## Read these files

1. [Results package and reproduction commands](../../../artifacts/record-results-2026-11-19/README.md).
2. [Measured resources and baseline report](../../../artifacts/record-results-2026-11-19/report.md).
3. [Accuracy–coverage figure](../../../artifacts/record-results-2026-11-19/accuracy-coverage.png).
4. [Proposed repeatability plan](../../plans/midterm-repeatability-run.md) and
   [candidate configuration](../../../configs/midterm-repeatability-draft.json).
5. [PR #12 review](../../reviews/pr12-after-main-integration.md): closed as
   superseded, because its fix and newer corrections are already in main.

## Next actions to agree on

These are proposed responsibilities, not claims that teammates have accepted them.

| Owner | Next action | Completion evidence |
| --- | --- | --- |
| Kris / results reviewer | Review this package, retain original-versus-repeat tables, seal reviewed code and configuration identities | Reviewed commit and frozen execution manifest |
| Vaish / pilot runner | Confirm actual inference host/endpoint, runtime/API version and exact Qwen3:8b digest; review candidate settings | Callable service with matching metadata recorded |
| Anish / ANM reviewer | Confirm original pilot ANM settings remain fixed and keep the 38-case validation separate | Configuration review; no additional tuning needed |
| Team | Agree to the bounded midterm focus and whether repetition is worth the remaining time | Explicit choice recorded before launch |

After configuration and service verification, run the deterministic D1006 smoke:
8 matched E1–E4 S0/S1 calls and 4 cached S2 checks. Scale only after operational
checks pass. A separate full repetition would add 136 model calls: maximum 144
fresh calls including smoke. Keep both runs; the same 17 cases test repeatability,
not a fresh holdout. No smoke or full run has started from this package.

If time or service access is tight, the audited original pilot can already be
presented as the midterm result. Human annotation stays deferred until after the
midterm if feasible; Track A live evaluation is a separate remaining gap.

The GitHub package contains aggregate evaluation results and reproduction code.
Full runtime logs, local paths and case-level evaluator joins remain outside this
handoff. Anyone doing later blind annotation should not read these results first.

[Copyable team message](message-to-team.md)
