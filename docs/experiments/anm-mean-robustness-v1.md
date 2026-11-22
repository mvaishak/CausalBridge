# Fixed mean-estimator robustness check

This exploratory follow-up tests whether the residual-spread patterns in pilot pairs 56 and 88 depend on the original mean estimator. It does not tune production ANM or generate new causal predictions. Both targets were selected after earlier outcomes were seen. All six originally correct pilot pairs (2, 3, 13, 16, 23, 86) are comparison cases; they are not source-matched controls. The other nine pilot cases are outside this focused experiment.

The protocol is `configs/anm-mean-robustness-v1.json`. It was frozen with complete original request/sample/configuration/result files and source hashes before execution. The original training/evaluation split, A/B mapping, training-only standardization, and benchmark-reference direction are retained. Each case has 64 training and 64 evaluation observations. Only the reference direction is studied: this is not an ANM accuracy evaluation.

## Fixed estimators and diagnostics

Every case receives four fits. All use the same training observations; evaluation responses are never used in these primary fits or hyperparameter selection.

- Original RBF kernel ridge: gamma 1, ridge 0.1.
- Smoother kernel ridge: gamma 0.25, ridge 0.1.
- More local kernel ridge: gamma 4, ridge 0.1.
- Gaussian-weighted local linear regression: bandwidth 0.5 in training-standardized cause units, without a ridge penalty. Rank deficiency is an explicit execution failure.

These are fixed sensitivity choices, not a search or proof that a more accurate mean function has been learned. No estimator is selected for deployment. Held-out MSE includes irreducible noise; lower real-data MSE does not establish smaller true mean-function error.

Reuse the earlier study's training-quantile bins, median-centered absolute residual spread, eta-squared contrast, 1,999 permutations, minimum eight evaluation observations per bin, IID permutation, and saved-order block-length-eight heuristic. Report raw residuals and five-fold cross-fitted quadratic residual-mean correction. Correction uses evaluation observations from other folds, so it is an auxiliary diagnostic, not a new independent evaluation set. Identical fold/permutation keys are used across estimators within a case. Keys differ from the prior study; do not treat small cross-study differences as estimator effects.

Holm adjustment covers all eight real cases separately for each estimator × residual form × permutation scheme (16 families). It does not jointly adjust across all families or historical exploratory investigations. P-values are nominal approximations: exchangeability, estimated medians, and saved-row dependence remain limitations. Block permutation is not a validated temporal/spatial correction. A descriptive robust candidate must retain nominal adjusted p≤0.05 in all four form/scheme combinations for every estimator. This is not a test proving structural noise or an error classifier.

## Synthetic checks

Use two fixed mean functions, 0.25 X³ and sin(2X), with 128 training and 128 evaluation observations, X uniform on [-2,2], and noise SD 0.5. Four seeds generate random draws reused across both functions and both regimes. Independent additive noise is contrasted with noise multiplied by `(1+0.375X)/sqrt(1+0.375²*4/3)`. All four estimators are evaluated, giving 64 configurations. True mean-function MSE can be calculated here. Controls are small, paired, and exploratory; they do not calibrate a population false-positive rate.

## Execute and replay

From the repository with the existing saved-data study extracted:

```sh
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_mean_robustness.py prepare --plan runs/mean-robustness-new --originals runs/anm-real-noise-20261121
uv run python scripts/anm_mean_robustness.py run --plan runs/mean-robustness-new
uv run python scripts/anm_mean_robustness.py report --plan runs/mean-robustness-new --output runs/mean-robustness-new/tables.md
```

If the earlier run directory is absent, restore its archived `plan/` using `verified_archive` and `materialize` from `anm_failure_audit`, with `artifacts/anm-real-noise-20261121/run-records.tar.gz` and its manifest. Pass the restored `plan` as `--originals`. Preparation also reads the committed earlier `real-records.json` to select cases and original mappings.

Reproduce the new saved table without any fitting or LLM calls:

```sh
uv run python scripts/anm_mean_robustness.py report --plan artifacts/anm-mean-robustness-20261121 --output /tmp/mean-robustness-tables.md
```

The new artifact README explains self-contained frozen-source reruns. Never remove execution markers from an original run. New full reruns must use a separate restored copy. Current production source hashes may diverge after future development; the archived frozen source supplies the exact executed implementation. No live model, GPU, or new external data is required.
