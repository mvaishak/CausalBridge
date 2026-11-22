# Adequacy-rule comparison: results and interpretation

## Main finding

The saved-data comparison does **not establish a reliable accuracy fix**. Independence-based withholding can remove wrong answers, but also removes correct answers. The trade-off changes substantially across the pilot/later panels and IID/heuristic-block schemes. Warning-only annotations improve inspectability by exposing the diagnostic state; they do not change answers or establish better causal accuracy.

No original ANM direction, threshold, raw result or production code was changed. There were no new fits, permutations or LLM calls. Five fixed policies, two stored diagnostic schemes and two panels produce 20 reported configurations and 550 case/policy/scheme rows. Every configuration is retained, including unfavourable results. The record contains 55 underlying cases, not 550 independent observations.

## Later panel: all 38 scheduled cases

| Diagnostic / policy | Correct | Wrong | Total abstentions | Retained accuracy | Coverage | Wrong removed | Correct lost |
|---|---:|---:|---:|---|---|---:|---:|
| Original (either scheme) | 13 | 13 | 12 | 13/26 = 50.0% | 26/38 = 68.4% | 0 | 0 |
| IID: withhold if both rejected | 6 | 8 | 24 | 6/14 = 42.9% | 14/38 = 36.8% | 5 | 7 |
| IID: withhold if selected rejected | 6 | 8 | 24 | 6/14 = 42.9% | 14/38 = 36.8% | 5 | 7 |
| IID: require unique nonrejected | 6 | 4 | 28 | 6/10 = 60.0% | 10/38 = 26.3% | 9 | 7 |
| Blocks: withhold if both rejected | 10 | 9 | 19 | 10/19 = 52.6% | 19/38 = 50.0% | 4 | 3 |
| Blocks: withhold if selected rejected | 10 | 9 | 19 | 10/19 = 52.6% | 19/38 = 50.0% | 4 | 3 |
| Blocks: require unique nonrejected | 9 | 1 | 28 | 9/10 = 90.0% | 10/38 = 26.3% | 12 | 4 |

Warning-only has exactly the original counts for both schemes, by design. All rows have zero execution failures. The three gates increase abstentions; they do not correct errors or introduce new directions. Total abstentions include the original 12; added policy abstentions are respectively 12, 12, 16 for the IID gates and 7, 7, 16 for the block gates.

The 90% row is worth recording as an exploratory selective-accuracy observation, but it does not justify recommending that rule:

- It answers only 10/38 cases and loses four originally correct answers. Correct-answer yield falls from 13/38 (34.2%) to 9/38 (23.7%), while wrong-answer yield falls from 13/38 (34.2%) to 1/38 (2.6%).
- The same strict rule with IID tests retains 6 correct and 4 wrong. The two schemes retain ten cases each, but only five retained cases overlap. The surviving cases cover eight source groups under IID and six under blocks, out of twelve source groups in the panel.
- The block method is an unvalidated row-order heuristic. Its higher accuracy cannot establish that it is the statistically appropriate test for these data.
- Source-weighted directional accuracy is 48.1% originally, 46.0% under the strict IID rule, and 95.4% under the strict block rule. Thus even the IID change from 50% to 60% unweighted accuracy does not persist under the original source weights.
- All outcomes were previously inspected, rules are exploratory, sample sizes are small, sources are clustered, and multiple configurations are reported. We do not choose a winner or claim a general improvement.

For these observed directional answers, the both-rejected and selected-rejected rules happen to yield the same decisions. They are different rules in general; regression tests retain that distinction.

## Pilot: all 17 scheduled cases

The original result is 6 correct, 8 wrong and 3 abstentions: accuracy 6/14 (42.9%), coverage 14/17 (82.4%).

- IID both-rejected and selected-rejected rules: 6 correct, 6 wrong, 5 abstentions; accuracy 50.0%, coverage 70.6%. They remove two wrong answers and lose no correct answers.
- IID unique-nonrejected rule: 4 correct, 5 wrong, 8 abstentions; accuracy 44.4%, coverage 52.9%. It removes three wrong and two correct answers.
- Block both-rejected and selected-rejected rules: 5 correct, 7 wrong, 5 abstentions; accuracy 41.7%, coverage 70.6%. They remove one wrong and one correct answer.
- Block unique-nonrejected rule: 2 correct, 5 wrong, 10 abstentions; accuracy 28.6%, coverage 41.2%. It removes three wrong and four correct answers.

The strict block rule's poor pilot result is retained alongside its favourable later-panel selective accuracy. It is direct evidence against describing that rule as a consistently successful fix in the available records.

## What this adds to the diagnosis

Pair 88's wrong direction is withheld by all three gates under both schemes. Pair 56's wrong direction survives every gate under both schemes. Its wrong direction is not rejected while the reference direction is rejected. This shows why a relative preference plus a nonrejection check still cannot certify causal correctness.

Verified facts: the explicit rules produce the recorded counts and coverage trade-offs; no rule flips answers; warning-only changes no original outcomes; gating can lose correct answers; results depend on diagnostic scheme and panel.

Reasonable interpretation: adequacy annotations are a defensible reporting addition. A conservative gate might be useful in a deliberately selective application, but its usefulness would require a predeclared cost for wrong answers versus withheld correct answers and fresh evaluation. We did not optimize or estimate those costs here.

Unresolved: why every real wrong answer occurs, which sampling model applies to each source, and which rule would generalize. No new independent data was available or acquired, as requested. New held-out validation remains future work, not a completed third chunk.

## Recommendation

Retain the original production ANM for the existing frozen study. Use the new diagnostics and policy results to make limitations and selective-coverage trade-offs visible in research discussion. Do not silently deploy an automatic abstention gate or claim an accuracy improvement from the most favourable row. The strongest additional finding is that **the proposed safeguard is itself fallible and sensitive to the diagnostic scheme; nonrejection and lower dependence do not establish causal correctness**.

## Reproduction and verification

The experiment guide is `docs/experiments/anm-adequacy-policy-comparison-v1.md`; exact tables, all case transitions, source breakdowns, frozen inputs/source and validation logs are in `artifacts/anm-adequacy-policy-comparison-20261121/`. Saved-result replay performs no new numerical experiments. Tests check label-blind policy decisions, no direction flips, p-value boundaries, missing diagnostics, preservation of execution failures, denominators, tamper rejection and byte-identical replay.

This replay is offline diagnostic code. It is not connected to the producer, model runner or checker. Historical report/slides and experiments remain unchanged.
