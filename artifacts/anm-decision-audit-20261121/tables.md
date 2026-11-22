# Independent ANM numerical and decision audit

All cases use original fixed settings and splits. No new release policy is deployed. Adequacy rejections are nominal; nonrejection does not verify independence.

| Panel | Outcome | N | Both rejected IID .05 | Both rejected IID .025 | Both rejected blocks .025 | Selected direction rejected IID .025 |
|---|---|---|---|---|---|---|
| pilot17 | correct | 6 | 1 | 0 | 1 | 0 |
| pilot17 | wrong | 8 | 3 | 2 | 1 | 2 |
| pilot17 | abstention | 3 | 2 | 0 | 0 | 0 |
| validation38 | correct | 13 | 8 | 7 | 3 | 7 |
| validation38 | wrong | 13 | 5 | 5 | 4 | 5 |
| validation38 | abstention | 12 | 7 | 7 | 6 | 0 |

## Existing synthetic evidence (no new synthetic fits)

Previous 99-permutation nominal .05 checks; fixed train/evaluation sizes 256/256. Do not directly equate these with the new 1,999-permutation real checks.

| Regime | Outcome | N | Both directions rejected |
|---|---|---|---|
| independent_additive | correct | 24 | 6 |
| independent_additive | wrong | 0 | 0 |
| independent_additive | abstention | 0 | 0 |
| heteroscedastic | correct | 2 | 2 |
| heteroscedastic | wrong | 17 | 17 |
| heteroscedastic | abstention | 5 | 5 |

## Per-case diagnostics

| Panel | Pair | Original outcome | IID p A→B | IID p B→A | Block p A→B | Block p B→A |
|---|---|---|---|---|---|---|
| validation38 | 5 | correct | 0.001 | 0.004 | 0.0035 | 0.02 |
| validation38 | 6 | wrong | 0.001 | 0.0005 | 0.0015 | 0.0005 |
| validation38 | 7 | abstention | 0.003 | 0.0055 | 0.006 | 0.01 |
| validation38 | 8 | correct | 0.0005 | 0.031 | 0.0005 | 0.0505 |
| validation38 | 9 | abstention | 0.0005 | 0.0005 | 0.001 | 0.002 |
| validation38 | 10 | wrong | 0.0165 | 0.0005 | 0.039 | 0.001 |
| validation38 | 11 | abstention | 0.0005 | 0.0005 | 0.001 | 0.0005 |
| validation38 | 25 | wrong | 0.1395 | 0.0035 | 0.393 | 0.062 |
| validation38 | 26 | abstention | 0.477 | 0.1345 | 0.661 | 0.3465 |
| validation38 | 27 | abstention | 0.019 | 0.016 | 0.172 | 0.178 |
| validation38 | 28 | correct | 0.0005 | 0.193 | 0.005 | 0.3175 |
| validation38 | 29 | abstention | 0.3935 | 0.0815 | 0.7345 | 0.4175 |
| validation38 | 30 | correct | 0.0005 | 0.0055 | 0.0005 | 0.0495 |
| validation38 | 31 | abstention | 0.054 | 0.018 | 0.1495 | 0.061 |
| validation38 | 32 | correct | 0.2965 | 0.0005 | 0.5365 | 0.0005 |
| validation38 | 33 | correct | 0.001 | 0.0035 | 0.0005 | 0.0155 |
| validation38 | 34 | correct | 0.006 | 0.3455 | 0.0535 | 0.588 |
| validation38 | 35 | wrong | 0.0015 | 0.0005 | 0.001 | 0.0005 |
| validation38 | 36 | wrong | 0.0005 | 0.0005 | 0.0005 | 0.0005 |
| validation38 | 37 | wrong | 0.0005 | 0.0005 | 0.0005 | 0.001 |
| validation38 | 38 | abstention | 0.5435 | 0.121 | 0.5435 | 0.153 |
| validation38 | 39 | abstention | 0.0025 | 0.002 | 0.0025 | 0.0005 |
| validation38 | 40 | correct | 0.0005 | 0.225 | 0.0005 | 0.212 |
| validation38 | 41 | abstention | 0.003 | 0.004 | 0.0055 | 0.006 |
| validation38 | 78 | correct | 0.0005 | 0.0005 | 0.0005 | 0.0005 |
| validation38 | 79 | correct | 0.0005 | 0.002 | 0.0005 | 0.069 |
| validation38 | 80 | correct | 0.0005 | 0.0055 | 0.0005 | 0.08 |
| validation38 | 84 | abstention | 0.002 | 0.0005 | 0.0015 | 0.0005 |
| validation38 | 91 | wrong | 0.0165 | 0.0515 | 0.0785 | 0.17 |
| validation38 | 92 | wrong | 0.043 | 0.1035 | 0.07 | 0.413 |
| validation38 | 97 | wrong | 0.1495 | 0.011 | 0.2955 | 0.08 |
| validation38 | 100 | correct | 0.0235 | 0.0005 | 0.1365 | 0.0005 |
| validation38 | 101 | correct | 0.0005 | 0.1145 | 0.0005 | 0.14 |
| validation38 | 102 | wrong | 0.567 | 0.1925 | 0.7315 | 0.3865 |
| validation38 | 103 | abstention | 0.5255 | 0.3805 | 0.537 | 0.423 |
| validation38 | 104 | wrong | 0.28 | 0.099 | 0.302 | 0.1735 |
| validation38 | 106 | wrong | 0.2445 | 0.0725 | 0.2975 | 0.1505 |
| validation38 | 108 | wrong | 0.1925 | 0.0005 | 0.66 | 0.049 |
| pilot17 | 1 | abstention | 0.0055 | 0.0265 | 0.0045 | 0.0505 |
| pilot17 | 2 | correct | 0.0015 | 0.04 | 0.009 | 0.0135 |
| pilot17 | 3 | correct | 0.002 | 0.178 | 0.004 | 0.1325 |
| pilot17 | 4 | wrong | 0.465 | 0.009 | 0.537 | 0.0155 |
| pilot17 | 13 | correct | 0.0075 | 0.086 | 0.032 | 0.1625 |
| pilot17 | 14 | wrong | 0.0015 | 0.1125 | 0.0035 | 0.1945 |
| pilot17 | 15 | wrong | 0.0105 | 0.0275 | 0.029 | 0.1505 |
| pilot17 | 16 | correct | 0.0645 | 0.004 | 0.119 | 0.011 |
| pilot17 | 18 | wrong | 0.001 | 0.001 | 0.034 | 0.0475 |
| pilot17 | 20 | wrong | 0.0355 | 0.3305 | 0.023 | 0.4395 |
| pilot17 | 21 | abstention | 0.0435 | 0.0215 | 0.0535 | 0.09 |
| pilot17 | 22 | wrong | 0.0075 | 0.14 | 0.0055 | 0.188 |
| pilot17 | 23 | correct | 0.623 | 0.123 | 0.6385 | 0.174 |
| pilot17 | 24 | abstention | 0.0695 | 0.1165 | 0.0445 | 0.144 |
| pilot17 | 56 | wrong | 0.4305 | 0.0005 | 0.4145 | 0.0005 |
| pilot17 | 86 | correct | 0.355 | 0.757 | 0.2935 | 0.73 |
| pilot17 | 88 | wrong | 0.0065 | 0.0015 | 0.016 | 0.001 |
