# Message to share with Vaish and the team

I've put the midterm handoff in `docs/team-handoff/2026-11-19/` on the results PR.
Please start with its README; it links the tables, figure, reproduction commands
and proposed rerun configuration.

The original 17-pair pilot has been audited and rescored from saved records, and
the resource/baseline package is complete. The checker catches five natural citation
failures, suppressing three wrong and two correct answers. E4 still gives the same
directions as ANM, with no demonstrated accuracy improvement. The separate primary
ANM validation remains 13 correct, 13 wrong and 12 abstentions on 38 cases.

For the midterm, I propose bounded evidence checking plus transparent negative
ANM results, with no further parameter search. Human annotation remains deferred.
PR #12 is closed as superseded because its fix and newer corrections are in main.

Vaish: the immediate next step is confirming the inference endpoint, runtime/API
version and exact Qwen3:8b model digest against the candidate configuration. Once
we freeze those settings, we can run the 8-call matched-pair smoke before deciding
whether to repeat all 17 pairs. No rerun has started; using the same pairs would
be a repeatability check, not a new held-out result.
