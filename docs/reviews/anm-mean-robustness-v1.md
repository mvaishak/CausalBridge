# Mean-estimator robustness: findings and limits

## Result

The changing residual spread in pilot pairs 56 and 88 survived all four fixed mean estimators. It also survived cross-fitted quadratic residual-mean correction, IID permutation, and the heuristic saved-order block check. The strongest defensible finding is **robustness to these particular mean-estimator choices**, not proof of structural heteroscedasticity or the root cause of the original wrong causal answers.

All 32 real-data configurations and 64 synthetic configurations completed. Original ANM outputs remain unchanged. Original forward residuals were reproduced to relative tolerance 1e-9 and absolute tolerance 1e-12, and both original directional HSIC scores were checked for each of the eight cases.

| Target | Original held-out MSE | Range over all four estimators | Raw spread ratio range | Mean-corrected spread ratio range |
|---|---:|---:|---:|---:|
| 56 | 0.625278 | 0.583568–0.632764 | 3.63–4.60 | 3.45–4.37 |
| 88 | 0.754295 | 0.737225–0.754295 | 3.24–3.58 | 2.78–3.23 |

MSE units are squared original-ANM training-standardized effect units. Spread ratios compare largest to smallest bin mean absolute deviation from the bin median; they are not structural noise variance ratios. The largest observed MSE reductions relative to the original estimator were about 6.7% and 2.3%. These are descriptive held-out outcomes, not selected model improvements or independent estimates of mean-function error.

Both targets retained all nominal Holm-adjusted checks at p≤0.05 under every estimator. Pair 88 was close to the cutoff under the flexible kernel after correction (IID 0.0385; heuristic blocks 0.0455), so this binary criterion should not conceal sensitivity in signal strength. All six originally correct pilot comparisons failed to meet this all-configuration criterion; none had a nominal adjusted flag after residual-mean correction. Some correct cases did have raw, estimator-specific flags (pair 2 under the flexible kernel/block check; pair 16 under smoother kernel or local linear/IID checks). Report these rather than implying perfect specificity.

**The current Holm family has eight cases, whereas the previous pilot study included 34 directions. Smaller adjusted p-values do not establish stronger independent evidence.** Targets were chosen because of their prior spread signals. This is a sensitivity analysis on selected, already-opened observations, not a new confirmation cohort or a valid test of enrichment among wrong answers.

## Synthetic checks

Each estimator has eight function/seed configurations per noise regime, with four random draws reused across two functions. All configurations are saved; no estimator was chosen from the results.

- Independent additive noise: original, smoother, and flexible kernels gave 0/8 nominal IID flags both before and after correction. Local linear gave 0/8 raw and 1/8 corrected.
- Cause-dependent noise spread: all four estimators gave 8/8 nominal IID flags both before and after correction.
- Median true mean-function MSE for independent noise was 0.01824 original, 0.01230 smoother, 0.02358 flexible, and 0.05771 local linear. For cause-dependent spread it was 0.00947, 0.01086, 0.01127, and 0.05076, respectively.

More flexible settings did not uniformly improve the known mean fit. The controls support this implementation's ability to retain a strong spread signal under these specified simulations; their small paired design cannot establish broad sensitivity or specificity.

## Interpretation

Verified: the real spread patterns persist across a small fixed set of differently smoothed mean estimators, even where held-out prediction error falls. This makes dependence on one particular original kernel setting less plausible.

Reasonable interpretation: changing conditional variability remains a credible candidate explanation for why the independent-additive-noise assumptions may be unsuitable for these two pairs.

Unresolved: flexible mean estimators can all miss the same structure, finite samples can distort bin summaries, and dependence, outliers, mixtures, confounding, or transformations can also produce changing residual spread. Residual-mean correction handles only one limited mean-error class. We did not establish that noise spread caused the original directional mistakes; we did not rerun reverse-direction alternative estimators or measure an accuracy improvement. Lack of a flag in a comparison case does not establish additive-noise validity.

These findings strengthen a **case-specific diagnostic interpretation**. They neither explain all benchmark failures nor justify a claim that ANM generally cannot work on real data. Original report/slides and frozen accuracy results were not changed. A future confirmatory study would require frozen diagnostics and previously unexamined cases with stronger knowledge of sampling and the data-generating process.

## Files and verification

- `configs/anm-mean-robustness-v1.json`: fixed case selection, estimators, synthetic controls, and interpretation rule.
- `src/causalbridge/evaluation/anm_mean_robustness.py`: training-only fits; preservation checks; synthetic controls; saved residual diagnostics; replayable tables.
- `scripts/anm_mean_robustness.py`: prepare/run/report commands.
- `tests/test_anm_mean_robustness.py`: training-fit mathematics, local-linear degeneracy, protocol scope, replay without fitting, and saved configuration completeness.
- `docs/experiments/anm-mean-robustness-v1.md`: protocol, assumptions, and commands.
- `artifacts/anm-mean-robustness-20261121/`: complete original inputs, frozen protocol/source, predictions/residuals, all tables, logs, and integrity inventory. See its README and validation record for exact final checks.

Implemented on `codex/anm-failure-diagnosis-20261121`. No production method or submission accuracy result is changed.
