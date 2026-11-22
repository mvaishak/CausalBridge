# ANM failure diagnosis: saved-data investigation

## Verdict

The saved evidence supports multiple failure modes, not one established root cause. Some wrong arrows are split-sensitive; others remain wrong. Sample size is associated with outcomes but mostly confounded with source family. Ties alone do not explain the errors. Neither split stability nor residual-dependence ranking establishes causal truth.

Verified 7,125 archived files, 210 saved real attempts and 352 saved synthetic attempts. No new ANM fits, permutations, LLM calls or threshold selection. Repeated attempts are not independent datasets.

## 1. The real-data result is reproduced

Counts are correct / wrong / abstention / execution failure. Every seed retains the same 38 pairs in 12 source groups; only the training/evaluation split changes.

| Split | C / W / A / F | Directional accuracy | Coverage |
|---|---|---|---|
| 261 | 13 / 13 / 12 / 0 | 13/26 | 26/38 |
| 1261 | 20 / 7 / 11 / 0 | 20/27 | 27/38 |
| 2261 | 14 / 9 / 15 / 0 | 14/23 | 23/38 |

Primary seed 261: 50% unweighted answered accuracy; weighted correct and wrong yields are 35.3% and 38.1% of total weight 10.8, giving weighted answered accuracy 48.1%. These agree with the frozen ANM-only result. Model execution failures from the separate LLM pipeline must not be inserted into ANM counts.

## 2. Some wrong directions are unstable; others persist

Among 13 primary wrong cases, 4/13 keep the same nonzero raw-margin sign across all three splits. In contrast, 12/13 primary correct cases do so. Raw sign stability differs from decision stability because the fixed threshold can turn a small signed margin into abstention.

Only 3/13 primary wrong cases become correct on at least one saved split. 3/13 remain wrong on every split. Therefore, changing a random seed sometimes changes the result, but repeated agreement can preserve an incorrect direction. No favorable seed is substituted for the primary seed.

## 3. Sample size matters in compatible simulations; the real association is confounded

| Real primary stratum | N | C / W / A / F | Answered accuracy |
|---|---:|---|---|
| full_512 | 22 | 9 / 3 / 10 / 0 | 9/12 |
| fewer_than_512 | 16 | 4 / 10 / 2 / 0 | 4/14 |

Only these source groups contain both full and shorter samples: **pima_diabetes**. Most of the size comparison also changes source/mechanism. It does not show that collecting more observations would fix the real wrong cases.

The cached synthetic comparison uses the same generated dataset IDs at both sizes. Selected 128-row samples are nested in the 512-row samples for all 32 compatible datasets in each partition. Both training and evaluation sample sizes change, so regression learning and HSIC finite-sample effects are not separated.

| Synthetic partition, primary split | Rows | C / W / A / F |
|---|---:|---|
| development | 128 | 20 / 8 / 4 / 0 |
| development | 512 | 24 / 0 / 8 / 0 |
| confirmation | 128 | 20 / 7 / 5 / 0 |
| confirmation | 512 | 26 / 0 / 6 / 0 |

- development: 6 wrong → correct, 2 wrong → abstention, 5 correct → abstention. Larger samples removed wrong releases here but did not retain every correct answer.
- confirmation: 5 wrong → correct, 2 wrong → abstention, 4 correct → abstention. Larger samples removed wrong releases here but did not retain every correct answer.

This is evidence of finite-sample sensitivity under the tested synthetic construction. It does not identify the source of real-data failure. Known nonidentified/assumption-violation controls have null causal accuracy, not manufactured correct/wrong labels.

## 4. Repeated values are not a sufficient explanation

The descriptive cutoff is a largest tied value occupying at least 10% of either selected column. It is a post-outcome audit bin, not a tuned exclusion rule.

| Tie stratum | N | C / W / A / F |
|---|---:|---|
| tie_at_least_10pct | 21 | 7 / 6 / 8 / 0 |
| tie_below_10pct | 17 | 6 / 7 / 4 / 0 |

Both strata contain correct and wrong answers. These counts do not support a blanket claim that ties caused the failure. Exact-row overlap across a split is reported descriptively; without original unit IDs it cannot establish leakage or that repeated values came from the same physical observation.

## 5. Margin and fit quality do not certify a direction

On the 38-pair panel, median absolute margin is 0.004398 for correct releases and 0.002594 for wrong releases. The descriptive correct-versus-wrong rank AUC is 0.669. This suggests some ranking information here, not a calibrated confidence measure. It must not be conflated with the original 17-pair pilot's different margin result. No margin cutoff is selected. Leave-one-source-out AUC values are in metrics.json; they are sensitivity checks, not independent replications.

In 5/13 wrong primary cases, the reference direction has lower held-out standardized prediction MSE than the opposite direction, yet ANM chooses the wrong direction. Production chooses lower residual dependence, not lower prediction error. This pinpoints a ranking disagreement; MSE itself is not a causal-direction oracle.

The separate cached four-pair development adequacy study gives more detail:

| Pair | Reference MSE | Opposite MSE | Cached permutation-test outcome |
|---|---:|---:|---|
| 12 | 0.909 | 1.351 | one_direction_not_rejected |
| 17 | 3.064 | 1.152 | one_direction_not_rejected |
| 93 | 0.509 | 0.315 | both_rejected |
| 99 | 0.610 | 1.091 | both_not_rejected |

Pairs 12 and 17: only the benchmark-wrong direction was not rejected. Pair 93: both directions rejected. Pair 99: neither direction rejected. Nonrejection is not proof of independence, and permutations assume exchangeability. These tests cover only four development pairs; their results cannot be assigned to all 38 validation cases. The existing parameter comparisons and adequacy gate did not establish a reliable real-data method; they are not newly tuned here.

## 6. Source families and every primary wrong case

Small groups and different sample sizes prevent a general domain-ranking claim.

| Source | N | C / W / A / F | Selected sizes |
|---|---:|---|---|
| abalone | 7 | 2 / 2 / 3 / 0 | 512 |
| concrete | 8 | 3 / 1 / 4 / 0 | 512 |
| cpus | 1 | 1 / 0 / 0 / 0 | 209 |
| janzing_brightness | 1 | 1 / 0 / 0 / 0 | 300 |
| janzing_mechanics | 4 | 0 / 3 / 1 / 0 | 109, 202 |
| janzing_temperature | 1 | 0 / 1 / 0 / 0 | 112 |
| janzing_voltage | 1 | 0 / 1 / 0 / 0 | 114 |
| liver_disorders | 5 | 2 / 3 / 0 / 0 | 345 |
| moffat_ecosystem | 3 | 3 / 0 / 0 / 0 | 512 |
| pima_diabetes | 4 | 1 / 0 / 3 / 0 | 394, 512 |
| solly_soil | 2 | 0 / 2 / 0 / 0 | 149, 150 |
| spatial_econometrics | 1 | 0 / 0 / 1 / 0 | 512 |

| Pair | Source | N | Absolute margin | Outcomes 261 / 1261 / 2261 |
|---|---|---:|---:|---|
| 108 | janzing_temperature | 112 | 0.019130 | wrong / wrong / wrong |
| 35 | liver_disorders | 345 | 0.008709 | wrong / abstention / wrong |
| 36 | liver_disorders | 345 | 0.005582 | wrong / correct / wrong |
| 6 | abalone | 512 | 0.003966 | wrong / abstention / abstention |
| 37 | liver_disorders | 345 | 0.003660 | wrong / wrong / abstention |
| 10 | abalone | 512 | 0.002601 | wrong / abstention / abstention |
| 97 | janzing_mechanics | 202 | 0.002594 | wrong / abstention / wrong |
| 91 | solly_soil | 149 | 0.002545 | wrong / wrong / wrong |
| 102 | janzing_mechanics | 109 | 0.002144 | wrong / correct / abstention |
| 104 | janzing_mechanics | 109 | 0.001803 | wrong / correct / wrong |
| 25 | concrete | 512 | 0.001779 | wrong / abstention / abstention |
| 106 | janzing_voltage | 114 | 0.001755 | wrong / wrong / abstention |
| 92 | solly_soil | 150 | 0.001668 | wrong / wrong / wrong |

## 7. Source context for the three persistently wrong cases

The two soil pairs share a source family; these are three cases from two families, not three independent source replications. The following are manual paraphrases of source descriptions checked against the pinned file hashes. Full description digests and unresolved questions are in metrics.json.

- Pair 91 (pair0091_des.txt): Clay content and soil moisture at 10 cm were measured in forest plots. The source describes 150 plots and exclusion of missing-data plots. Clay is described as one determinant of water retention. Adjacent selected-row correlations for runtime A/B: 0.814, 0.681. Omitted determinants, spatial dependence and missing-data selection could matter; none is established as the cause of this wrong arrow.
- Pair 92 (pair0092_des.txt): Organic carbon content and clay content were measured in forest plots. The source describes 150 plots and exclusion of missing-data plots. The source identifies clay as a determinant of carbon accumulation. Adjacent selected-row correlations for runtime A/B: 0.815, 0.746. This shares the soil source family with pair 91; it is not an independent source replication. Missingness, shared causes and spatial dependence are hypotheses, not demonstrated causes.
- Pair 108 (pair0108_des.txt): The variables are duration of one sixth of an engine rotation and heat-bath temperature. The rotation-duration measurement represents inverse velocity. The source describes a hot-water-driven engine and temperature-sensor measurements recorded in 2017. Adjacent selected-row correlations for runtime A/B: 0.547, 1.000. Sequential dependence and nonlinear measurement effects are plausible questions; no observation-time IDs or direct assumption test establish the decisive cause.

Adjacent-row correlations describe the saved source-row order, which can have unequal spacing. Values are rounded to three decimals. Without unit/time IDs, correlation does not establish serial dependence, leakage or its causal role in the error. These metadata observations motivate targeted tests; they are not diagnosed assumption violations.

## 8. What is verified, suggested and unresolved

**Verified:** archive integrity, request/sample/configuration and column mapping bindings, threshold arithmetic, split indices, training-only means/scales, reproducibility digests, and cached residual-moment/MSE consistency. All scheduled attempts are retained. This found no such preparation/accounting defect in the audited records; it is not a fresh independent KRR/HSIC reconstruction. Mapping is checked against its seed and saved binding; the complete upstream snapshot is not reread to reconstruct every original selected observation.

**Supported interpretation:** finite samples and split sensitivity contribute to fragility in the saved simulations; real split sensitivity and persistently wrong preferences are both observed. Lower residual dependence can favor the benchmark-wrong direction. Neither a large margin, a stable sign nor a nonrejected independence test guarantees correct identification.

**Unresolved:** which real cases violate additive-noise assumptions, whether confounding/selection/cluster dependence is decisive, which reference labels are imperfect, and whether the fixed regression/bandwidth settings contribute. Tied values and sample-size associations do not establish these causes.

## 9. Recommended next work

1. Keep this audit separate from Vaishak's LLM cue experiment. The LLM study tests downstream propagation; this audit characterizes upstream fragility.
2. If more ANM work is justified, freeze a known-truth synthetic factorial experiment separating training size from evaluation size and additive noise from one specific violation at a time. Use multiple fresh dataset seeds, report all conditions, and retain a fixed baseline. This is proposed, not executed.
3. Obtain source-level metadata for the persistently wrong real cases before claiming a case-specific assumption violation. Existing source descriptions raise concerns but do not identify the decisive cause.
4. Do not tune thresholds, reverse arrows, select a favorable split, or exclude difficult pairs after seeing labels. A revised accuracy claim needs a new source-separated evaluation cohort.

## Theory and external context

ANM identification depends on additive-noise structure and additional conditions; a theorem is not a guarantee for a finite-sample fixed implementation. See [Peters et al. (2014)](https://jmlr.org/papers/v15/peters14a.html). The broader CauseEffectPairs study reports useful ANM performance with other evaluation details, so this audit does not refute ANM as a whole: [Mooij et al. (2016)](https://jmlr.org/papers/v17/14-518.html). Neither publication validates our particular 38 outputs.

Generated from metrics.json; see the shared experiment guide for reproduction. No significance, causal root-cause or improvement claim is made.
