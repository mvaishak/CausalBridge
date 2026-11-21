# ANM component mechanism study

**Controlled synthetic pilot. These results do not identify the cause of errors on real pairs.**

Phase: full. 24 base datasets, 192 paired factorial cells; 0 execution failures. Changing train size preserves evaluation rows; changing evaluation size preserves training rows. Noise regimes share exogenous draws. Results below retain all scheduled worlds.

| Regime | Train | Eval | C | W | A | F | Learned forward rejected | Oracle forward rejected | Median mean-function error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| independent_additive | 64 | 64 | 21 | 1 | 2 | 0 | 1/24 | 0/24 | 0.01873 |
| independent_additive | 64 | 256 | 23 | 0 | 1 | 0 | 9/24 | 1/24 | 0.01863 |
| independent_additive | 256 | 64 | 22 | 0 | 2 | 0 | 1/24 | 0/24 | 0.00688 |
| independent_additive | 256 | 256 | 24 | 0 | 0 | 0 | 6/24 | 1/24 | 0.00661 |
| heteroscedastic | 64 | 64 | 6 | 17 | 1 | 0 | 20/24 | 20/24 | 0.02103 |
| heteroscedastic | 64 | 256 | 1 | 23 | 0 | 0 | 24/24 | 24/24 | 0.01766 |
| heteroscedastic | 256 | 64 | 7 | 13 | 4 | 0 | 19/24 | 20/24 | 0.00658 |
| heteroscedastic | 256 | 256 | 2 | 17 | 5 | 0 | 24/24 | 24/24 | 0.00664 |

## Oracle-assisted diagnostic (not a deployable method)

Only the known true-direction regression is replaced. The reverse model stays learned.

| Regime | Train | Eval | Oracle-assisted C | W | A |
|---|---:|---:|---:|---:|---:|
| independent_additive | 64 | 64 | 24 | 0 | 0 |
| independent_additive | 64 | 256 | 24 | 0 | 0 |
| independent_additive | 256 | 64 | 23 | 0 | 1 |
| independent_additive | 256 | 256 | 24 | 0 | 0 |
| heteroscedastic | 64 | 64 | 7 | 15 | 2 |
| heteroscedastic | 64 | 256 | 1 | 20 | 3 |
| heteroscedastic | 256 | 64 | 7 | 15 | 2 |
| heteroscedastic | 256 | 256 | 2 | 16 | 6 |

## Mechanism families

| Family | Regime | Train | Eval | N | C | W | A | F |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| scaled_cubic | independent_additive | 64 | 64 | 12 | 11 | 0 | 1 | 0 |
| scaled_cubic | independent_additive | 64 | 256 | 12 | 11 | 0 | 1 | 0 |
| scaled_cubic | independent_additive | 256 | 64 | 12 | 10 | 0 | 2 | 0 |
| scaled_cubic | independent_additive | 256 | 256 | 12 | 12 | 0 | 0 | 0 |
| scaled_cubic | heteroscedastic | 64 | 64 | 12 | 1 | 11 | 0 | 0 |
| scaled_cubic | heteroscedastic | 64 | 256 | 12 | 0 | 12 | 0 | 0 |
| scaled_cubic | heteroscedastic | 256 | 64 | 12 | 2 | 8 | 2 | 0 |
| scaled_cubic | heteroscedastic | 256 | 256 | 12 | 0 | 10 | 2 | 0 |
| sine | independent_additive | 64 | 64 | 12 | 10 | 1 | 1 | 0 |
| sine | independent_additive | 64 | 256 | 12 | 12 | 0 | 0 | 0 |
| sine | independent_additive | 256 | 64 | 12 | 12 | 0 | 0 | 0 |
| sine | independent_additive | 256 | 256 | 12 | 12 | 0 | 0 | 0 |
| sine | heteroscedastic | 64 | 64 | 12 | 5 | 6 | 1 | 0 |
| sine | heteroscedastic | 64 | 256 | 12 | 1 | 11 | 0 | 0 |
| sine | heteroscedastic | 256 | 64 | 12 | 5 | 5 | 2 | 0 |
| sine | heteroscedastic | 256 | 256 | 12 | 2 | 7 | 3 | 0 |

## Matched effects

Right minus left yield. Intervals resample whole base datasets within each of the two fixed mechanism families, preserving paired conditions. They are exploratory, unadjusted for multiple comparisons and do not represent uncertainty over new families.
- n_train 64 → 256; regime=independent_additive, train=None, eval=64: wrong yield -4.2% [-12.5%, +0.0%]; correct yield +4.2%.
- n_train 64 → 256; regime=independent_additive, train=None, eval=256: wrong yield +0.0% [+0.0%, +0.0%]; correct yield +4.2%.
- n_eval 64 → 256; regime=independent_additive, train=64, eval=None: wrong yield -4.2% [-12.5%, +0.0%]; correct yield +8.3%.
- n_eval 64 → 256; regime=independent_additive, train=256, eval=None: wrong yield +0.0% [+0.0%, +0.0%]; correct yield +8.3%.
- n_train 64 → 256; regime=heteroscedastic, train=None, eval=64: wrong yield -16.7% [-37.5%, +0.0%]; correct yield +4.2%.
- n_train 64 → 256; regime=heteroscedastic, train=None, eval=256: wrong yield -25.0% [-41.7%, -8.3%]; correct yield +4.2%.
- n_eval 64 → 256; regime=heteroscedastic, train=64, eval=None: wrong yield +25.0% [+8.3%, +41.7%]; correct yield -20.8%.
- n_eval 64 → 256; regime=heteroscedastic, train=256, eval=None: wrong yield +16.7% [+0.0%, +37.5%]; correct yield -20.8%.
- regime independent_additive → heteroscedastic; regime=None, train=64, eval=64: wrong yield +66.7% [+50.0%, +83.3%]; correct yield -62.5%.
- regime independent_additive → heteroscedastic; regime=None, train=64, eval=256: wrong yield +95.8% [+87.5%, +100.0%]; correct yield -91.7%.
- regime independent_additive → heteroscedastic; regime=None, train=256, eval=64: wrong yield +54.2% [+33.3%, +75.0%]; correct yield -62.5%.
- regime independent_additive → heteroscedastic; regime=None, train=256, eval=256: wrong yield +70.8% [+54.2%, +87.5%]; correct yield -91.7%.

## Interpretation boundaries

- Mean-function error is in original effect units, comparing learned predictions with the known conditional mean. Its change isolates prediction approximation here; it is not a causal-direction metric.
- Oracle-forward residuals remove mean-regression approximation. Their dependence test can still reject under finite-sample randomness in the additive condition; nonrejection does not prove independence. Heteroscedasticity violates forward independent additive noise by construction, even when a finite test does not detect it.
- Oracle-assisted directions replace only the true-direction score with an oracle score. They use privileged generating-function knowledge and are not a deployable method, upper bound, new benchmark or proposed production replacement.
- Dependence tests use 99 residual permutations, a plus-one p-value, alpha .05 and a frozen 1e-12 numerical tie tolerance. They diagnose dependence, not causal truth. No threshold, kernel, model or sample exclusion was chosen from these outcomes.
- This study uses two fixed functions, one noise amplitude and one heteroscedastic strength. It tests one assumption violation, not confounding, temporal dependence, all ANM mechanisms, or the specific soil/engine datasets.
- Inspect failures and family-level outcomes before interpreting aggregate rates. A zero-error cell or interval is not proof of general reliability.
