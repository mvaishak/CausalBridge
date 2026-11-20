---
title: "CausalBridge: structured evidence and verification for LLM causal reasoning"
author: "CausalBridge project team · DSC 261, Fall 2026"
date: "20 November 2026"
---

**Abstract.** We tested whether causal tools and deterministic evidence checks make a local language model's causal answers more reliable. In a 50-question synthetic known-graph pilot, Qwen3:8b released only two answers: one correct and one wrong; it missed 27 answerable questions, including three planning errors. In a 17-pair real-data pilot, adding an additive-noise-model (ANM) diagnostic led the model to copy all 14 answered method directions, including eight benchmark-wrong arrows. A later exploratory 38-pair integrated run likewise copied ANM on every pair: 13 correct, 13 wrong, and 12 without a released direction, including one binding failure. Its checker suppressed three benchmark-correct E4 answers and no wrong E4 answers. ANM recovered 26/32 compatible synthetic directions at 512 rows with six abstentions, but did not transfer reliably to real pairs. Typed evidence became auditable; these experiments do not establish better causal direction accuracy.

## 1. Question and prior work

A directed graph can show a path from X to Y without determining whether raising X raises Y. An observational pair can be compatible with multiple causal mechanisms. CausalBridge asks: **To what extent do structured causal evidence and deterministic verification improve the reliability of LLM causal reasoning?** We operationalize reliability as correct answer or justified abstention for known-graph questions, and benchmark-direction agreement, coverage, evidence integrity and error propagation for real observational pairs. These tasks have different oracles and remain separate.

ANM methods identify direction under assumptions about functional form and independent additive noise; finite-sample fitting and assumption violations matter [1,2]. The Tübingen CauseEffectPairs database supplies reference directions and similarity weights, while warning that its reference labels are not guaranteed correct [3,4]. The [DSC 261 course project standard](https://bsalimi.github.io/dsc261-fa26/) calls for an executable trust claim with explicit failure boundaries [5].

## 2. System and evaluation contract

Track A gives the model a graph, a question and varying visible numerical evidence. A parser chooses the causal query, a planner selects one graph/numerical operation, and a verifier checks the bound tool result and proposed answer. The fixed synthetic benchmark has 50 questions from 10 graph groups, 29 answerable and 21 unanswerable. Its exact witness gives two complete models with the same visible $P(X,Y)=1/4$ in every cell and opposite effects, +0.30 and −0.30. Deterministic tests checked the witness and benchmark export before live inference. The oracle was not sent to the model.

Track B evaluates 17 selected scalar Tübingen pairs in seven source groups. E1 supplies names, E2 supplies anonymized measurements, E3 combines names and measurements, and E4 adds one ANM result. S0 is a base prompt; S1 adds uncertainty instructions. S2 checks the **saved S1** output without another generation. A simple gate and an ANM-only baseline also reuse saved data. Each pair has E1–E4 × S0/S1, producing 136 live generations. The checker binds identities, displayed row and summary citations, and saved ANM requests/results. Its rules do not verify unrestricted prose or causal truth. The frozen ANM uses bidirectional kernel ridge regression and held-out residual HSIC, with a $0.001$ margin threshold; the margin is not a causal probability.

Both live tracks used a local `qwen3:8b` model with pinned digest `500a1f06…3e4ca4b2b8b41`, temperature 0, seed 261 and thinking disabled. Track A used 8192 context/1024 output tokens; Track B used 4096/512. Model requests, raw responses, configuration, token counts, latency and tool traces are archived. No gold reference was placed in model prompts. The original 17-pair Track B score file was reproduced byte-for-byte from archived analysis, mapping and evaluator records. The Track A live run was executed for this delivery on the frozen 50 cases.

After the pilot, the team added a 512-row ANM validation variant and completed real-data roster and scoring checks. A request-level replay found all 136 original pilot prompts, evidence packages and ANM results unchanged under the merged production pipeline. The 17 pilot cases therefore were not regenerated. For an additional matched end-to-end test, we froze the 38 eligible validation-role pairs in 12 disjoint source groups and used the saved 512-row ANM results. Their benchmark outcomes had already been opened by the numerical study, so this larger panel is exploratory rather than an independent holdout.

## 3. Results

| Panel and strategy | Correct | Wrong | No release | Coverage | Answered accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| A50 | 1 | 1 | 48 | 4.0% | 50.0% (2 answers) |
| B17 E3/S0 | 4 | 4 | 9 | 67.1% weighted | 59.2% weighted |
| B17 E4 | 6 | 8 | 3 | 89.0% weighted | 40.0% weighted |
| B38 E3/S0 | 9 | 5 | 24 | 38.2% weighted | 59.3% weighted |
| B38 E4 | 13 | 13 | 12 | 73.4% weighted | 48.1% weighted |
| B38 E4/S2 | 10 | 13 | 15 | 65.3% weighted | 41.7% weighted |
| ANM38 | 13 | 13 | 12 | 73.4% weighted | 48.1% weighted |

`A50` is the synthetic Track A run. `B17` is the original real pilot; `B38` is the exploratory 38-pair panel with opened ANM labels. E4 without `/S2` groups S0, S1, gate and ANM-only, which made the same decisions within each panel. Percentages for Track B and ANM use benchmark weights.

Track A's 48 nonreleases comprise 21 justified abstentions, 24 missed answerable questions without an execution error, and three planning-stage structured-output errors on answerable questions. The scorer's 27 false-abstention label includes those three errors; the operational accounting separates them. Correct-answer yield is 1/50=2%. The run made 102 live model stages. Only 9/50 parsed query types matched the oracle's intended type. In `G006_sign_complete`, the question asks whether a change in X *increases* Y. The model instead asked for $P(Y=1\mid do(X=1))$ and returned 0.31249. The verifier marked that answer valid for the changed query, while the oracle answer to the original sign question is *negative*. This is a concrete semantic-binding failure. The only correct release was a directed-path question.

Track B's E4 conditions made identical decisions on all 17 pairs: 14 answers, six reference-correct, eight wrong and three abstentions. Its weighted correct-answer yield is 35.6%, wrong-answer yield 53.4%. Relative to matched E3/S0 cases, E4 changed 13 decisions, including four correct arrows becoming wrong and one wrong arrow becoming correct. Weighted correct yield fell 4.1 percentage points, even though unweighted correct yield rose 11.8 points as coverage increased. All 14 answered E4 arrows matched ANM. The checker changed no E4 release. E2/S0's apparent 100% answered accuracy came from only two released answers; its weighted coverage was 32.9%.

Adding names to the same numerical evidence (E2→E3, S0) increased weighted correct-answer yield by 6.8 points in the 17-pair pilot and 22.6 points in the 38-pair panel. Wrong-answer yield also rose by 27.4 and 11.8 points, respectively. These are matched descriptive contrasts, not a reliable improvement claim.

On the larger 38-pair panel, E4/S0 and S1 copied ANM on all 38 decisions. Relative to matched E3/S0, E4 increased weighted correct yield by 12.7 points but wrong yield by 22.5 points; answered accuracy fell from 59.3% to 48.1% as coverage rose from 38.2% to 73.4%. The exploratory paired source-group bootstrap interval for the correct-yield difference is −19.9 to +46.3 points. The checker rejected three correct E4 answers for numeric citation errors and no wrong E4 answers. The simple gate made no E4 change. Of the 12 E4/S0 nonreleases, 11 were model abstentions and one was a package-binding failure; E4/S2 adds three checker rejections to those 12. This panel used 512-row ANM artifacts and previously opened benchmark outcomes; it does not confirm a general benefit.

The original checker reviewed 68 saved S1 proposals. Forty-eight abstained upstream and supplied no typed claims. Of 20 answered proposals, it accepted six benchmark-correct and nine wrong, and rejected two correct and three wrong. The five rejections caught unavailable E1 citations and two E3 displayed-row mismatches. In the larger panel it suppressed seven correct and seven wrong answers across packages; one E4 rejection came from four-decimal rounding against a strict 1e−12 numeric tolerance. These are process outcomes, not an estimate of causal truth.

The initial 128-row ANM synthetic panel passed numerical reference and column-swap checks but failed its predeclared recovery/stability gate: 20 correct, eight wrong, four abstentions on 32 compatible cases. A new 512-row synthetic confirmation had 26 correct, zero wrong and six abstentions. The fixed real validation used up to 512 rows and gave 13 correct, 13 wrong, 12 abstentions; only 22 of 38 pairs had all 512 observations. The real primary split's raw-margin sign was stable over three splits for 23/38 pairs. The 38 outcomes are now opened and cannot confirm a method revised after inspection.

## 4. Uncertainty, failure boundary and conclusion

Cases share graphs or source families. Exploratory group-bootstrap intervals therefore resample whole groups, not individual rows: Track A coverage 0–12% across 10 graph groups; original Track B E4 weighted answered accuracy 12.3–70.6% across seven source groups; integrated 38-pair E4 answered accuracy 21.1–76.8% across 12 groups. We omit a Track A answered-accuracy interval because both answers share one graph group. No significance test supports a positive performance claim. Source-group bootstraps do not account for imperfect reference labels, group dependence or selection of the cohorts.

The synthetic-to-real ANM gap may reflect sample size, dependence, functional mismatch, confounding or labels; these experiments do not isolate one cause. IGCI and RECI use different directional asymmetries but also require assumptions [6,7]. We did not select a new method after opening the 38 reference outcomes without a fresh holdout. Track A shows that tool correctness cannot repair a changed question. Track B shows that an incorrect diagnostic can propagate through a model even when citations are accurate. Deterministic verification provides a bounded audit trail for typed claims. We found no evidence that the tested structure or checker improved causal direction accuracy. A revised method requires a frozen protocol and a new source-separated holdout.

The raw runs, case-level scores, figures, checker audit and exact reproduction commands are in `artifacts/final-delivery/` and `docs/reviews/final-reproducibility.md`. The detailed technical reports preserve the interrupted run, negative cases and protocol deviations separately from this course report.

**Assistance disclosure.** Codex assisted with the final audit, analysis code and report/presentation drafting. The submitted claims and source records require review by the student team under the applicable Canvas policy.

## References

1. P. O. Hoyer, D. Janzing, J. M. Mooij, J. Peters, and B. Schölkopf. [Nonlinear causal discovery with additive noise models](https://proceedings.neurips.cc/paper_files/paper/2008/file/f7664060cc52bc6f3d620bcedc94a4b6-Paper.pdf). *Advances in Neural Information Processing Systems 21*, 2009.
2. J. Peters, J. M. Mooij, D. Janzing, and B. Schölkopf. [Causal discovery with continuous additive noise models](https://jmlr.org/papers/v15/peters14a.html). *Journal of Machine Learning Research* 15:2009–2053, 2014.
3. J. M. Mooij, J. Peters, D. Janzing, J. Zscheischler, and B. Schölkopf. [Distinguishing cause from effect using observational data: methods and benchmarks](https://jmlr.org/papers/v17/14-518.html). *Journal of Machine Learning Research* 17(32):1–102, 2016.
4. Max Planck Institute for Intelligent Systems. [Database with cause-effect pairs](https://webdav.tuebingen.mpg.de/cause-effect/), accessed 2026-11-19.
5. UC San Diego DSC 261. [Responsible Data Science, Fall 2026 course page](https://bsalimi.github.io/dsc261-fa26/), accessed 2026-11-19.
6. D. Janzing et al. [Information-geometric approach to inferring causal directions](https://www.sciencedirect.com/science/article/pii/S0004370212000045). *Artificial Intelligence* 182–183:1–31, 2012.
7. P. Blöbaum et al. [Cause-effect inference by comparing regression errors](https://proceedings.mlr.press/v84/bloebaum18a.html). *Proceedings of AISTATS*, PMLR 84:900–909, 2018.
