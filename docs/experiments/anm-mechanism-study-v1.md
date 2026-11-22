# ANM component mechanism study v1

This follows the saved-data audit on `codex/anm-failure-diagnosis-20261121`.
The question is whether regression approximation, evaluation-sample noise or a
specific additive-noise violation changes the behavior of the fixed ANM method.
This is a fresh, controlled synthetic pilot, not tuning on opened real pairs.

## Frozen design

`configs/anm-mechanism-study-v1.json` fixes all settings before execution. The
prepare command writes the ordered schedule, all dataset pools, original ANM
requests, configuration/source hashes and a UTC freeze record before any result.
This is an internal reproducibility freeze, not external preregistration.

- Mechanisms: `Y = .25 X^3 + noise` and `Y = sin(2X) + noise`; X is uniform on [-2,2].
- Noise amplitude .5; independent standard Gaussian exogenous draws.
- Two regimes: independent additive noise, or heteroscedastic noise obtained by
  multiplying the same epsilon by `(1 + .375 X)/sqrt(1 + .375^2 * 4/3)`.
  This keeps the *population expected noise variance* equal across regimes;
  finite-sample noise variances need not be identical. Conditional mean f(X) is
  unchanged. Heteroscedasticity violates forward independent additive noise by
  construction, even if a finite test does not detect it.
- 12 fresh seeds per family: **24 independent base worlds**, paired across noise
  regimes; **48 regime datasets**, each observed in four size conditions.
- Training size 64 versus 256; evaluation size 64 versus 256, varied separately.
  Independent train/evaluation pools; smaller samples are nested prefixes.
- Column orientation alternates before fitting. Numerical code receives only
  numeric rows and opaque request bindings; oracle/function metadata is used by
  the separate post-fit diagnostic, never by the production ANM calculation.
- Fixed historical gamma 1, ridge .1, threshold .001. No search or exclusions.
- **192 main cells**. **16 separate preflight cells**, using disjoint seeds.
  Preflight passes on successful execution and numerical agreement, not accuracy.
- Each cell executes the unchanged producer (two directional fits) and reconstructs
  those fits for component diagnostics (two more fits). Total planned directional
  fits: **832 including preflight**, not 832 independent datasets.
- Residual tests use 99 matching permutations for learned forward, learned reverse
  and oracle forward residuals, plus-one p-values, alpha .05, 1e-12 tie tolerance.
  Total planned permutation statistics: **61,776 including preflight**.
- No LLM calls, GPU or new real-data fits. Preserve the prior studies unchanged.

## What each control isolates

1. **Change training size, hold evaluation rows fixed:** measure conditional-mean
   estimation error against the known f(X), in original effect units. This avoids
   comparing errors under different training-based target scales.
2. **Change evaluation size, hold training rows fixed:** assess finite-evaluation
   sensitivity of HSIC scores, dependence detection and the frozen direction rule.
   More evaluation rows can change the raw-score scale as well as uncertainty;
   the fixed .001 threshold is not assumed calibrated across sample sizes.
3. **Replace learned true-direction regression with the known conditional mean:**
   oracle residuals remove mean-function approximation. Compare dependence before
   and after this replacement. No oracle reverse conditional mean is asserted.
4. **Change only noise regime with paired exogenous draws:** test one specific
   assumption mismatch. This is not a test of confounding or temporal dependence.

Oracle-assisted direction counts use privileged knowledge and are diagnostic only.
They are not a deployable method, upper bound or proposed production replacement.
P-values test residual dependence, not causal correctness. Nonrejection is not proof
of independence. In the independent-noise oracle condition, occasional rejection
can occur under a finite sample and Monte Carlo testing.

## Metrics and uncertainty

Every size/regime cell has 24 scheduled worlds. Report C/W/A/F, yields over all 24,
accuracy among directional answers only, mean-function error and dependence
rejections. Report family-level results to avoid hiding heterogeneity.

Primary contrasts are paired training-size and evaluation-size effects within a
noise regime, and paired regime effects at fixed train/evaluation sizes. Preserve
all failures. Resample complete base worlds within each of the two fixed families
(10,000 paired bootstrap draws, seed 261). These are exploratory intervals,
unadjusted for multiple comparisons, not uncertainty over new mechanism families.
Conditions within one base world are not independent observations.

No claim of explaining a particular real wrong pair follows. A positive synthetic
result likewise does not establish real-data accuracy improvement. If the tested
violation does not reduce direction accuracy, report that result rather than
increasing its strength until it does.

## Execute and reproduce

Use Python 3.12 and the pinned NumPy environment. All paths below must be new.

```sh
uv sync --frozen --dev --extra anm
uv run --extra anm python -m pytest tests/test_anm_mechanism_study.py -q
uv run --extra anm python scripts/anm_mechanism_study.py prepare --phase preflight --output runs/anm-mechanism-preflight-01
uv run --extra anm python scripts/anm_mechanism_study.py run --plan runs/anm-mechanism-preflight-01
uv run --extra anm python scripts/anm_mechanism_study.py prepare --phase full --output runs/anm-mechanism-full-01
uv run --extra anm python scripts/anm_mechanism_study.py run --plan runs/anm-mechanism-full-01 --preflight runs/anm-mechanism-preflight-01
uv run --extra anm python scripts/anm_mechanism_study.py analyze --plan runs/anm-mechanism-full-01 --output runs/anm-mechanism-analysis-01
```

Prepare writes requests before fitting. A source/protocol change invalidates the
freeze. A started study cannot be silently rerun or overwritten. Execution failures
remain records; a failed preflight blocks full execution. Do not adjust settings
based on observed accuracy and then reuse the same study label.

The analysis command reads saved production results and diagnostic vectors, checks
receipts and preprocessing, and replays all saved permutation calculations without
refitting. It generates case-level JSON, metrics and a bounded Markdown report.
Its replay repeats permutation arithmetic; it makes no new regression fits or LLM
calls. Raw data, requests, results, diagnostics, completions and freeze records must
be preserved together. Packaging source hashes is not authenticated preregistration.

## Execution and results

The frozen v1 protocol was executed without changing its settings after outcomes.
All 16 preflight and 192 main cells succeeded. The [interpretation report](../reviews/anm-mechanism-study-v1.md)
and [frozen bundle](../../artifacts/anm-mechanism-study-20261121/README.md) report
all conditions and limits. Source, raw requests/results and diagnostic vectors are
included so later code changes need not force a new numerical experiment.
