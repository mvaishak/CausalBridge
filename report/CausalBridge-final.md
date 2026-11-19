---
title: "CausalBridge: structured evidence and verification for LLM causal reasoning"
author: "CausalBridge project team · DSC 261, Fall 2026"
date: "19 November 2026"
---

**Abstract.** We tested whether causal tools and deterministic evidence checks make a local language model's causal answers more reliable. In a 50-question synthetic known-graph pilot, Qwen3:8b released only two answers: one correct and one wrong; all 21 unanswerable questions were abstained on, but 27 answerable questions were also missed. In a separate 17-pair real-data pilot, adding an additive-noise-model (ANM) diagnostic caused the model to copy the method's direction on all 14 answered pairs, including eight benchmark-wrong arrows. The checker rejected five invalidly supported answers outside that condition, sacrificing two benchmark-correct answers, and changed no E4 releases. ANM recovered 26/32 compatible synthetic directions at 512 rows with six abstentions, but on 38 real benchmark pairs it produced 13 correct, 13 wrong and 12 abstentions. The system improves traceability for typed evidence. These experiments do not establish better causal direction accuracy.

## 1. Question and prior work

A directed graph can show a path from X to Y without determining whether raising X raises Y. An observational pair can be compatible with multiple causal mechanisms. CausalBridge asks: **To what extent do structured causal evidence and deterministic verification improve the reliability of LLM causal reasoning?** We operationalize reliability as correct answer or justified abstention for known-graph questions, and benchmark-direction agreement, coverage, evidence integrity and error propagation for real observational pairs. These tasks have different oracles and remain separate.

ANM methods identify direction under assumptions about functional form and independent additive noise; finite-sample fitting and assumption violations matter [1,2]. The Tübingen CauseEffectPairs database supplies reference directions and similarity weights, while warning that its reference labels are not guaranteed correct [3,4]. The [DSC 261 course project standard](https://bsalimi.github.io/dsc261-fa26/) calls for an executable trust claim with explicit failure boundaries [5].

## 2. System and evaluation contract

Track A gives the model a graph, a question and varying visible numerical evidence. A parser chooses the causal query, a planner selects one graph/numerical operation, and a verifier checks the bound tool result and proposed answer. The fixed synthetic benchmark has 50 questions from 10 graph groups, 29 answerable and 21 unanswerable. Its exact witness gives two complete models with the same visible $P(X,Y)=1/4$ in every cell and opposite effects, +0.30 and −0.30. Deterministic tests checked the witness and benchmark export before live inference. The oracle was not sent to the model.

Track B evaluates 17 selected scalar Tübingen pairs in seven source groups. E1 supplies names, E2 supplies anonymized measurements, E3 combines names and measurements, and E4 adds one ANM result. S0 is a base prompt; S1 adds uncertainty instructions. S2 checks the **saved S1** output without another generation. A simple gate and an ANM-only baseline also reuse saved data. Each pair has E1–E4 × S0/S1, producing 136 live generations. The checker binds identities, displayed row and summary citations, and saved ANM requests/results. Its rules do not verify unrestricted prose or causal truth. The frozen ANM uses bidirectional kernel ridge regression and held-out residual HSIC, with a $0.001$ margin threshold; the margin is not a causal probability.

Both live tracks used a local `qwen3:8b` model with pinned digest `500a1f06…3e4ca4b2b8b41`, temperature 0, seed 261 and thinking disabled. Track A used 8192 context/1024 output tokens; Track B used 4096/512. Model requests, raw responses, configuration, token counts, latency and tool traces are archived. No gold reference was placed in model prompts. The Track B run preceded this report; its score file was reproduced byte-for-byte from the archived analysis, mapping and evaluator records. The Track A live run was executed for this delivery on the frozen 50 cases.

## 3. Results

| Panel and strategy | Correct | Wrong | Abstain | Coverage | Answered accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Track A, 50 synthetic questions | 1 | 1 | 48 | 4.0% | 50.0% (2 answers) |
| Track B E3/S0, 17 real pairs | 4 | 4 | 9 | 67.1% weighted | 59.2% weighted |
| Track B E4/S0, S1, S2, gate, ANM-only | 6 | 8 | 3 | 89.0% weighted | 40.0% weighted |
| ANM real validation, 38 pairs | 13 | 13 | 12 | 73.4% weighted | 48.1% weighted |

Track A's 48 abstentions contain 21 correct abstentions and 27 missed answerable cases. Correct-answer yield is 1/50=2%. It made 102 live model stages, with three planning-stage structured-output errors. Only 9/50 parsed query types matched the oracle's intended type. In `G006_sign_complete`, the question asks whether a change in X *increases* Y. The model instead asked for $P(Y=1\mid do(X=1))$ and returned 0.31249. The verifier marked that answer valid for the changed query, while the oracle answer to the original sign question is *negative*. This is a concrete semantic-binding failure. The only correct release was a directed-path question.

Track B's E4 conditions made identical decisions on all 17 pairs: 14 answers, six reference-correct, eight wrong and three abstentions. Its weighted correct-answer yield is 35.6%, wrong-answer yield 53.4%. Relative to matched E3/S0 cases, E4 changed 13 decisions, including four correct arrows becoming wrong and one wrong arrow becoming correct. Weighted correct yield fell 4.1 percentage points, even though unweighted correct yield rose 11.8 points as coverage increased. All 14 answered E4 arrows matched ANM. The checker changed no E4 release. E2/S0's apparent 100% answered accuracy came from only two released answers; its weighted coverage was 32.9%.

The checker reviewed 68 saved S1 proposals. Forty-eight abstained upstream and supplied no typed claims. Of 20 answered proposals, it accepted six benchmark-correct and nine wrong, and rejected two correct and three wrong. The five rejections caught unavailable E1 citations and two E3 displayed-row mismatches. Two strict text/structured-direction mismatches remained outside typed checking. These are process outcomes, not an estimate of causal truth.

The initial 128-row ANM synthetic panel passed numerical reference and column-swap checks but failed its predeclared recovery/stability gate: 20 correct, eight wrong, four abstentions on 32 compatible cases. A new 512-row synthetic confirmation had 26 correct, zero wrong and six abstentions. The fixed real validation used up to 512 rows and gave 13 correct, 13 wrong, 12 abstentions; only 22 of 38 pairs had all 512 observations. The real primary split's raw-margin sign was stable over three splits for 23/38 pairs. The 38 outcomes are now opened and cannot confirm a method revised after inspection.

## 4. Uncertainty, failure boundary and conclusion

Cases share graphs or source families. Exploratory group-bootstrap intervals therefore resample whole groups, not individual rows: Track A coverage 0–12% across 10 graph groups; Track B E4 weighted answered accuracy 12.3–70.6% across seven source groups; real ANM unweighted answered accuracy 27.3–72.7% across 12 groups. We omit a Track A answered-accuracy interval because both answers share one graph group. No significance test supports a positive performance claim. The source-group bootstrap does not account for imperfect reference labels or selection of the pilot cohort.

The synthetic-to-real ANM gap may reflect sample size, dependence, functional mismatch, confounding or labels; these experiments do not isolate one cause. Track A shows that tool correctness cannot repair a changed question. Track B shows that an incorrect diagnostic can propagate through a model even when citations are accurate. Deterministic verification provides a bounded audit trail for typed claims. We found no evidence that the tested structure or checker improved causal direction accuracy. A revised method requires a frozen protocol and a new source-separated holdout.

The raw runs, case-level scores, figure, checker audit and exact reproduction commands are in the repository's `artifacts/final-delivery/` and `docs/reviews/final-reproducibility.md`. The detailed technical reports preserve negative cases and protocol deviations separately from this four-page course report.

**Assistance disclosure.** Codex assisted with the final audit, analysis code and report/presentation drafting. The submitted claims and source records require review by the student team under the applicable Canvas policy.

![Case counts across the distinct Track A, Track B E4 and real ANM panels. Track A abstentions include both justified and missed answers; panels are not pooled.](artifacts/final-delivery/analysis/outcomes.svg){width=90%}

## References

1. P. O. Hoyer, D. Janzing, J. M. Mooij, J. Peters, and B. Schölkopf. [Nonlinear causal discovery with additive noise models](https://proceedings.neurips.cc/paper_files/paper/2008/file/f7664060cc52bc6f3d620bcedc94a4b6-Paper.pdf). *Advances in Neural Information Processing Systems 21*, 2009.
2. J. Peters, J. M. Mooij, D. Janzing, and B. Schölkopf. [Causal discovery with continuous additive noise models](https://jmlr.org/papers/v15/peters14a.html). *Journal of Machine Learning Research* 15:2009–2053, 2014.
3. J. M. Mooij, J. Peters, D. Janzing, J. Zscheischler, and B. Schölkopf. [Distinguishing cause from effect using observational data: methods and benchmarks](https://jmlr.org/papers/v17/14-518.html). *Journal of Machine Learning Research* 17(32):1–102, 2016.
4. Max Planck Institute for Intelligent Systems. [Database with cause-effect pairs](https://webdav.tuebingen.mpg.de/cause-effect/), accessed 2026-11-19.
5. UC San Diego DSC 261. [Responsible Data Science, Fall 2026 course page](https://bsalimi.github.io/dsc261-fa26/), accessed 2026-11-19.
