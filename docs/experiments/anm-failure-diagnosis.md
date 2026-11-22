# ANM failure diagnosis: offline evidence and next decision

Branch: `codex/anm-failure-diagnosis-20261121`, from GitHub main `fb81b96`.
This work is separate from `codex/anm-evidence-investigation-20261121`.
It characterizes the upstream diagnostic; the other branch investigates downstream
LLM responses to controlled misleading cues. Neither needs the other's new results.

## Scope and output

This is a post-outcome descriptive audit of opened data, not a new calibrated ANM,
parameter search, independent holdout, or demonstrated accuracy improvement.
The full report is [anm-failure-diagnosis.md](../reviews/anm-failure-diagnosis.md).
Reproducible numeric artifacts and figures are under
`artifacts/anm-failure-diagnosis-20261121/`.

The audit verifies all 7,125 archive members before copying bytes into a temporary
directory. It uses the production saved-input loader and independently joins the
frozen roster, column mapping and results. It verifies 114 validation, 72 development,
24 larger-development and 352 synthetic attempts. These 562 attempts include repeated
settings, sizes and splits: they are not 562 independent real datasets.
Original files are never changed. No LLM calls, new ANM fits, new permutation tests,
new exclusions, favorable-seed replacement or threshold search are performed.

Checks include independently saved request/sample/configuration digests, seeded
column order, mapping identity, selected-index counts, exact split reconstruction,
result/reproducibility binding, threshold/sign arithmetic, training-only means and
standard deviations, and cached prediction-MSE/residual-moment agreement. The full
upstream snapshot is not required, so source-row selection is not reconstructed
from raw source files. This audit is not a fresh independent KRR/HSIC implementation.

## Reproduce from a clean checkout

Python 3.12 and uv are the existing project prerequisites. All numeric input artifacts
are committed; no data download, local ignored snapshot, model server, API key or GPU
is needed. Use a new output directory each time.

```sh
uv sync --frozen --dev --extra anm
uv run --extra anm python -m pytest tests/test_anm_failure_audit.py -q
uv run --extra anm python scripts/diagnose_anm_failures.py --output runs/anm-failure-audit-new
```

Outputs:

- `metrics.json`: source hashes, frozen-input hashes, exact metrics and scope.
- `case-results.json` and CSV: 38 primary cases, split stability and data features.
- `real-attempts.json`: all 114 validation split outcomes, preserving primary labels.
- `report.md`: generated findings, every wrong primary case, limitations and next work.

Optional standard scientific plots use a separate, pinned rendering dependency:

```sh
uv run --with matplotlib==3.10.6 python scripts/plot_anm_failures.py --analysis runs/anm-failure-audit-new --output runs/anm-failure-figures-new
```

The renderer reads saved metrics only and records the input digest and Matplotlib
version. PNG/SVG visuals can differ across fonts/platforms; numeric metrics are the
source of truth. The renderer is optional, keeping the production dependency set
unchanged. It was executed and the resulting PNGs visually inspected for this audit.

The usual `bash scripts/check.sh` runs the full suite, lint/format, scripted demos,
synthetic ANM handshake and package builds. The handshake performs its existing
small synthetic software fit; the new diagnosis command itself performs none.
Two existing tests may skip when the optional full upstream snapshot is absent.

## Outcome definitions and sample units

- Correct/wrong: a successful non-null ANM direction versus the benchmark reference.
- Abstention: successful ANM execution with null direction under the frozen threshold.
- Execution failure: an ANM error, never an abstention. The archived validation has zero.
- There is no LLM checker or verification-rejection population in this ANM-only audit.
- Yields and coverage retain all 38 cases per split. Answered accuracy uses directional
  answers only. Weighted yields use the original total benchmark weight 10.8.
- Splits reuse cases and selected samples; the independent case count stays 38.
- Source families are dependent clusters. Counts and descriptive associations are
  reported without significance tests or independent-observation assumptions.
- The >=10% tie bin is an explicit post-outcome descriptive choice, not an exclusion
  rule or causal hypothesis test. Sample size, ties and source group are correlated.
- The margin rank AUC uses answered correct versus wrong cases only. It is a ranking
  statistic, not a posterior probability, calibration estimate or selected threshold.
- Synthetic sample-size transitions are matched within dataset ID. Larger samples
  change both training and evaluation size; they do not isolate those components.
- Linear Gaussian and other historical assumption-control correctness remains null;
  generative arrow labels are not retroactively used to score nonidentified controls.
- Existing adequacy p-values are cached 199-permutation results on four development
  pairs. Nonrejection is not independence, and exchangeability is not established.

## Interpretation and proposed follow-up

The audit separates verified behavior from plausible causes. Split-sensitive wrong
arrows suggest instability. Persistent wrong arrows show stability is insufficient.
Wrong answers despite lower reference-direction MSE show that the ANM's residual
independence ranking, rather than predictive error alone, determines the preference.
None of these observations identifies a unique cause of failure on a real pair.

A useful next numerical study would freeze independent, known-truth synthetic
conditions, then vary training size and evaluation size separately. In a different
controlled factor, change one assumption (for example, noise dependence on the cause)
while retaining the mechanism and noise draws where possible. Use multiple fresh
dataset seeds and predeclare outcomes. This can test a specific mechanism without
retuning on opened real pairs. It is a proposal; no such new fits were run here.

Review original unit-level metadata for the three persistently wrong real cases
before asserting confounding, dependence, measurement artifacts or label errors.
The current source descriptions can flag concerns but cannot establish the cause.
Do not replace benchmark labels or drop cases to obtain a positive result.

Related context: [Peters et al., 2014](https://jmlr.org/papers/v15/peters14a.html)
states an additive-noise identification result under conditions. The benchmark study
[Mooij et al., 2016](https://jmlr.org/papers/v17/14-518.html) documents useful ANM results
with other implementation/evaluation choices. Our result concerns this fixed setup
and cohort, rather than a refutation of ANM as an entire method family.

## Source-context provenance

`configs/anm-failure-case-metadata.json` stores manual paraphrases for persistent
wrong pairs 91, 92 and 108. On 21 November, their original description bytes were
read from the available hash-verified snapshot and matched against
`configs/pilot-data.json`. Replay checks the saved description digests and pair IDs;
it does not pretend to automatically validate the meaning of the paraphrases.
The full source archive URL and member names are retained. A reviewer with the
snapshot can independently compare each description's SHA-256 and read the source.

Pairs 91 and 92 share forest-plot source data; pair 108 measures an engine rotation
time and heat-bath temperature. These facts motivate questions about omitted
variables, missing-data selection, measurement effects and dependence. They do not
identify which assumption, if any, caused a wrong direction. Adjacent selected-row
correlations are descriptive only: sorting alone can produce high correlations in
otherwise independently sampled data. They are not a valid test of serial dependence
or proof that random train/test splitting leaked physical observations.

The proposed component investigation has since been executed separately as
[anm-mechanism-study-v1](anm-mechanism-study-v1.md). The saved-data audit and its
frozen outputs remain unchanged; the new synthetic fits have their own protocol,
raw archive, analysis and limitations.
