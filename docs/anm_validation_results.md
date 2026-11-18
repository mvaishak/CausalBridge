# Descriptive test on the 38 real validation pairs

On 18 November 2026, Anish explicitly authorized testing the 38 validation pairs
without tuning on them. These outcomes are now opened. The fixed configuration
was chosen before this test: up to 512 rows, gamma 1, ridge alpha 0.1, threshold
0.001, sampling seed 262 and split seeds 261/1261/2261. Split 261 is primary;
secondary results do not replace it. Only `sample_512` is executed, not a grid.

This is a descriptive test, not a claim that a candidate passed an agreed
reliability criterion. No acceptance threshold is invented. The normal ANM
procedure fits regression on half of each pair's observations and evaluates
residuals on the other half. There is no cross-pair training or label-based
parameter selection. References are joined after numerical execution.

## Results

| Fixed split | Correct | Wrong | Abstain | Unweighted answered accuracy | Weighted answered accuracy | Weighted coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **261 (primary)** | **13** | **13** | **12** | **50.0%** | **48.1%** | **73.4%** |
| 1261 | 20 | 7 | 11 | 74.1% | 53.2% | 76.0% |
| 2261 | 14 | 9 | 15 | 60.9% | 60.5% | 61.9% |

All 38 pairs from 12 source groups remain in every denominator. Total benchmark
weight is 10.8. Primary weighted correct yield is 35.3%, wrong yield 38.1%;
unweighted coverage is 26/38=68.4%. Raw-margin signs agree nontrivially across all
three splits on 23/38 pairs (60.5%). There are zero execution errors. Repeated
splits are not independent causal examples; no confidence interval is claimed.

Actual selected sizes range from 109 to 512: 22 pairs supply 512 observations,
16 have fewer. This differs from the synthetic panel's exact 512-row samples.
No pair is removed, padded or imputed to improve performance. The synthetic
success does not establish robust transfer here.

## Protocol, audit and reproduction

`examples/anm_validation_test.py` refuses changes to declared settings or splits
before opening data. It verifies the frozen roster and writes protocol/source
identities and roster/manifest digests before fitting. It executes only assigned
validation cases, with independently saved original requests/results.

```bash
uv run --extra anm python examples/anm_validation_test.py \
  --snapshot runs/pilot-preparation/raw --manifest configs/pilot-data.json \
  --roster configs/evaluation-roster.json \
  --plan configs/anm-development-large-sample.json \
  --output runs/anm-validation-test-new
```

Fresh outputs are mandatory. Reproduction repeats the same configuration; it must
not search for a better setting or favorable split. Original manifests, roles,
source bytes and historical predictions are unchanged. No LLM/API/server calls.

Local artifacts: `runs/anish-anm-validation-test-01/`. The separate cached audit
verified the exact 38 case IDs and 114 request identities/configurations, decoded
predictions back to original columns and recomputed weighted metrics for every
split. Audit: `runs/anish-anm-validation-test-audit-01.json`. This is artifact/
accounting verification, not a second independent numerical implementation.

The original roster still records these pairs as validation to preserve provenance,
but they are **no longer untouched**. If their outcomes influence later changes,
those changes need a new source-separated holdout for a fresh final assessment.
Do not claim future tuning against these results retains the original holdout.
