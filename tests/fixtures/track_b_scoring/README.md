# Track B scorer acceptance fixture v1

All records are synthetic mechanism examples, not live-model findings. These
files are a **projection of private evaluator-joined analysis rows**, not the
native-analysis-v2 schema. Faizah can adapt this projection to her scorer input;
field names are not a claim that her final API has been accepted.

- `joined_rows.json`: 136 rows, eight cases × 17 scheduled condition/package slots.
- `expected.json`: case manifest, rational metric oracles, failures, process
  injections, H1/H2/H3 differences and three fixed paired group-resample draws.
- `checker_edge_cases.json`: separate six-row example distinguishing missing-trust
  checker abstention, checker error and a passing original model abstention.

## Hand calculation for the main fixture

| Case | Family | Weight | S1 | S2 |
| --- | --- | ---: | --- | --- |
| D0201 | family-1 | 2 | Correct | Correct retained |
| D0202 | family-1 | 1 | Wrong | Rejected |
| D0203 | family-2 | 3 | Correct | Rejected |
| D0204 | family-2 | 2 | Wrong | Wrong retained |
| D0205 | family-3 | 1 | Abstains | Pass without answer |
| D0206 | family-3 | 2 | Generation failure | Parent failure skip |
| D0207 | family-4 | 1 | Parse failure | Parent failure skip |
| D0208 | family-4 | 4 | Binding failure | Parent failure skip |

All runtime references are A_to_B in this scoring-only example; Phase 4's separate
truth-table tests cover direction conversion. Eligible weight is **16**, successful
parent weight including abstentions **9**, original directional-answer weight **8**.

S1: correct weight 2+3=5; wrong weight 1+2=3. Coverage=8/16,
correct yield=5/16, wrong yield=3/16, selective accuracy=5/8.

S2: correct weight 2; wrong weight 2. Coverage=4/16, correct yield=2/16,
wrong yield=2/16, selective accuracy=2/4. Wrong removed=1, correct suppressed=3.
The example deliberately **reduces selective accuracy** from 5/8 to 1/2: filtering
is not guaranteed to improve it. Correct/wrong yield and coverage cannot increase.

No-answer ANM_ONLY and E4/SIMPLE_GATE retain denominator 16; coverage/yields=0,
selective accuracy=null (undefined). The toy E4 method is unavailable by design;
this is not evidence about ANM performance. E1–E3 SIMPLE_GATE reproduce S1 without
process checking.

S0 at E1/E2 matches the S1 arrows, without checker rejection. At E3/E4, D0202
changes from wrong to correct and D0205 changes from abstention to wrong. Correct
weight=6, wrong weight=3, coverage=9/16, selective accuracy=6/9. This gives H1/S0
(E3 minus E2) correct-yield and coverage gains of 1/16, wrong-yield difference 0,
and selective-accuracy difference 2/3−5/8=1/24. Other H1/S1 and H2 differences
are zero in this fixture. H3 is S2 minus S1 on the exact same E4 parents.

The deliberate unavailable-citation mechanism errors are D0202 and D0203:
weight 4, rate 4/16 over eligible weight, or 4/9 conditional on successful parents.
These are explicitly different denominators and are separate from the generation,
parse and binding failure weights 2, 1 and 4. Do not report injected mechanism
errors as natural-model process-error prevalence. A final research taxonomy still
needs team agreement before held-out scoring.

## Fixed paired source-group resamples

Each draw selects four families with replacement. All pairs from a selected family
are copied, with their original weights, as many times as that family is drawn.
Use the **same draw** for both conditions and all packages. Do not sample pairs or
conditions independently, renormalize each family, or deduplicate repeated draws.

| Draw | Eligible weight | S1 correct / wrong | S2 correct / wrong |
| --- | ---: | --- | --- |
| family-1, family-1, family-4, family-3 | 14 | 4 / 2 | 4 / 0 |
| family-2 four times | 20 | 12 / 8 | 0 / 8 |
| family-3, family-4, family-3, family-4 | 16 | 0 / 0 | 0 / 0 |

The final draw has undefined selective accuracy in both conditions; its accuracy
difference is also undefined. Do not coerce it to zero. These deterministic draws
are bootstrap **acceptance examples**, not a bootstrap estimator or confidence
interval. Number of draws, percentile method, RNG seed and treatment/reporting of
undefined accuracy replicates remain the scorer owner's documented freeze choices.

## Consumer acceptance procedure

1. Validate all 136 planned slots and the invariant case/family/weight metadata.
   Fail on missing or duplicate rows; never drop failures before computing totals.
2. For each package/condition, compare raw weight totals and metrics to `expected`.
   Rational strings specify exact targets; null selective accuracy is required for
   zero answers. Scorer adapters may convert rationals to floats for comparison.
3. Check the paired H1/H2/H3 differences and separate wrong-removed/correct-suppressed
   totals. Verify checker rejection is a nonanswer, not a newly wrong answer.
4. Feed each fixed family draw to the bootstrap resampling layer and compare the
   raw totals and per-condition metrics before computing any intervals.
5. Check the separate checker-edge fixture without folding it into the main 136 rows.

`tests/test_scoring_acceptance_fixtures.py` checks these hand calculations using
exact Fraction arithmetic. It does not implement the production scorer. The real
Faizah consumer acceptance remains pending until her scorer passes these oracles.

Phase 6 reconciliation: the projection now uses actual native checker reason codes
and the actual ANM insufficient_rows/input_validation outcome instead of handwritten
placeholders. It is reproduced by evaluation.acceptance_demo. Metric/resample
oracles are unchanged; the separate checker-edge fixture remains scorer-only.
