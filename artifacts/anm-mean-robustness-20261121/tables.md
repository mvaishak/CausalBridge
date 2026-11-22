# Fixed mean-estimator robustness results

Exploratory, selected opened pilot cases. MSE is held-out effect prediction error in original ANM training-standardized units, not true mean-function error.

All p-values below are nominal Holm-adjusted across eight cases separately per estimator/mode/scheme. Block permutation is only a row-order heuristic.

| Pair | Original outcome | Estimator | MSE | Raw spread ratio | Raw IID p | Raw block p | Detrended spread ratio | Detrended IID p | Detrended block p |
|---|---|---|---|---|---|---|---|---|---|
| 2 | correct | original_krr | 0.471162 | 1.84103 | 0.315 | 0.24 | 1.68729 | 0.6775 | 0.642 |
| 2 | correct | smooth_krr | 0.498345 | 1.89535 | 0.155 | 0.115 | 1.72257 | 0.3375 | 0.285 |
| 2 | correct | flexible_krr | 0.551562 | 2.23555 | 0.063 | 0.042 | 2.17304 | 0.105 | 0.06 |
| 2 | correct | local_linear | 0.496191 | 1.91009 | 0.155 | 0.093 | 1.73616 | 0.2625 | 0.186 |
| 3 | correct | original_krr | 0.675784 | 1.34384 | 1 | 0.984 | 1.41143 | 0.743 | 0.642 |
| 3 | correct | smooth_krr | 0.687313 | 1.39075 | 1 | 0.878 | 1.42082 | 0.922 | 0.675 |
| 3 | correct | flexible_krr | 0.60227 | 1.87818 | 0.394 | 0.346 | 1.85137 | 0.376 | 0.264 |
| 3 | correct | local_linear | 0.658859 | 1.38517 | 1 | 0.893 | 1.41866 | 0.894 | 0.657 |
| 13 | correct | original_krr | 0.468183 | 1.87906 | 0.614 | 0.49 | 1.77947 | 0.6775 | 0.642 |
| 13 | correct | smooth_krr | 0.476808 | 2.08112 | 0.428 | 0.458 | 1.92784 | 0.486 | 0.512 |
| 13 | correct | flexible_krr | 0.460171 | 1.55192 | 0.8205 | 0.7335 | 1.51923 | 1 | 0.93 |
| 13 | correct | local_linear | 0.47395 | 1.96111 | 0.48 | 0.524 | 1.86409 | 0.554 | 0.568 |
| 16 | correct | original_krr | 0.686035 | 1.84382 | 0.228 | 0.3025 | 1.77877 | 0.564 | 0.642 |
| 16 | correct | smooth_krr | 0.620976 | 2.12344 | 0.027 | 0.102 | 1.87794 | 0.156 | 0.3375 |
| 16 | correct | flexible_krr | 0.903247 | 2.13801 | 0.185 | 0.0775 | 1.94916 | 0.2 | 0.25 |
| 16 | correct | local_linear | 0.62225 | 2.04577 | 0.042 | 0.093 | 1.83156 | 0.213 | 0.285 |
| 23 | correct | original_krr | 0.880953 | 1.78089 | 0.614 | 0.49 | 1.64665 | 0.6775 | 0.642 |
| 23 | correct | smooth_krr | 0.835207 | 1.83412 | 0.428 | 0.458 | 1.69202 | 0.486 | 0.519 |
| 23 | correct | flexible_krr | 1.31945 | 1.08159 | 1 | 1 | 1.2311 | 1 | 1 |
| 23 | correct | local_linear | 0.771924 | 1.7944 | 0.48 | 0.524 | 1.63484 | 0.554 | 0.568 |
| 56 | wrong | original_krr | 0.625278 | 4.23873 | 0.004 | 0.0105 | 4.06112 | 0.004 | 0.012 |
| 56 | wrong | smooth_krr | 0.611144 | 4.31241 | 0.004 | 0.004 | 4.37277 | 0.004 | 0.008 |
| 56 | wrong | flexible_krr | 0.583568 | 3.63317 | 0.004 | 0.0175 | 3.44523 | 0.004 | 0.016 |
| 56 | wrong | local_linear | 0.632764 | 4.59747 | 0.004 | 0.004 | 4.25964 | 0.004 | 0.008 |
| 86 | correct | original_krr | 0.450675 | 1.15123 | 1 | 0.984 | 1.03007 | 0.9865 | 0.989 |
| 86 | correct | smooth_krr | 0.450359 | 1.10379 | 1 | 0.94 | 1.04258 | 0.987 | 0.982 |
| 86 | correct | flexible_krr | 0.471728 | 1.12318 | 1 | 1 | 1.27371 | 1 | 1 |
| 86 | correct | local_linear | 0.432974 | 1.13758 | 1 | 0.893 | 1.1248 | 0.894 | 0.877 |
| 88 | wrong | original_krr | 0.754295 | 3.58418 | 0.004 | 0.004 | 3.1377 | 0.014 | 0.012 |
| 88 | wrong | smooth_krr | 0.737641 | 3.5795 | 0.004 | 0.004 | 3.22833 | 0.014 | 0.008 |
| 88 | wrong | flexible_krr | 0.743492 | 3.24035 | 0.007 | 0.004 | 2.77821 | 0.0385 | 0.0455 |
| 88 | wrong | local_linear | 0.737225 | 3.5376 | 0.004 | 0.004 | 3.09844 | 0.0175 | 0.008 |

## Synthetic controls

Eight function/seed settings (four random draws reused across two fixed functions), reused across regimes/estimators. Counts use unadjusted IID p≤0.05; trials are paired.

| Regime | Estimator | N | Median true mean MSE | Raw flags | Detrended flags |
|---|---|---|---|---|---|
| independent_additive | original_krr | 8 | 0.0182445 | 0 | 0 |
| independent_additive | smooth_krr | 8 | 0.0122967 | 0 | 0 |
| independent_additive | flexible_krr | 8 | 0.0235846 | 0 | 0 |
| independent_additive | local_linear | 8 | 0.0577058 | 0 | 1 |
| heteroscedastic | original_krr | 8 | 0.0094651 | 8 | 8 |
| heteroscedastic | smooth_krr | 8 | 0.0108614 | 8 | 8 |
| heteroscedastic | flexible_krr | 8 | 0.0112694 | 8 | 8 |
| heteroscedastic | local_linear | 8 | 0.0507552 | 8 | 8 |
