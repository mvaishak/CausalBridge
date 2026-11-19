# Final Track B evaluation

The November 14 pilot is a verified live `qwen3:8b` run on 17 selected Tübingen CauseEffectPairs in 7 source groups. Its native journal contains 136 generations (17 pairs × E1–E4 × S0/S1), exact messages, raw Ollama payloads and token counts. S2 is a cached deterministic check of each S1 proposal. The simple gate and ANM-only baseline also reuse saved outputs. No new model calls were needed for this final analysis.

The original run is archived unchanged at `artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip`. The final branch's scorer reproduced `pilot-scores.json` byte for byte from the saved analysis, evaluator records and mapping. The existing case-level independent audit is copied to `artifacts/final-delivery/track-b-diagnostics/`.

## Matched pilot results

Counts below are unweighted; percentages use the roster's benchmark weights. Every row has all 17 pairs in its denominator. `S2` is a release decision on saved `S1`, not a separate LLM answer.

| Evidence / strategy | Correct | Wrong | Abstain | Weighted coverage | Weighted answered accuracy | Weighted correct yield |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E1 / S0 | 2 | 3 | 12 | 28.8% | 19.0% | 5.5% |
| E1 / S1 | 2 | 1 | 14 | 23.3% | 29.4% | 6.8% |
| E1 / S2 | 0 | 0 | 17 | 0% | undefined | 0% |
| E2 / S0 | 2 | 0 | 15 | 32.9% | 100% | 32.9% |
| E2 / S1 or S2 | 0 | 0 | 17 | 0% | undefined | 0% |
| E3 / S0 | 4 | 4 | 9 | 67.1% | 59.2% | 39.7% |
| E3 / S1 | 0 | 3 | 14 | 24.7% | 0% | 0% |
| E3 / S2 | 0 | 1 | 16 | 4.1% | 0% | 0% |
| E4 / S0, S1, S2, simple gate, ANM-only | 6 | 8 | 3 | 89.0% | 40.0% | 35.6% |

E2/S0's 100% answered accuracy refers to only two answers. Its coverage is 32.9% weighted and 11.8% by pair count. E4 has 53.4% weighted wrong yield. Across all 17 matched E4 cases, S0, S1, S2, simple gate and ANM-only make identical directional decisions. The observed model copied ANM's direction in all 14 answered E4 cases for each S0 and S1, including 8 benchmark-wrong arrows. The checker did not change E4 release outcomes.

E3→E4 changes 13 of 17 S0 decisions: 4 correct arrows become wrong, 1 wrong becomes correct, 5 abstentions become correct, 2 become wrong, and 1 wrong becomes an abstention. E4 raises coverage by 35.3 percentage points unweighted. The benchmark-weighted correct yield falls by 4.1 points relative to E3/S0, while unweighted correct yield rises by 11.8 points. These different summaries reflect source weighting and changed answer sets; neither identifies a general benefit. The exact transition rows are in `artifacts/final-delivery/track-b-diagnostics/matched-summary.json` and the original archive.

The frozen roster assigns 12 other pairs from pilot families to the pilot split but excludes them from the 17 selected live cases. The 38-pair ANM validation uses distinct pairs and source groups. Model outcomes on that 38-pair panel were not collected, so the real ANM validation cannot be presented as an LLM holdout.

## Evidence integrity and limits

The checker examined 68 S1 proposals. It suppressed five answered outputs in E1/E3: three benchmark-wrong and two benchmark-correct. It passed all 17 E4 checks, releasing the 14 answered E4 proposals. See `final-checker-evaluation.md` for the process confusion table and limitations.

The exploratory threshold .001 was not calibrated. The pilot has one model, one generation per pair/condition, and seven source groups. The reference arrows are benchmark scoring references; unobserved confounding, measurement rounding and source dependence can invalidate a causal interpretation. The model's short `reason_code` is not a rich independent explanation. This is evidence about the tested cohort and protocol, not a universal claim about causal inference.
