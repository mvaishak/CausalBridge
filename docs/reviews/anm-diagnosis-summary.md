# Consolidated ANM diagnosis

This summary separates established results from candidate explanations. It covers the saved-data audit, controlled synthetic study, real residual-spread study, estimator robustness check and independent numerical/decision audit. These analyses reuse opened data. They are diagnostic research, not independent held-out confirmation or evidence of a deployed accuracy improvement.

## What is established

| Question | Evidence | Bounded finding |
|---|---|---|
| Does this implementation reproduce the mathematical calculation? | All 110 fixed-original-residual HSIC reference checks passed. Independent eigensolver fits changed zero of 55 real decisions. | Arithmetic differences found in this audit do not explain the observed categorical errors. This is not a proof of correctness on all inputs. |
| Can an ANM assumption violation produce failures? | At 256 training / 256 evaluation observations, the independent-additive synthetic condition gave 24 correct, 0 wrong, 0 abstentions. A paired cause-dependent-noise condition gave 2 correct, 17 wrong, 5 abstentions. Using the known forward mean still gave 2 correct, 16 wrong, 6 abstentions. | One specified assumption mismatch can break the fixed method, even without forward mean-estimation error. This does not identify every real-data failure's cause. |
| Do particular real failures have a compatible spread pattern? | Pairs 56 and 88 retain changing residual spread under four fixed mean estimators, raw/mean-corrected residuals and IID/heuristic-block checks. | Their pattern does not depend on one original mean-estimator setting. Structural noise variation remains a candidate, not a proved root cause. |
| Is that spread pattern a universal explanation or error classifier? | Correct/abstaining later-panel cases also flag. Persistent wrong cases 91, 92 and 108 have no robust primary spread flag across all checks. | No universal spread-based explanation or reliable correctness detector was established. |
| Does the decision rule check model adequacy? | It compares HSIC scores and a margin threshold; it does not require residual independence. Both directions reject in pilot pair 88, but the method releases a benchmark-wrong direction. | Relative preference can be released where both fitted models show evidence of mismatch. |
| Would checking the chosen direction catch every wrong answer? | In pair 56, the reference B→A rejects (IID p=0.0005), while the chosen wrong A→B does not (p=0.4305). | Nonrejection does not establish the right causal direction. A simple adequacy gate cannot solve every observed error. |
| Would an adequacy gate remove only errors? | In the primary 38-pair panel, both directions reject at nominal p≤0.025 each in 5/13 wrong and 7/13 correct cases under IID checks. Block sensitivity changes the counts. | An automatic gate can lose correct answers. Its accuracy/coverage trade-off requires explicit evaluation. |

## What does not fully explain the failures

- Numerical solver and score differences: small discrepancies occurred, but none changed the 55 audited decisions. Near-tie bandwidth sensitivity deserves separate robustness work, not attribution of all wrong answers.
- Regression error alone: the synthetic mismatch persisted with the known forward mean. The real estimator check also retained candidate spread patterns where held-out prediction MSE fell. Other mean errors remain possible.
- One unlucky split alone: 9/13 primary wrong cases changed raw-margin sign across three saved splits, while others stayed wrong. Repeated splits are not new datasets.
- Small sample size alone: larger samples helped under suitable synthetic assumptions, but did not automatically resolve a mismatch. Real sample-size comparisons are confounded by source family.
- Repeated values alone: ties were not a blanket separator of real correct and wrong outcomes. This does not imply they have no effect.
- Four development pairs alone: shared settings were assessed on only four pairs, which is weak calibration evidence. Each evaluation pair nevertheless supplies its own regression training observations. We did not train one synthetic/global regression and transfer it to the real panel.

Do not rephrase these as factors that have no effect. The evidence says they are insufficient as sole explanations.

## Scope and scientific limits

The primary ANM outcomes remain pilot 6 correct / 8 wrong / 3 abstentions (17 pairs), and later panel 13 correct / 13 wrong / 12 abstentions (38 pairs). These ANM outcomes are distinct from LLM release/checker outcomes. Neither panel is a fresh holdout for these follow-ups. Benchmark directions are reference labels, not direct intervention evidence in every source dataset.

Real residual tests are nominal, approximate diagnostics with uncertain sampling dependence and finite power. Saved-order block permutations are only a heuristic. Multiple analyses and deliberately selected target cases preclude confirmatory interpretations. Absence of rejection is not proof of independence. A regression residual is not an observed structural disturbance.

Four development datasets are insufficient to establish broad calibration reliability. Expanding them would help assess settings, but no experiment here shows that their number caused poor performance or that additional calibration alone will fix it. Without stronger source information or new data, a unique causal explanation of every real error cannot be established.

## Conclusion and next bounded task

The defensible diagnosis is **a relative dependence preference is insufficient to guarantee causal direction when assumptions or fitted models are unsuitable**. We demonstrated a controlled failure mechanism and identified real cases compatible with model mismatch, while constraining numerical explanations. We did not establish a universal real-data root cause or a validated repair.

The next local task is a frozen, exploratory replay comparing annotations and conservative abstention rules on these saved adequacy records. It must retain historical predictions, distinguish original abstention from added policy withholding, report every fixed rule, and measure both errors removed and correct answers lost. Do not choose a winning deployment rule from the opened panel. New held-out validation remains outside the currently authorized scope.

## Evidence

- [Saved-data diagnosis](anm-failure-diagnosis.md)
- [Controlled mechanism study](anm-mechanism-study-v1.md)
- [Real residual-spread study](anm-real-noise-v1.md)
- [Mean-estimator robustness](anm-mean-robustness-v1.md)
- [Independent numerical/decision audit](anm-decision-audit-v1.md)

Each component links to its raw/source bundles and reproducibility checks. Original production ANM, final report, slides and frozen experimental results are unchanged.

## Completed exploratory policy follow-up

The fixed replay is now completed; see [adequacy-rule comparison](anm-adequacy-policy-comparison-v1.md). It reports every rule and confirms that apparent selective-accuracy gains depend on scheme and coverage. No production change or general improvement was established. New-data validation was not undertaken.
