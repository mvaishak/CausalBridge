# Team handoff — 19 November 2026

**Status update — 20 November 2026:** this directory preserves the original
17-pair results package. Current delivery is on
[`codex/postmerge-track-b-evaluation-20261119` at `d773118`](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-execution-audit.md).
Track A's live 50-question evaluation and the larger integrated Track B panel
(38 pairs, 304 real-model responses) are complete. The 17-pair repeatability
plan is historical/optional; do not launch duplicate inference from these notes.
The 38-pair panel uses already opened labels and is exploratory, not a fresh holdout.

This is a team-facing historical results summary, not a personal continuity or
knowledge-base document. Human annotation remains deferred. Saved-record review
does not constitute independent human adjudication or a second ANM implementation.

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

## Current next actions

- Review the [completed execution inventory](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-execution-audit.md)
  and [final results analysis](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-results-analysis.md).
- Use the [final reproduction guide](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-reproducibility.md)
  for completed delivery, and this PR's reproduction commands for its original-pilot resources.
- Resolve reporting/reproduction review comments and confirm Canvas requirements.
  No additional 17-pair run or ANM tuning is required by this package.

The linked [repeatability plan](../../plans/midterm-repeatability-run.md) and
[candidate configuration](../../../configs/midterm-repeatability-draft.json) are
retained as historical, optional proposals. They are not a current execution queue.
Track A live evaluation is complete. The 38-pair panel differs in cohort and ANM
sample limit from the original pilot and must not be presented as its exact replication.

The GitHub package contains aggregate evaluation results and reproduction code.
Full runtime logs, local paths and case-level evaluator joins remain outside this
handoff. Anyone doing later blind annotation should not read these results first.

[Copyable team message](message-to-team.md)
