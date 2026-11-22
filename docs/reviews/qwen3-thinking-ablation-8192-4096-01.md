# Qwen3 thinking ablation at 8192/4096

## Executive verdict

**PARTIAL execution.** All 272 scheduled observations are preserved across 136 matched inputs; 1 have recorded failures. This is an exploratory analysis on the previously opened 17-pair cohort.

## Configuration and provenance

Started at `fb81b96a92c8cc78360276e54bd3d9be0a974e56`. Qwen3:8b digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`. Both thinking settings use temperature 0, seed 261, num_ctx=8192 and num_predict=4096. All original E1–E4 evidence, S0/S1 messages and output schemas are reused exactly. Only think changes within a matched input. Request order alternates off-first and on-first across sorted case/package/style inputs. Original frozen pilot files were not modified.

The service is accessed through the existing SSH tunnel at 127.0.0.1:11435; no authenticated direct compute endpoint was available. Infrastructure snapshots and loaded-model.json record the actual API/runtime and 8192 context allocation. Local free disk space was 23 GiB at preflight. The full request, raw response, separate thinking field, final content, checker result, failure and token/latency values are retained per observation. Separate thinking-token counts are not exposed and were not inferred.

## Thinking activation and preflight

An initial two-request activation check returned separate reasoning only with thinking enabled. The subsequent preflight used eight matched inputs / 16 observations across two opaque cases, E1/E4 and S0/S1. All final answers parsed and bound, all eight thinking-on calls returned reasoning, and no response truncated. The checker sees final structured content only. Activation and preflight calls are separate from the final 272 observations.

## Full 2 × 2 outcomes

Counts below aggregate four evidence packages over 17 pairs: 68 scheduled observations per row. Correctness uses benchmark references. Failures and abstentions remain in every yield denominator. Answered accuracy conditions on valid directional outputs. Rejection is an additional checker decision and may overlap an upstream explicit abstention; it is not counted as a model abstention.

| Style | Thinking | N | Correct | Wrong | Abstain | Failure | Direction accuracy | Answered accuracy | Checker rejected | Correct & released | Released |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0 | False | 68 | 6 | 9 | 53 | 0 | 8.8% | 40.0% | 0 | 6 | 15 |
| S0 | True | 68 | 12 | 8 | 48 | 0 | 17.6% | 60.0% | 0 | 12 | 20 |
| S1 | False | 68 | 6 | 7 | 54 | 1 | 8.8% | 46.2% | 0 | 6 | 13 |
| S1 | True | 68 | 11 | 8 | 49 | 0 | 16.2% | 57.9% | 0 | 11 | 19 |

## Matched comparisons and uncertainty

Whole causal pairs are resampled with replacement (10,000 percentile bootstrap draws, seed 261). Evidence packages from one pair remain together. These intervals are exploratory and do not account for all source-family dependence or uncertain benchmark labels. The 272 observations are not 272 independent causal datasets.

S0: 6 improved, 0 worsened, 62 unchanged; correct-yield difference +8.8 points; pair-bootstrap interval [2.9, 16.2] points.

S1: 5 improved, 0 worsened, 63 unchanged; correct-yield difference +7.4 points; pair-bootstrap interval [1.5, 14.7] points.

Per-evidence exact McNemar counts/p-values are in full-analysis.json; they are unadjusted exploratory checks. A pooled exact McNemar test across repeated evidence packages would ignore dependence and is not used. The style interaction is the difference of paired thinking effects (S1 minus S0): {"difference_of_differences": -0.014705882352941176, "pair_bootstrap_interval": [-0.058823529411764705, 0.029411764705882353]}.

## Evidence strata and overhead

| Style | Think | Evidence | Correct | Wrong | Abstain | Failure | Rejected | Median seconds | Median generated tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0 | False | E1 | 0 | 0 | 17 | 0 | 0 | 6.8 | 111.0 |
| S0 | False | E2 | 0 | 0 | 17 | 0 | 0 | 6.6 | 109.0 |
| S0 | False | E3 | 0 | 1 | 16 | 0 | 0 | 7.2 | 110.0 |
| S0 | False | E4 | 6 | 8 | 3 | 0 | 0 | 11.6 | 142.0 |
| S0 | True | E1 | 1 | 0 | 16 | 0 | 0 | 23.0 | 414.0 |
| S0 | True | E2 | 1 | 0 | 16 | 0 | 0 | 42.5 | 719.0 |
| S0 | True | E3 | 4 | 0 | 13 | 0 | 0 | 36.3 | 610.0 |
| S0 | True | E4 | 6 | 8 | 3 | 0 | 0 | 43.8 | 709.0 |
| S1 | False | E1 | 0 | 0 | 17 | 0 | 0 | 6.9 | 111.0 |
| S1 | False | E2 | 0 | 0 | 17 | 0 | 0 | 6.6 | 109.0 |
| S1 | False | E3 | 0 | 0 | 17 | 0 | 0 | 6.8 | 108.0 |
| S1 | False | E4 | 6 | 7 | 3 | 1 | 0 | 16.5 | 217.0 |
| S1 | True | E1 | 1 | 0 | 16 | 0 | 0 | 29.0 | 479.0 |
| S1 | True | E2 | 0 | 0 | 17 | 0 | 0 | 37.9 | 643.0 |
| S1 | True | E3 | 4 | 0 | 13 | 0 | 0 | 45.6 | 707.0 |
| S1 | True | E4 | 6 | 8 | 3 | 0 | 0 | 42.7 | 639.0 |

## E4 diagnostic propagation

Disagreement with ANM is not by itself evidence of improvement. The transitions below retain reference correctness, upstream ANM direction, failures and checker decisions.

S0 think=False: among 8 benchmark-wrong ANM inputs, 8 copied the wrong ANM direction and 0 gave a benchmark-correct answer. Full case records also retain abstentions and failures.

S0 think=True: among 8 benchmark-wrong ANM inputs, 8 copied the wrong ANM direction and 0 gave a benchmark-correct answer. Full case records also retain abstentions and failures.

S1 think=False: among 8 benchmark-wrong ANM inputs, 7 copied the wrong ANM direction and 0 gave a benchmark-correct answer. Full case records also retain abstentions and failures.

S1 think=True: among 8 benchmark-wrong ANM inputs, 8 copied the wrong ANM direction and 0 gave a benchmark-correct answer. Full case records also retain abstentions and failures.

## Checker outcomes and case-level transitions

Every valid final response in this experiment supplied claims=[]. Zero checker rejections is therefore vacuous for typed citation checking: no nonempty claim list was tested. Correct-and-released counts mean benchmark-correct answers passed the implemented release policy; they do not establish evidentiary support for the causal conclusion. Checker reason-code counts are stratified in full-analysis.json. Invalid citations, unavailable evidence and numeric mismatches are distinct from causal correctness. The checker permits an accurately attributed disagreement with ANM. Arbitrary natural-language reasoning/explanation contradictions are not automatically adjudicated by the typed checker; this study does not claim an exhaustive semantic contradiction rate. All 136 transitions, including underlying directions, are in full-transitions.json; full-case-results.json includes reference direction and checker results after inference.

## Historical pilot comparison

The original pilot used thinking off, context 4096 and output 512. The new off condition changes both token budgets, so differences versus the original cannot be assigned to thinking. Model digest, archived messages, schema and evidence are unchanged. Original E4/S0 and S1 had 6 correct, 8 wrong and 3 abstentions of 17. The new matched on/off comparisons, rather than historical differences, estimate the exploratory thinking effect.

## Interpretation, limitations and next experiment

Interpret the point differences alongside pair-bootstrap intervals, wrong-answer yield, abstentions and checker rejections. A rise in answered accuracy with reduced coverage is not a general improvement. Benchmark directions remain fallible references. One model, one seed, an opened cohort, repeated evidence conditions and source dependence limit generalization. Ordering is balanced overall, but sorted S0 inputs are off-first and S1 inputs are on-first; this limits causal interpretation of the style interaction and latency contrasts. Thinking traces are recorded outputs, not a validated explanation of internal cognition. The next confirmatory study should freeze a matched thinking protocol with order counterbalanced within each prompt style, and a preregistered nonempty-citation or independent evidence-quality assessment, before collecting an untouched source-separated real cohort; use development cases to choose any prompt or budget change.

## Reproduce

Run `uv run python scripts/analyze_thinking_ablation.py --phase full` followed by `uv run python scripts/report_thinking_ablation.py` to replay the saved predictions/checks and regenerate this report. New inference uses `scripts/qwen3_thinking_ablation.py`; never reuse or overwrite the original pilot. Raw evidence is under `runs/qwen3-thinking-ablation-8192-4096-01/`.

## Final interpretation and validation

Thinking increased observed correct-direction yield on this opened cohort: +6/68 S0 and +5/68 S1, with no correct answer becoming incorrect. The gains occurred outside E4. It did not correct any of the eight benchmark-wrong ANM directions in either prompt style. The S1 wrong-answer count increased by one because thinking-on returned a wrong direction where off truncated; this is an execution/release difference, not a successful challenge to ANM.

Evidence reliability did not demonstrably improve: all 271 valid final predictions had empty claim lists, so there were zero evaluated nonempty typed claim lists and zero citation rejections in every cell. Natural-language reasoning was retained, but its faithfulness and unrestricted contradictions were not independently adjudicated. Checker-accepted release is an operational metric, not proof that a causal direction is supported.

The completed dataset has 272 saved raw responses, 136 matched request identities and 135 matches with two valid final predictions. One S1-Off/E4 response (D1028) exhausted all 4096 output tokens; it remains an execution failure, not an abstention. All 136 thinking-on responses returned separate reasoning; no thinking-off response did.

Source-family sensitivity (seven groups) widens the exploratory difference intervals: {"S0": {"groups": 7, "interval": [0.009615384615384616, 0.21153846153846154]}, "S1": {"groups": 7, "interval": [0.0, 0.19047619047619047]}}. The per-package E3 exact McNemar p-value is 0.125 for both styles; all other per-package values are 1.0. Small grouped samples, unadjusted exploratory analyses and ordering prevent a confirmatory generalization claim.

Historical unweighted comparison (68 scheduled inputs per style): original S0 had 14 correct, 15 wrong and 39 abstentions; original S1 had 8 correct, 12 wrong and 48 abstentions. New Off has 6 correct in each style. The historical-to-new change in budget and potentially runtime conditions cannot be attributed to thinking. The positive thinking contrast refers only to the new 8192/4096 matched experiment.

Reproduction order: `uv run python scripts/analyze_thinking_ablation.py --phase full`, `uv run python scripts/report_thinking_ablation.py`, then `uv run python scripts/verify_thinking_ablation.py`. The final verifier independently recounts raw replies and checks frozen source hashes, identities, budgets and request equality. Original pilot archives remain unchanged. No changes were committed, pushed or merged.

## Aggregate latency and generated-token overhead

| Thinking | Responses | Median seconds | Summed client seconds | Median generated tokens | Total generated tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| False | 136 | 6.99 | 1422.92 | 111.0 | 21498 |
| True | 136 | 37.52 | 5742.86 | 632.5 | 94812 |

The API generated-token count is retained as exposed; it is not partitioned into reasoning and final-answer tokens. Summed request latency is not full pipeline wall time. Empty claim lists make the zero citation-rejection count uninformative about nonempty citation quality. Transport used a 900-second timeout equally in every cell; this is recorded in the execution script and its frozen hash.

Software validation: 1,027 tests passed with two snapshot-dependent skips; lint, formatting, deterministic demos, ANM handshake and package builds passed. The independent raw verifier also passed. See final-software-validation.log in the run directory.
