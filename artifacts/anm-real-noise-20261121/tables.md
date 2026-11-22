# Real-pair residual-spread tables

**Exploratory diagnostics. Flags are not proof of changing structural noise or causal failure.**

Both panels retain their original predictions. Unavailable diagnostics are not negative tests. Nominal randomization assumes exchangeability; saved-row-order blocks are a heuristic, not a validated dependence correction. Multiplicity correction does not fix invalid assumptions.

## Reference-direction primary outcomes

| Panel | Form | Scheme | Original outcome | Scheduled | Available | Nominal flags | Holm nominal flags |
|---|---|---|---|---:|---:|---:|---:|
| pilot17 | raw | iid | correct | 6 | 6 | 1 | 0 |
| pilot17 | raw | iid | wrong | 8 | 8 | 6 | 2 |
| pilot17 | raw | iid | abstention | 3 | 3 | 0 | 0 |
| pilot17 | raw | saved_order_blocks | correct | 6 | 6 | 1 | 0 |
| pilot17 | raw | saved_order_blocks | wrong | 8 | 8 | 5 | 2 |
| pilot17 | raw | saved_order_blocks | abstention | 3 | 3 | 1 | 0 |
| pilot17 | mean_detrended | iid | correct | 6 | 6 | 1 | 0 |
| pilot17 | mean_detrended | iid | wrong | 8 | 8 | 6 | 4 |
| pilot17 | mean_detrended | iid | abstention | 3 | 3 | 0 | 0 |
| pilot17 | mean_detrended | saved_order_blocks | correct | 6 | 6 | 0 | 0 |
| pilot17 | mean_detrended | saved_order_blocks | wrong | 8 | 8 | 5 | 2 |
| pilot17 | mean_detrended | saved_order_blocks | abstention | 3 | 3 | 1 | 0 |
| validation38 | raw | iid | correct | 13 | 11 | 5 | 2 |
| validation38 | raw | iid | wrong | 13 | 10 | 6 | 2 |
| validation38 | raw | iid | abstention | 12 | 9 | 3 | 2 |
| validation38 | raw | saved_order_blocks | correct | 13 | 11 | 5 | 2 |
| validation38 | raw | saved_order_blocks | wrong | 13 | 10 | 5 | 1 |
| validation38 | raw | saved_order_blocks | abstention | 12 | 9 | 3 | 2 |
| validation38 | mean_detrended | iid | correct | 13 | 11 | 5 | 2 |
| validation38 | mean_detrended | iid | wrong | 13 | 10 | 6 | 2 |
| validation38 | mean_detrended | iid | abstention | 12 | 9 | 3 | 2 |
| validation38 | mean_detrended | saved_order_blocks | correct | 13 | 11 | 4 | 2 |
| validation38 | mean_detrended | saved_order_blocks | wrong | 13 | 10 | 5 | 1 |
| validation38 | mean_detrended | saved_order_blocks | abstention | 12 | 9 | 3 | 2 |

## Known residual controls (nominal .05; not fresh validation)

| Control | Form | Scheme | N | Available | Flags |
|---|---|---|---:|---:|---:|
| constant_noise_quadratic_mean_error | raw | iid | 24 | 24 | 22 |
| constant_noise_quadratic_mean_error | raw | saved_order_blocks | 24 | 24 | 22 |
| constant_noise_quadratic_mean_error | mean_detrended | iid | 24 | 24 | 0 |
| constant_noise_quadratic_mean_error | mean_detrended | saved_order_blocks | 24 | 24 | 0 |
| heteroscedastic | raw | iid | 24 | 24 | 24 |
| heteroscedastic | raw | saved_order_blocks | 24 | 24 | 24 |
| heteroscedastic | mean_detrended | iid | 24 | 24 | 24 |
| heteroscedastic | mean_detrended | saved_order_blocks | 24 | 24 | 24 |
| independent_additive | raw | iid | 24 | 24 | 0 |
| independent_additive | raw | saved_order_blocks | 24 | 24 | 0 |
| independent_additive | mean_detrended | iid | 24 | 24 | 0 |
| independent_additive | mean_detrended | saved_order_blocks | 24 | 24 | 0 |

## Every primary reference-direction case

Adjusted p-values are from separate directional families (34 or 76 tests). A blank diagnostic does not imply constant variance. Ratios are of mean absolute deviations from bin medians, not ratios of structural noise variances.

| Panel | Pair | Outcome | N eval | Raw ratio | Detrended ratio | Raw IID adjusted p | Detrended IID adjusted p | Detrended block adjusted p |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| pilot17 | 1 | abstention | 64 | 3.163 | 2.367 | 1 | 1 | 0.6625 |
| pilot17 | 2 | correct | 64 | 1.841 | 1.769 | 1 | 1 | 1 |
| pilot17 | 3 | correct | 64 | 1.344 | 1.578 | 1 | 1 | 1 |
| pilot17 | 4 | wrong | 64 | 1.832 | 4.05 | 0.189 | 0.032 | 0.1305 |
| pilot17 | 13 | correct | 64 | 1.879 | 1.845 | 1 | 1 | 1 |
| pilot17 | 14 | wrong | 64 | 1.771 | 1.685 | 1 | 1 | 1 |
| pilot17 | 15 | wrong | 64 | 2.757 | 2.392 | 0.1015 | 0.221 | 0.224 |
| pilot17 | 16 | correct | 64 | 1.844 | 1.99 | 0.7475 | 0.7245 | 1 |
| pilot17 | 18 | wrong | 64 | 2.69 | 2.794 | 0.064 | 0.017 | 1 |
| pilot17 | 20 | wrong | 64 | 3.765 | 3.196 | 0.35 | 0.759 | 0.378 |
| pilot17 | 21 | abstention | 64 | 2.236 | 2.527 | 1 | 1 | 1 |
| pilot17 | 22 | wrong | 64 | 1.72 | 1.423 | 1 | 1 | 1 |
| pilot17 | 23 | correct | 64 | 1.781 | 1.69 | 1 | 1 | 1 |
| pilot17 | 24 | abstention | 64 | 1.509 | 1.37 | 1 | 1 | 1 |
| pilot17 | 56 | wrong | 64 | 4.239 | 4.666 | 0.017 | 0.017 | 0.017 |
| pilot17 | 86 | correct | 64 | 1.151 | 1.186 | 1 | 1 | 1 |
| pilot17 | 88 | wrong | 64 | 3.584 | 3.026 | 0.017 | 0.032 | 0.017 |
| validation38 | 5 | correct | 256 | 1.255 | 1.239 | 1 | 1 | 1 |
| validation38 | 6 | wrong | 256 | 2.764 | 2.767 | 0.038 | 0.038 | 0.038 |
| validation38 | 7 | abstention | 256 | 1.25 | 1.252 | 1 | 1 | 1 |
| validation38 | 8 | correct | 256 | 1.256 | 1.279 | 1 | 1 | 1 |
| validation38 | 9 | abstention | 256 | 2.642 | 2.691 | 0.038 | 0.038 | 0.038 |
| validation38 | 10 | wrong | 256 | 1.559 | 1.471 | 0.14 | 0.416 | 0.684 |
| validation38 | 11 | abstention | 256 | 2.882 | 2.803 | 0.038 | 0.038 | 0.038 |
| validation38 | 25 | wrong | 256 | 1.639 | 1.605 | 0.038 | 0.038 | 0.15 |
| validation38 | 26 | abstention | 256 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 27 | abstention | 256 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 28 | correct | 256 | 1.236 | 1.216 | 1 | 1 | 1 |
| validation38 | 29 | abstention | 256 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 30 | correct | 256 | 1.313 | 1.304 | 1 | 1 | 1 |
| validation38 | 31 | abstention | 256 | 1.461 | 1.423 | 0.5355 | 0.792 | 1 |
| validation38 | 32 | correct | 256 | 1.389 | 1.369 | 0.405 | 0.425 | 1 |
| validation38 | 33 | correct | 173 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 34 | correct | 173 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 35 | wrong | 173 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 36 | wrong | 173 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 37 | wrong | 173 | unavailable | unavailable | unavailable | unavailable | unavailable |
| validation38 | 38 | abstention | 256 | 1.109 | 1.104 | 1 | 1 | 1 |
| validation38 | 39 | abstention | 197 | 1.201 | 1.176 | 1 | 1 | 1 |
| validation38 | 40 | correct | 256 | 1.146 | 1.139 | 1 | 1 | 1 |
| validation38 | 41 | abstention | 256 | 1.329 | 1.376 | 1 | 1 | 1 |
| validation38 | 78 | correct | 256 | 3.239 | 3.294 | 0.038 | 0.038 | 0.038 |
| validation38 | 79 | correct | 256 | 1.442 | 1.475 | 1 | 0.987 | 1 |
| validation38 | 80 | correct | 256 | 2.015 | 1.955 | 0.038 | 0.038 | 0.038 |
| validation38 | 84 | abstention | 256 | 1.559 | 1.634 | 1 | 1 | 1 |
| validation38 | 91 | wrong | 75 | 2.251 | 2.189 | 0.062 | 0.118 | 1 |
| validation38 | 92 | wrong | 75 | 1.611 | 1.658 | 1 | 1 | 1 |
| validation38 | 97 | wrong | 101 | 1.306 | 1.449 | 1 | 1 | 1 |
| validation38 | 100 | correct | 105 | 1.449 | 1.538 | 1 | 1 | 1 |
| validation38 | 101 | correct | 150 | 1.445 | 1.435 | 0.705 | 1 | 1 |
| validation38 | 102 | wrong | 55 | 1.221 | 1.351 | 1 | 1 | 1 |
| validation38 | 103 | abstention | 55 | 1.401 | 1.365 | 1 | 1 | 1 |
| validation38 | 104 | wrong | 55 | 1.109 | 1.232 | 1 | 1 | 1 |
| validation38 | 106 | wrong | 57 | 3.458 | 3.397 | 0.062 | 0.118 | 0.065 |
| validation38 | 108 | wrong | 56 | 7.936 | 7.19 | 0.165 | 0.062 | 1 |

## Persistent wrong cases across saved splits

| Pair | Split | Raw IID adjusted p | Detrended IID adjusted p | Detrended block adjusted p |
|---|---:|---:|---:|---:|
| 91 | 261 | 0.062 | 0.118 | 1 |
| 91 | 1261 | 0.038 | 0.038 | 0.896 |
| 91 | 2261 | 0.598 | 0.135 | 0.575 |
| 92 | 261 | 1 | 1 | 1 |
| 92 | 1261 | 1 | 1 | 1 |
| 92 | 2261 | 1 | 1 | 1 |
| 108 | 261 | 0.165 | 0.062 | 1 |
| 108 | 1261 | 0.093 | 0.038 | 1 |
| 108 | 2261 | 0.038 | 0.057 | 1 |

Original ANM C/W/A totals: pilot 6/8/3; later primary 13/13/12. No new ANM direction is selected, and reference labels remain fallible. All opposite-direction values, split sensitivities and vectors are preserved in JSON.
