# Phase 5: scoring acceptance fixtures

Completed the independent synthetic scorer handoff, without adding a production
scorer or bootstrap estimator. The complete specification, hand calculations and
consumer procedure are in
[the fixture README](../tests/fixtures/track_b_scoring/README.md).

The main input has eight cases in four source families, 136 scheduled slots and
eligible weight 16 per package/condition. Expected results cover S0, S1, S2,
simple-gate and ANM-only baselines; failure accounting; no-answer accuracy;
wrong answers removed versus correct answers suppressed; and paired H1/H2/H3
comparisons. A separate six-row fixture distinguishes checker error, missing-trust
abstention and pass without answer.

Three fixed source-family resamples verify repeated-family multiplicity, paired
case membership and weighted totals, including a no-answer replicate. They do not
choose confidence-interval settings or claim statistical uncertainty estimates.

All fixtures are reduced projections of private evaluator-joined rows. Their
expected values are exact rational strings, and their schemas remain adapter
targets pending Faizah's actual scorer. Phase 6 now verifies that the merged
execution/export/join path produces the expected scoring projection. See
[offline acceptance](kris-phase6-offline-acceptance.md); arithmetic consistency
alone was not treated as evidence of that integration.

Forty fixture acceptance tests use independent exact arithmetic and reject missing,
duplicate, misweighted, regrouped or incorrectly labeled inputs. No production
source, runtime protocol, model call or real dataset was changed in this phase.

Final validation: **40 new fixture tests; 759 total tests passed**, Ruff
lint/format, both demos, synthetic ANM handshake and wheel/sdist builds.
Changes remain local and uncommitted.
