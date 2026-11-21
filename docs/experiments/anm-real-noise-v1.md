# Real-pair residual-spread investigation v1

This is the next exploratory step on `codex/anm-failure-diagnosis-20261121`.
The synthetic component study established a failure mechanism under one deliberately
violated assumption. This study asks whether residual patterns on the real pairs
are **compatible** with changing noise spread. It cannot prove that a structural
noise process is heteroscedastic or that it caused an incorrect direction.

## Frozen inputs and design

The JSON config, source hashes, original requests/results, all case IDs, source
families and synthetic-control vectors are saved before new residual diagnostics.
This is an internal freeze, not external preregistration. All references are already
opened; no accuracy-improvement or independent-validation claim is made.

- Original 17-pair pilot, split 261: 6 correct, 8 wrong, 3 abstentions.
- Later 38-pair panel, split 261: 13 correct, 13 wrong, 12 abstentions.
- Its saved splits 1261/2261 are sensitivity checks, not extra independent datasets.
- All pairs, including correct and abstaining controls, are retained. Panels are
  never pooled, since sample sizes and source families differ.
- 131 saved attempts (17 + 38×3), both directions: **262 frozen fit reconstructions**.
  Recomputed HSIC must match the saved production score. No ANM parameter, threshold,
  sample, mapping, original prediction, reference label or result is changed.
- Numerical diagnostics do not use correctness labels. References/grouping are
  used only for analysis after both directions have been processed.

## What is measured

Cause bins use the training cause's 1/3 and 2/3 quantiles. Equal cause values are
not split across bins. A bin with fewer than eight held-out observations makes
that diagnostic unavailable, not negative, and does not remove the pair from ANM
counts. No bins are merged after seeing outcomes.

Within each bin, subtract the residual median and calculate absolute deviations.
Measure how much of their variation is between cause bins (eta-squared). Also
report empirical within-bin variance, robust spread ratio, and residual mean/median
patterns. Changing residual spread can reflect changing variance, distribution
shape, unresolved mean error, outliers or sampling—not necessarily structural noise.

The median-centering idea follows [Brown and Forsythe (1974)](https://doi.org/10.1080/01621459.1974.10482955).
Our statistic and randomization are an explicitly documented adaptation, not a
claim that we ran the classical parametric Brown–Forsythe F test. Permuting the
median-centered deviations gives **nominal, approximate** p-values under an
exchangeability assumption; estimated centering and unequal bin sizes complicate
that assumption. It is not an exact distribution-free noise-variance test.

### Residual-mean sensitivity

Repeat after subtracting a cross-fitted quadratic prediction of the residual mean:
five fixed folds, degree two, least squares, no tuning or reference labels. Original
ANM preprocessing remains unchanged. This can remove simple mean misspecification,
but can leave more complex errors or introduce estimation error. Persistence of a
spread flag is corroboration, not proof; disappearance is sensitivity, not proof of
an alternative cause. Rank-deficient fits are unavailable rather than fabricated.

### Observation-dependence sensitivity

Each form has two fixed randomization schemes, with 1,999 draws and a plus-one
p-value:

1. Shuffle individual absolute deviations (nominal IID assumption).
2. Shuffle contiguous blocks of eight in saved sample-row order, after restoring
   evaluation rows to that order.

The block scheme is a **heuristic sensitivity**, not an established correction for
serial/spatial dependence. We do not have observation-time or spatial-unit IDs;
saved row order may reflect sorting and has unequal source spacing. Blocks preserve
some local order, but stationarity, suitable block length and exchangeability of
blocks are not established. Do not call a block result a valid dependence-adjusted
causal test.

## Multiplicity, denominators and calibration

Holm-adjust nominal p-values over every planned directional test within each
panel/split/diagnostic form/randomization scheme (34 or 76 tests). Unavailable
entries retain a slot but are not flagged. Families are reported separately; no
joint error guarantee across all sensitivity analyses is claimed. Holm cannot
repair invalid within-dataset exchangeability assumptions.

For reference directions, report flags among the original correct/wrong/abstaining
pairs with both all-scheduled and available-diagnostic denominators. Report the
opposite directions and all case-level values too. Counts are descriptive; source
families and repeated splits do not support an independent-pairs prevalence test.

Before interpreting real flags, assess fixed diagnostics on 24 reused base worlds
from the frozen synthetic study:

- Known independent-additive oracle residuals (constant structural variance).
- Known heteroscedastic oracle residuals.
- Constant noise plus a deliberately unremoved quadratic mean error (.5 times
  `X²−4/3`), to expose false attribution of regression bias to variance.

These are 72 **paired calibration vectors**, not 72 independent worlds and not a
fresh accuracy validation. Controls are processed with the same bins, detrending
and randomization. Their flags are reported at nominal .05 to describe sensitivity
and false flags, without selecting a new cutoff or hiding unfavorable controls.

## Execution and replay

Python 3.12, uv and the existing NumPy extra are sufficient. No full upstream data
snapshot, GPU, LLM, new real-data selection or alternative ANM fit is needed.
All input archives are already in the branch. Use new paths.

```sh
uv sync --frozen --dev --extra anm
uv run --extra anm python -m pytest tests/test_anm_real_noise.py -q
uv run --extra anm python scripts/anm_real_noise.py prepare --output runs/anm-real-noise-01
uv run --extra anm python scripts/anm_real_noise.py run --plan runs/anm-real-noise-01
uv run --extra anm python scripts/anm_real_noise.py analyze --plan runs/anm-real-noise-01 --output runs/anm-real-noise-analysis-01 --replay
```

Execution writes diagnostics separately from read-only copied originals. A started
run is not overwritten. Analysis with `--replay` recalculates spread checks and
cross-fitted residual corrections from saved vectors, without reconstructing ANM
fits. Raw inputs, vectors, source freeze and completion digests must remain together.
Unavailability is recorded separately from ANM failures or abstentions.

## Execution and findings

The frozen protocol was run on all original inputs without selecting parameters
from its outcomes. Original scores matched in all 262 reconstructions. All 334
real/control vector records were preserved, including unavailable spread checks.
There are 1,264 available form/scheme tests and 72 unavailable tests; availability
is separate from ANM execution or abstention. The
[interpretation](../reviews/anm-real-noise-v1.md) and
[raw bundle](../../artifacts/anm-real-noise-20261121/README.md) retain every case and
explicitly distinguish suggestive candidates from a demonstrated causal explanation.
