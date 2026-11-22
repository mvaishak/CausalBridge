# ANM numerical correctness and decision-rule audit

## Executive finding

We have evidence of a **decision-rule limitation**, not an established coding error that explains the benchmark's wrong directions. The method ranks two residual-dependence scores and releases a direction when their difference exceeds a threshold. It does not require either fitted direction to pass an independence check. Consequently it can select a direction even when both fits show evidence against the additive-independent-noise model. This is consistent with its documented bounded diagnostic role; it is not a violation of its current implementation contract.

This audit covers every original pilot pair (17) and every primary later-panel pair (38), at the original saved splits and settings. All 55 historical decisions were preserved. We made no production changes, threshold selections, new LLM calls, or accuracy-improvement claims.

## Independent mathematical check

We reconstructed both regressions using symmetric eigendecomposition rather than the producer's direct linear-system solve. We separately constructed median-positive-distance bandwidths and explicit H K H centering, scoring by trace(Kc Lc)/n². On the saved original residuals, all 110 directional HSIC calculations reproduced the saved producer scores within relative tolerance 1e-9 and absolute tolerance 1e-12. This checks the HSIC formula independently; the original saved vectors were reconstructed by the previous phase and are not an independent source of truth.

The independent regression solution's maximum relative normal-equation error was 5.18e-13. Sixteen of 110 end-to-end scores differed beyond the stricter eigensolver comparison tolerance (relative 1e-8 / absolute 1e-11); the maximum absolute difference was 2.12e-6. **Zero of 55 decisions changed.** Thus these small discrepancies do not explain the original categorical errors in this panel.

A preliminary run reordered evaluation rows before prediction and stopped at a score mismatch on pair 5. Follow-up inspection showed that near-tied residual values can acquire slightly different rounding under otherwise equivalent numerical execution. The positive-distance-only bandwidth rule is sensitive to whether these tiny distances are exactly zero. For that real case, the original score was 0.0040039370737874405 and recomputing predictions after row reordering gave 0.00400246895712543. This is a numerical robustness concern, not proof that all eigensolver discrepancies have this cause or that this caused a wrong direction. The amended complete audit retains discrepancies instead of suppressing them, preserves original residuals for adequacy tests, and keeps evaluation order unchanged during the reference fits. The preliminary failure and frozen source are archived.

We did not certify all possible inputs, verify the data-generating process, or independently reproduce a separate third-party ANM package. These checks strongly constrain arithmetic explanations for the observed decisions, but are not a universal proof of software correctness.

## Real-data adequacy findings

For each direction we performed 1,999 plus-one Monte Carlo HSIC permutations, with a fixed seed. The primary descriptive comparison uses nominal p≤0.025 per direction (Bonferroni for the two directional tests within a pair). We also report p≤0.05 and a block-length-eight saved-row-order heuristic. No cross-pair or across-analysis-family confirmatory guarantee is claimed. Sampling dependence, source grouping, finite power, and already-opened data constrain interpretation.

| Panel / historical outcome | Cases | Both directions rejected, IID p≤0.025 each | Both rejected, blocks p≤0.025 each |
|---|---:|---:|---:|
| Pilot correct | 6 | 0 | 1 |
| Pilot wrong | 8 | 2 | 1 |
| Pilot abstained | 3 | 0 | 0 |
| Later-panel correct | 13 | 7 | 3 |
| Later-panel wrong | 13 | 5 | 4 |
| Later-panel abstained | 12 | 7 | 6 |

Both-direction rejection is not restricted to wrong answers. A new rejection rule would remove correct answers too. These are **diagnostic counts, not validation of an improved gate or an estimate of future accuracy**. Statistical rejection can also reflect regression misspecification or dependence; lack of rejection does not establish independence.

### Two distinct candidate cases

**Pair 88:** both directions reject under IID (A→B p=0.0065, B→A p=0.0015) and heuristic blocks (0.016, 0.001), including the within-pair 0.025 threshold. The original method nevertheless released a benchmark-wrong direction. Together with the earlier estimator-robust spread pattern, this supports a case-specific concern that relative ranking is operating where neither fitted additive-noise model is supported by these diagnostics. It does not identify structural noise as the root cause.

**Pair 56:** the benchmark reference B→A rejects (p=0.0005 under both schemes), but the chosen wrong A→B does not (IID p=0.4305; blocks p=0.4145). The earlier spread pattern remains consistent with an unsuitable forward independent-noise assumption. Merely checking whether the selected direction fails an independence test would not identify this error. Nonrejection of the wrong direction can reflect limited power, an alternative compatible representation, dependence, model error, or other structure; this audit does not discriminate among them.

The persistent wrong pairs 91, 92, and 108 do not have both directions rejected under the primary within-pair criterion. This limitation is therefore not a complete explanation of the real benchmark errors.

## Connection to synthetic performance

We re-tabulated existing saved component-study results, without new synthetic fits. At training/evaluation sizes 256/256:

- Independent additive noise: 24 correct, zero wrong, zero abstentions. Both learned directions rejected in 6/24 cases under that study's 99-permutation nominal 0.05 checks.
- Cause-dependent noise spread: 2 correct, 17 wrong, 5 abstentions. Both learned directions rejected in all 24 cases, including all 19 directional releases.

This reconciles good performance under the tested independent-additive controls with poor performance under one explicit mismatch. It also shows why converting adequacy tests directly into a production gate is not a free fix: finite-sample regression residuals can reject even in a correctly generated additive-noise control. Different permutation counts and significance rules mean the synthetic counts must not be compared as if identical to the new real-data tests.

## Four development pairs

The four development pairs do not train one common regression model deployed on the other pairs. Each pair supplies its own training and held-out observations. The development roster supplies limited evidence for choosing shared hyperparameters and thresholds. Four heterogeneous datasets are insufficient to establish broad calibration reliability, but their count alone does not explain the observed failures. Calibration quality, regression fit within each pair, assumption suitability, and decision policy are separate questions.

Do not silently turn inspected validation pairs into fresh development evidence. A new calibration study needs frozen candidate methods and objectives, source-aware splitting, and genuinely unexamined assessment cases. If only opened cases are available, label the study exploratory and obtain a new held-out assessment set before claiming improvement.

## What is established, and what would settle the next questions?

**Established for these artifacts:** original decisions follow the implemented score-ranking logic; independent numerical execution does not change any of the 55 decisions; the rule can release a direction when both residual-independence tests reject; real pairs 56 and 88 demonstrate different diagnostic failure patterns; adequacy rejection is not a reliable correctness label.

**Not established:** a universal root cause of real errors, that one ANM assumption is uniquely responsible, a successful repair, or that four development pairs caused the poor benchmark performance.

Priority next steps, if extending beyond this diagnosis:

1. **Method/decision validation:** freeze a revision that clearly separates directional preference, adequacy warnings, abstention and execution failure. Evaluate accuracy, correct/wrong yield and coverage on new cases; predefine acceptable coverage loss. Do not claim improved performance from the opened cases above.
2. **Calibration adequacy:** compare frozen configurations using a larger development collection separated by source family, then evaluate once on a new held-out panel. More rows within one pair are not substitutes for more independent dataset families.
3. **Real root-cause attribution:** obtain original sampling units, order, preprocessing and source-domain information for pairs 56/88; test targeted competing explanations. Definitively separating confounding, changing structural noise, and functional misspecification usually requires stronger design information, intervention data or a known generating process, not repeated statistical tests on the same observational sample.

We should finalize the bounded findings above rather than continue until an error is forced to appear. Any additional numerical robustness repair must be independently tested and versioned; it should not be presented as the explanation of these categorical errors without evidence.

## Reproduction and files

- `configs/anm-decision-audit-v1.json`: protocol filename retained; internal version v2 documents the preliminary amendment before the complete run.
- `src/causalbridge/evaluation/anm_decision_audit.py`: independent reference calculation, frozen input verification, nominal adequacy checks, and deterministic tables.
- `scripts/anm_decision_audit.py`: prepare/run/report interface.
- `tests/test_anm_decision_audit.py`: independent numerical references, invariance, permutation arithmetic, no-fit replay and preserved real-case evidence.
- `artifacts/anm-decision-audit-20261121/`: all case-level checks, complete raw/source archive, preliminary failure, integrity manifest and validation records. Its README provides execution commands.

Original frozen results, production ANM, report and slides are unchanged. See `anm-diagnosis-summary.md` for the consolidated interpretation. The user authorized committing this audit and consolidation; publication remains separate.
