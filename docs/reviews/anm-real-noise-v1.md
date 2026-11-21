# Real ANM pairs: residual-spread follow-up

## Verdict

**There is evidence compatible with changing residual spread in a subset of the
wrong pilot cases, but no demonstrated universal explanation for the real errors.**
The strongest pilot candidates are benchmark pairs 56 and 88. Their patterns persist
after a simple residual-mean correction and a saved-order block sensitivity check.
These are not proof of changing structural noise, valid causal directions, or the
cause of the ANM errors. The 38-pair panel gives a less specific pattern, including
flags in correct and abstaining cases. The three persistently wrong cases do not
have a robust primary-split flag under every diagnostic.

No original ANM prediction, setting, input, reference label or exclusion changed.
We reconstructed 131 frozen fits in both directions (262 directional reconstructions),
requiring their HSIC scores to match preserved results, and applied new diagnostics
separately. The original 17-pair and later 38-pair panels are never pooled.

## Why a residual-spread flag needs a mean-error control

A residual is the measured effect minus a fitted prediction. If the fitted mean is
wrong, its residuals can vary across cause values even when true noise variance is
constant. A scatterplot or a test of squared residuals alone would not separate
those explanations.

We therefore used training-quantile bins, within-bin median-centered absolute
residual deviations, and a second analysis after five-fold cross-fitted quadratic
residual-mean correction. Settings and all input vectors were frozen before the
new diagnostics. The correction is a sensitivity analysis, not an oracle. Complex
mean misspecification may remain, and the correction can introduce estimation error.

The fixed diagnostic was checked on paired residual controls from 24 base worlds:

| Known control | Nominal IID flags before mean correction | After mean correction |
|---|---:|---:|
| Independent additive oracle noise | 0/24 | 0/24 |
| Constant noise plus quadratic mean error | 22/24 | 0/24 |
| Heteroscedastic oracle noise | 24/24 | 24/24 |

The block sensitivity produced the same control counts. These are reused synthetic
calibration examples, not fresh validation or a guarantee of zero false-positive
rate. The quadratic control matches the correction's model class and does not test
all possible mean errors. The 22/24 result demonstrates why naive residual-spread
flags can be wrongly attributed to structural noise.

## Real primary results

We report the direction indicated by the benchmark reference, whether or not ANM
selected it. Both directions were tested; all opposite-direction results are saved.
Each nominal p-value uses 1,999 randomizations and the plus-one rule. Holm adjustment
uses all 34 pilot or 76 later-panel directional slots separately within each form
and randomization scheme. Invalid/unavailable diagnostics retain their slot.

These are **Holm-adjusted nominal spread flags**, not confirmed heteroscedasticity.
Within-observation exchangeability, estimated median centering and finite bins are
not established for the real data. Multiple-test adjustment does not fix those
assumptions. Block permutation is a heuristic, not a validated dependence correction.

| Panel | Original ANM outcome | Scheduled reference directions | Available | Raw IID flags | Mean-corrected IID flags | Mean-corrected block flags |
|---|---|---:|---:|---:|---:|---:|
| Pilot 17 | Correct | 6 | 6 | 0 | 0 | 0 |
| Pilot 17 | Wrong | 8 | 8 | 2 | 4 | 2 |
| Pilot 17 | Abstain | 3 | 3 | 0 | 0 | 0 |
| Later 38 | Correct | 13 | 11 | 2 | 2 | 2 |
| Later 38 | Wrong | 13 | 10 | 2 | 2 | 1 |
| Later 38 | Abstain | 12 | 9 | 2 | 2 | 2 |

An unavailable diagnostic is not a negative test, an ANM abstention or an execution
failure. The unavailability here comes from insufficient/empty cause bins under
the fixed rule, often involving tied measurements. No cases were removed from the
original ANM totals: 6C/8W/3A and 13C/13W/12A. The two sensitivity splits repeat the
same later cases; they do not add independent pairs.

The pilot contrast is descriptive and potentially interesting. It is not a formal
test that spread flags predict incorrect directions: source families differ,
references are opened and imperfect, and only six correct controls are present.
The later panel does not show a specific separation of wrong from correct cases.

## Strongest pilot candidates

The spread ratio below is the largest divided by smallest *mean absolute deviation
from a bin median*, after mean correction. It is not a structural noise variance ratio.

| Pair | Source context | Available test observations | Spread ratio | Adjusted nominal IID p | Adjusted nominal block p |
|---|---|---:|---:|---:|---:|
| 56 | Female life expectancy and capital latitude | 64 | 4.67 | 0.017 | 0.017 |
| 88 | Age and relative change in spinal bone mineral density | 64 | 3.03 | 0.032 | 0.017 |

Both were wrong ANM cases in the original pilot. Raw and mean-corrected patterns
survived adjustment in both randomization schemes. The cause bins had counts
11/29/24 for pair 56 and 25/23/16 for pair 88. Pilot pairs 4 and 18 additionally
flagged after mean correction under nominal IID randomization, but not after the
block sensitivity, so they are weaker candidates.

A post-outcome source-description review, checked against the repository's pinned
file hashes, supplies context. Pair 56 is country-level observational data, so
omitted determinants and heterogeneous populations remain plausible alternatives.
Pair 88's source selected the first measurement per child; we must not invent a
repeated-measurement explanation for those processed rows. Age-dependent spread is
compatible with the diagnostic, but neither these metadata nor the test identifies
why the ANM direction was wrong.

The checks do not manipulate the real noise process. A candidate association can
coexist with regression bias, selection, measurement effects, dependence, reference
error or another ANM mismatch. The controlled synthetic result demonstrates that
one such mismatch *can* break the diagnostic; it does not attribute the real error.

## What happened to the three persistently wrong cases?

Primary split 261:

| Pair | Mean-corrected spread ratio | Raw IID adjusted nominal p | Mean-corrected IID adjusted nominal p | Mean-corrected block adjusted nominal p |
|---|---:|---:|---:|---:|
| 91 | 2.19 | 0.062 | 0.118 | 1.0 |
| 92 | 1.66 | 1.0 | 1.0 | 1.0 |
| 108 | 7.19 | 0.165 | 0.062 | 1.0 |

Pair 91 has a suggestive unadjusted pattern but not a primary adjusted flag. Pair
108 has a large spread ratio whose nominal evidence is sensitive to adjustment and
row-order blocks. Secondary splits sometimes flag pairs 91/108 under IID analysis,
but do not establish a robust block result. Pair 92 has no compelling pattern under
these fixed diagnostics. We do not replace the primary split with a favorable one.
Nonflagging does not prove constant noise variance, especially with small samples.

## What we learned and the appropriate next decision

1. There are two concrete pilot cases worth a deeper source-level noise/model review.
   This is more specific than merely knowing that ANM can fail on heteroscedastic
   synthetic data, but remains an exploratory candidate explanation.
2. Mean-function error is a real alternative explanation for spread diagnostics;
   our controls expose it directly. A generic residual-variance test would overclaim.
3. Changing residual spread is not a complete or sufficient explanation of the real
   errors: correct/abstaining cases can flag, and persistently wrong cases may not.
4. Retain the project conclusion about upstream fragility and downstream propagation.
   Do not relabel references, change exclusions, reverse arrows, retune ANM, or claim
   improved causal accuracy from these observations.
5. If further work is justified, examine original units/population structure and
   repeated measurements for the candidate datasets, or obtain independent data
   with a richer mean/noise model frozen beforehand. That would test a narrowed
   hypothesis; these opened pairs cannot provide independent confirmation of a fix.

## Reproduction and methodological limits

The [protocol](../experiments/anm-real-noise-v1.md) and
[raw bundle and tables](../../artifacts/anm-real-noise-20261121/README.md) preserve all
originals, residual vectors, diagnostics, flags, source hashes and unavailable cases.
A replay recomputes diagnostics from vectors without fitting ANM again. Full study
source is archived so later branch changes need not prevent exact reproduction.

The median-centered contrast is inspired by
[Brown and Forsythe (1974)](https://doi.org/10.1080/01621459.1974.10482955), but our
randomization is an explicitly documented adaptation. Nominal exchangeability of
transformed deviations is not guaranteed after estimated centering or under
within-dataset dependence. Saved-order blocks are not verified time/spatial blocks.
Coarse bins, finite samples, conditional distribution shape and unresolved mean
errors prevent a causal noise-variance conclusion. No test in this report proves
a real structural assumption or a case-specific root cause.
