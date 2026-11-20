# Final integrated Track B evaluation on the opened 38-pair panel

## Scope and protocol

This is a matched exploratory extension to the frozen 17-pair pilot. The 38 Tübingen pairs have 12 source groups disjoint from the pilot's seven, and all satisfy the final roster's scalar, row-count, variation, weight, and source-review eligibility checks. The 38 benchmark reference outcomes were already opened for Anish's numerical ANM validation. There is no untouched eligible source-separated panel in the pinned snapshot. These new LLM responses are genuine, but the panel cannot be described as an independent post-selection holdout.

The frozen protocol is `configs/final-track-b-integrated-38.json`. It uses the PR #15 `sample_512` ANM artifacts with exact sample/config/mapping binding, reviewed variable names from source descriptions, E1–E4 evidence, S0/S1 live inference, S2 deterministic verification of saved S1 outputs, the simple gate, and ANM-only. Every pair has all 17 scored package/condition combinations. The same pinned `qwen3:8b` digest, temperature, seed, context, and output budget as the 17-pair pilot were used. The 17-pair pilot used a 128-row ANM variant; its metrics and the 38-pair metrics describe different panels and method-input sizes. The new name mapping was prepared after the benchmark outcomes were opened, although the mapping records variable descriptions rather than direction labels; this is another reason not to treat the panel as blinded confirmation.

## Execution provenance

The 38-pair scripted integration run passed before live inference. A one-pair live smoke passed with eight actual calls. The first full-panel attempt saved 51 successful live responses before an SSH tunnel loss; its remaining 253 scheduled records are transport failures and are excluded from scientific scoring. The resumed full-panel journal reuses those 51 exact raw responses only after matching the complete messages, schema, model configuration, and request fingerprint. It makes the remaining 253 model calls against the pinned local endpoint. The separate provenance log labels every saved or new response. Raw journals from both attempts are preserved; no model reply is synthesized.

The `scripts/verify_integrated_live_provenance.py` command must pass before interpreting the resumed panel. `scripts/analyze_final_track_b_38.py` computes case-level decisions, benchmark-weighted scores, paired E3→E4 differences, source-group bootstrap intervals, and checker suppression counts only from a complete real-model run. The bootstrap intervals are exploratory and do not account for imperfect reference directions or potential cross-group dependence.

## Matched results

The native audit and independent provenance audit passed. The complete panel has 304 real-model responses: 51 exact saved-live responses from the interrupted attempt and 253 new live generations in the resumed journal. Three connection retries had no accepted response and are logged separately. The final endpoint still reported the same pinned model digest. The scorer joined the reference directions only after the responses were complete. There are 152 deterministic S2 checks and no new S2 model calls.

Counts are unweighted; percentages use benchmark weights. Each row has all 38 pairs in its denominator. `Answered accuracy` is conditional on a released direction; `correct yield` is correct released weight divided by all panel weight.

| Strategy | Correct | Wrong | No release | Weighted coverage | Answered accuracy | Correct yield |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E1 / S0 | 9 | 8 | 21 | 42.4% | 58.9% | 25.0% |
| E1 / S1 | 4 | 6 | 28 | 21.1% | 30.7% | 6.5% |
| E1 / S2 | 0 | 0 | 38 | 0% | Undefined | 0% |
| E2 / S0 | 0 | 2 | 36 | 3.7% | 0% | 0% |
| E2 / S1 or S2 | 0 | 0 | 38 | 0% | Undefined | 0% |
| E3 / S0 | 9 | 5 | 24 | 38.2% | 59.3% | 22.6% |
| E3 / S1 | 2 | 4 | 32 | 19.7% | 56.4% | 11.1% |
| E3 / S2 | 2 | 3 | 33 | 18.4% | 60.5% | 11.1% |
| E4 / S0, S1, simple gate, ANM-only | 13 | 13 | 12 | 73.4% | 48.1% | 35.3% |
| E4 / S2 checker | 10 | 13 | 15 | 65.3% | 41.7% | 27.3% |

E4/S0, E4/S1, the simple gate, and ANM-only agreed on **all 38** released directions and nonreleases, but their nonrelease reasons differ. Every answered E4/S0 direction copied the ANM result. The 13 benchmark-wrong arrows therefore propagated without a correction from the model. E4/S2 suppressed three benchmark-correct E4/S1 answers and no benchmark-wrong E4/S1 answers, reducing weighted answered accuracy from 48.1% to 41.7% and correct yield from 35.3% to 27.3%. A separate E4 S0/S1 case, D1016, failed case/package binding because the model copied one character of the package digest incorrectly; it was a binding failure, not a model abstention, and contributed to the failure count.

Compared on exactly the same cases, E4/S0 had 12 more answers than E3/S0. Nine E3 abstentions became correct E4 answers, but six became wrong answers; five E3 correct arrows became wrong E4 arrows and two wrong arrows became correct. Weighted coverage rose 35.2 percentage points; correct yield rose 12.7 points, while wrong yield rose 22.5 points and answered accuracy fell from 59.3% to 48.1%. The exploratory 12-source-group bootstrap interval for the paired correct-yield difference is **−19.9 to +46.3 points**; for coverage it is +13.7 to +59.5 points. The interval does not support a reliable positive direction-accuracy claim. Weighted E4/S0 answered accuracy has a wide exploratory source-group interval of 21.1–76.8%; the E3/S0 interval is 21.1–100%. These intervals do not model imperfect benchmark directions or broader dependence among source families.

## Evidence verification and concrete failures

Across 152 S1 proposals, 42 contained a direction. S2 released 28 and suppressed 14: seven benchmark-correct and seven benchmark-wrong. Ten suppressions were E1 claims that cited method, row, or summary evidence absent from E1. One E3 row citation and three E4 numeric citations failed. Two E4 cases had wrong summary values; one cited the adjacent displayed row. The remaining 109 upstream abstentions passed the checker without a direction, and one S1 proposal with a malformed package digest could not be checked as a valid parent prediction. The simple gate made no E4 change.

The three E4 suppressions demonstrate the distinction between evidence integrity and directional accuracy. In D1019 (benchmark pair 80), the model cited a displayed standard deviation of 230.123 where the package supplied 280.123. In D1063 (pair 79), it cited row 14's values but gave the values of row 13. Both rejections enforce the exact typed evidence contract. In D1018 (pair 33), the model rounded standard deviations to four decimal places; the checker uses a 1e−12 relative/absolute tolerance and rejected the rounded citation. That is a documented precision cost of this strict policy, not evidence that the direction was wrong. All three proposed directions agreed with their benchmark references, so the checker improved citation exactness while losing correct directional coverage.

D1075 (pair 102, Janzing mechanics) shows diagnostic error propagation. With E3/S0, the model chose `B_to_A`, agreeing with the benchmark direction from ball starting position to first-barrier transit time. E4/S0 supplied the ANM preference `A_to_B` (margin 0.002144); the model changed to `A_to_B`, cited the method, and became benchmark-wrong. The evidence summary stayed the same. The checker accepted the method citation because it faithfully described the saved ANM result; it cannot establish whether that result is causally correct.

## Relation to the original pilot

The original 17-pair E4 comparison used 128 ANM rows and found 6 correct, 8 wrong, 3 abstentions; E4 correct yield fell 4.1 weighted points relative to E3/S0, and S2 changed no E4 releases. The new 38-pair panel uses up to 512 rows and finds 13 correct, 13 wrong, and 12 without a release (11 model abstentions and one binding failure in E4/S0); E4 correct yield rises 12.7 points relative to E3/S0, but its answered accuracy is lower and the paired interval spans zero. S2 now rejects three correct E4 arrows. The direction of the correct-yield contrast differs between panels. Both panels show complete E4 model copying of ANM and no evidence that the checker repairs wrong diagnostic directions. They differ in source groups, sample sizes, and prior exposure of labels, so neither is a replication of the other's effect estimate.

Source data: `artifacts/final-delivery/postmerge-track-b/integrated-38-resumed-live.tar.gz`, `integrated-38-provenance-audit.json`, and `integrated-38-analysis/` (case results, metrics, and vector figure). The interrupted run is preserved separately and is not included in these scores.
