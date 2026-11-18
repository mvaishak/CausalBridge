# ANM synthetic success and real-data limits

## Scope fixed before fitting

`configs/anm-synthetic-panel.json` and `examples/anm_synthetic_panel.py` define a
new panel with fixed generators, seeds, sizes, splits and demonstration criteria.
The protocol and complete schedule were saved before any panel fits. The unchanged
producer was used; no model/LLM calls, parameter tuning, real validation outcomes,
or historical-result edits were involved. This is a new demonstration study,
not a reproduction of the missing original 48-dataset validation bundle.

There are **88 independently generated datasets**:

- 64 ANM-compatible cases: cubic, quadratic, sine and tanh functions, Gaussian
  or variance-one Laplace noise, scales 0.25/1, both causal column directions,
  and independent development/confirmation draws.
- 24 controls: linear Gaussian, Gaussian confounding and heteroscedastic mechanisms.
  Their construction arrows are recorded, but their causal accuracy is undefined.
- Each partition has 32 compatible cases and 12 controls. Confirmation has fresh
  seeds for the same function/noise settings, not unseen functions.
- Each dataset is generated once at 512 rows. Its first 128 rows form the smaller
  sample. Both sizes use splits 261/1261. These repeated evaluations are dependent.

The baseline gamma=1, alpha=0.1, half training/evaluation split and threshold
0.001 stay fixed. The primary endpoint is **confirmation, n=512, split 261**.
The demonstration gate requires at least 50% coverage and 75% answered accuracy,
plus at least 50% coverage/accuracy in every compatible family, zero execution
errors and passing column-swap checks. These are local engineering demonstration
criteria, not an externally preregistered general-reliability standard. No family,
seed, error or abstention is removed after looking at performance.

## Results

| Partition | Rows | Split | Correct / wrong / abstain | Answered accuracy | Coverage | Correct yield |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Development | 128 | 261 | 20 / 8 / 4 | 71.4% | 87.5% | 62.5% |
| Development | 128 | 1261 | 20 / 7 / 5 | 74.1% | 84.4% | 62.5% |
| Development | 512 | 261 | 24 / 0 / 8 | 100% | 75.0% | 75.0% |
| Development | 512 | 1261 | 26 / 0 / 6 | 100% | 81.3% | 81.3% |
| Confirmation | 128 | 261 | 20 / 7 / 5 | 74.1% | 84.4% | 62.5% |
| Confirmation | 128 | 1261 | 18 / 7 / 7 | 72.0% | 78.1% | 56.3% |
| **Confirmation** | **512** | **261** | **26 / 0 / 6** | **100%** | **81.3%** | **81.3%** |
| Confirmation | 512 | 1261 | 26 / 0 / 6 | 100% | 81.3% | 81.3% |

Primary family results retain all eight cases per family:

| Family | Correct / wrong / abstain | Answered accuracy | Coverage |
| --- | --- | ---: | ---: |
| Cubic | 5 / 0 / 3 | 100% | 62.5% |
| Quadratic | 8 / 0 / 0 | 100% | 100% |
| Sine | 6 / 0 / 2 | 100% | 75.0% |
| Tanh | 7 / 0 / 1 | 100% | 87.5% |

The fixed demonstration gate **passes**. Correct yield improves from 62.5% to
81.3% at the primary confirmation split, so the gain is not solely a change in
the answered denominator. Increasing rows changes both training and dependence
evaluation sizes (and the behavior of the fixed ridge procedure); this experiment
does not isolate which component produces the improvement.

Additional **post-outcome descriptive** checks, separate from the predeclared
demonstration gate, retain all confirmation split outcomes, including abstentions:

| Recovery diagnostic | n=128 | n=512 |
| --- | ---: | ---: |
| Correct raw directional signs | 43/64 = 67.2% | 60/64 = 93.8% |
| Same nonzero sign across both splits | 23/32 = 71.9% | 28/32 = 87.5% |
| Weakest family's raw-sign recovery | 8/16 = 50% | 13/16 = 81.3% |

The 64 split outcomes still represent 32 independent confirmation datasets, not
64 datasets. These diagnostics address the possibility that conditional accuracy
improved solely by abstaining. They are not a rerun of the original report's gate
on its original data and do not overturn its n=128 failure.

Control releases at the primary confirmation split:

| Control | n=128 answers / cases | n=512 answers / cases | Causal accuracy |
| --- | --- | --- | --- |
| Linear Gaussian | 3 / 4 | 0 / 4 | Undefined |
| Confounded Gaussian | 3 / 4 | 0 / 4 | Undefined |
| Heteroscedastic | 4 / 4 | 2 / 4 | Undefined |

The remaining heteroscedastic releases matter: this producer still does not
certify its assumptions. The small panel, fixed mechanisms and absence of exact
identifiability proofs for every generator triple limit the claim. **The result
demonstrates success on these synthetic compatible cases, not reliable recovery
on arbitrary real pairs or a production repair.** No confidence interval or
population-level reliability claim is made.

## Real-development transfer check

After the synthetic result, `configs/anm-development-large-sample.json` fixed a
baseline-versus-larger-sample comparison on the same four allowed real development
pairs. No real validation pair was used. Three pairs provide 512 rows; MOPEX pair
93 has only 432, which is reported explicitly. Existing selection across sizes is
not guaranteed nested, unlike the synthetic panel.

At split 261, pair 99 changes to the correct direction; pairs 12/17/93 remain
wrong. Unweighted answered accuracy is 1/4=25%; benchmark-weighted answered
accuracy/correct yield is 33.3%, coverage 100% and wrong yield 66.7%. Other splits
1261 and 2261 still have zero answered accuracy. This is an unstable development
result, not evidence that the synthetic improvement has transferred reliably.

## Artifacts and reproduction

```bash
uv run --extra anm python examples/anm_synthetic_panel.py \
  --plan configs/anm-synthetic-panel.json --output runs/anm-synthetic-panel-new
uv run --extra anm python -m causalbridge.discovery.study development \
  --snapshot runs/pilot-preparation/raw --manifest configs/pilot-data.json \
  --roster configs/evaluation-roster.json \
  --plan configs/anm-development-large-sample.json \
  --output runs/anm-development-large-new
```

Use fresh outputs. Plans, generator source and producer identities are recorded
before fitting. The panel has 352 original attempts plus 176 swap attempts; no
execution errors, and every swap check passes. Each attempt has an independently
saved original numeric request/config/sample and validated result artifacts.

Saved local outputs: `runs/anish-anm-synthetic-panel-01/` and
`runs/anish-anm-development-large-01/` (ignored). A separate cached reconciliation
regenerated all 88 datasets from seeds, verified the exact 352-case/size/split
schedule, every prefix sample, request/result binding, truth and metric, and all
176 swapped directions/scores. Report: `runs/anish-anm-synthetic-panel-audit-01.json`.
This is an artifact/accounting audit, not a second numerical implementation.

## Next decision

There is now positive evidence that the unchanged ANM works under the tested
synthetic settings with more observations. Do not discard the earlier failures:
the real development panel remains unreliable, and controls show residual
over-release. Keep the 38 real validation pairs unused. A real-data candidate
needs defensible development performance, assumption review and explicit criteria
before freezing. An alternative project scope can study LLM responses to fallible
method evidence, but must state that premise rather than claim reliable assistance.
