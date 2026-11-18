# ANM producer and independently saved original requests

Current development follow-up: [ANM development workflow/results](anm_development.md)
documents the four implemented chunks, the executed 72-attempt development
comparison and controls, and the protected candidate-freeze/validation path.
The original producer calculations and pilot threshold are unchanged. No real
validation candidate is frozen and no real held-out outcomes have been opened.

Status: implemented locally on `codex/anish-anm-provenance`, based on merged main
`48d6cda` (PR #4). The detailed implementation roadmap governs scope. The exact
[Track B integration contract](track_b_integration_contract.md) governs transport.
No existing predictor, verifier, binding schema, or release rule was changed.

## What Anish supplies

- Track A: `tools.engine.CausalEngineBackend`, reusable exact binary calculations,
  and an independent rational-arithmetic confirmation of the merged witness/pilot.
- Track B: numeric display summaries, held-out bidirectional KRR/HSIC diagnostics,
  immutable-by-API input artifacts, the original `ANMRequestBinding`, and the
  existing `ANMResult`/`ANMProvenance` types.
- A synthetic numerical handshake through Vaishak's existing predictor/checker.
  Its model reply is scripted. It is not a Tuebingen or live-LLM experiment.

All remote branches were inspected. Graph/witness work and the small Track A
pilot are merged. Track B interfaces are merged in PR #4. The current remote
branches do not contain Faizah's real-data loader/scorer or Kris's actual
experiment runner. Those modules are not implemented as substitutes here.

## The essential requirement: receipt before result

Use `save_anm_request` BEFORE `execute_anm_request`. Saving validates numeric
A/B inputs, snapshots them, selects a deterministic train/evaluation partition,
and persists the request independently. It does not execute regression, import
NumPy, inspect a method result, or read evaluator labels.

```python
from pathlib import Path
from causalbridge.discovery.anm_requests import ANMConfig, save_anm_request
from causalbridge.discovery.anm import execute_anm_request, load_anm_artifacts

folder = Path("runs/anm-case-001")  # must not already exist
original = save_anm_request(
    rows,
    case_id="D001",
    ab_mapping_id="opaque-map-001",
    directory=folder,
    config=ANMConfig(),  # threshold=None: scores without a direction decision
)
result = execute_anm_request(folder)
artifacts = load_anm_artifacts(folder)
assert artifacts.request == original
```

The runner supplies already selected, ordered scalar pairs. No automatic
subsampling, row removal, imputation, orientation change, or name/label access
occurs. `sampling_seed` describes the caller's selection; this module cannot
certify that selection. NumPy arrays, numeric lists and tuples normalize into
finite float pairs. Booleans, strings, malformed rows and nonfinite values fail
at the transport boundary before a valid numeric request can be created.

Well-formed but empty, too-small, oversized or low-variation samples can still
have a truthful request digest. They are persisted and then return typed
input-validation errors. Invalid configuration/schema inputs raise before
persistence; do not fabricate provenance for unhashable/invalid inputs.

## Files and exact digest scopes

Every attempt uses a fresh directory. Files are exclusively created, flushed,
and fsynced, including directory entries. The API never overwrites an original.

| File | Saved when / purpose |
| --- | --- |
| `sample.json` | Before execution: normalized `ab_mapping_id` and ordered A/B `rows`. |
| `config.json` | Before execution: validated ANMConfig JSON, including every default. |
| `request.json` | Before execution: exact `ANMRequestBinding`, directly readable by Kris/Vaishak. |
| `inputs.json` | Before execution: request/sample/config/split digests. |
| `execution_started.json` | Exclusive execution claim before numerical work; prevents rerunning one attempt. |
| `reproducibility.json` | Actual split indices, preprocessing, parameters, threshold/version and dependencies. |
| `result.json` | Existing ANMResult; written last as the completion marker. |

Use the existing `canonical_digest` function: `sha256:` plus 64 lowercase hex
characters, over UTF-8 JSON with sorted keys, compact separators, ASCII escaping,
and no NaN/Infinity. These are content hashes of validated JSON, not hashes of
file whitespace and not RFC 8785. Integers in measurements normalize to floats
before hashing. Ordered rows, A/B orientation and `-0.0` remain significant.

- `sample_digest`: canonical ANMSample `{ab_mapping_id, rows}` only. It is the
  complete method sample, NOT the smaller displayed sample.
- `config_digest`: complete validated ANMConfig JSON, including threshold,
  threshold-selection version, seeds, split fraction, limits, estimator and
  method/configuration versions.
- `request_digest`: complete saved ANMRequestBinding JSON. Also recorded in the
  pre-execution manifest and the reproducibility record.
- `split_digest`: canonical `{training_indices, evaluation_indices}`.
- `reproducibility_ref`: canonical complete reproducibility record; no circular
  result hash is included. The loader checks this reference and input bindings.

`load_anm_request(folder)` verifies originals against actual saved sample/config
and manifest without reading any result. `load_anm_artifacts(folder)` additionally
validates the result, all request/provenance fields, threshold, record reference,
configuration and original split indices. A missing request causes an error;
there is no fallback that projects request fields from result provenance.

Digests are consistency receipts, not signatures. Trusted artifact storage and a
correct initial mapping are still required. A caller that rewrites all trusted
originals consistently is outside this guarantee. An interrupted attempt stays
visible; create a new directory rather than overwrite or silently rerun it.

## Numerical method and configurable pilot defaults

The optional `anm` extra adds NumPy. Kernel ridge regression is implemented with
an explicit linear solve; scikit-learn/SciPy are not required. The base Track A
engine, request saving, and display summaries work without NumPy.

| Setting | Default / precise behavior |
| --- | --- |
| Method version | `anm-krr-hsic-1.0` |
| Configuration version | `pilot-1` |
| Threshold / selection version | null / `not-calibrated` |
| Selected rows | Caller supplied; min 100, max 256; no hidden resampling. Max configurable up to 2048. |
| Split | `random.Random(split_seed).shuffle` on ordered row indices; first floor(n*0.5) train, remainder evaluation. |
| Seeds | sampling=261, split=261; both preserved in request/config. |
| Standardization | A/B training means and population std (ddof=0); same transform on evaluation rows. |
| Regression | Both directions: RBF KRR, gamma=1.0, ridge alpha=0.1; solve `(K + alpha I)c = y`. |
| Residuals | Evaluation outcomes minus evaluation predictions; center/scale by evaluation residual mean/population std for the diagnostic only. |
| HSIC | Biased RBF HSIC `sum(K_centered * L_centered)/n^2`. Each bandwidth is the median strictly positive off-diagonal Euclidean distance. Kernel `exp(-distance^2/(2*sigma^2))`. |
| Scores | `score_ab=HSIC(A, B residual)`; `score_ba=HSIC(B, A residual)`; lower dependence favored. |
| Margin | `score_ba - score_ab`; no presentation rounding before deciding. |

Configured tau: `margin > tau` chooses A_to_B; `margin < -tau` chooses B_to_A;
closed interval `[-tau,tau]` yields `decision=abstain`, null predicted_direction,
reason `ambiguous_margin`. Directional success has null reason. Unconfigured tau
retains scores but has null threshold/decision/direction and
`reason_code=threshold_not_configured`, exactly as the merged schema requires.

No scientific threshold is selected here. Use development groups, freeze it in
ANMConfig with configuration/threshold-selection versions, then run held-out data.
The example's explicit zero threshold is synthetic smoke configuration only.
All returned results state that ANM assumptions, no confounding/feedback, and
independent sampling are unverified. Scores are not causal probabilities.

## Errors and caller responsibilities

| Reason | Existing ANMResult error_category |
| --- | --- |
| insufficient_rows, too_many_rows, insufficient_split_rows, insufficient_variation, constant_training_column | input_validation |
| numpy_unavailable | configuration |
| regression_fit_failed, nonfinite_regression_result | regression |
| undefined_kernel_bandwidth, constant_evaluation_residual, nonfinite_hsic_result | dependence |

Every method error has status=error, a category/reason, no scores/margin/direction,
and provenance from the real original request. Its threshold may be retained.
Missing/corrupt storage, duplicate execution, invalid transport/config, or write
failures raise to the caller; the runner must log them as operational failures.

The reproducibility record contains selected-row split indices, actual training
means/scales, residual transforms and HSIC bandwidths per direction, all config
values, and actual Python/NumPy versions. A partial preprocessing record on a
failed method is intentional; do not invent steps that did not execute.

## Exact handoff to Kris and Vaishak

```python
from causalbridge.verifier.bindings import ANMRequestBinding
from causalbridge.discovery.schemas import canonical_digest

# Or read request.json directly with ANMRequestBinding.model_validate_json(...).
artifacts = load_anm_artifacts(folder)
method_request = artifacts.request  # independently saved original, not from result!
method_result = artifacts.result
method_result_digest = canonical_digest(method_result.model_dump(mode="json"))
```

Attach method_result to E4. Save the original request, original result digest,
evidence/package/display/mapping identities before prediction. On successful
S1 persistence, attach its proposal_digest and construct VerificationContext.
Its `method_request` is this saved original. When deriving S2, retrieve the
original receipt; do not rebuild expected identities from candidate outputs.
The checker makes no extra numerical/model calls. The synthetic example performs
this full handshake and writes its evidence receipt, S1, context and S2 separately.

`statistics.summarize_display_rows` matches the merged NumericSummary contract:
source=display_rows, population std, exact displayed count, finite Pearson
correlation (null for a constant column). It does not summarize a larger hidden
method sample. This follows the implemented contract rather than earlier draft
plans that allowed tool-sample summaries in that field.

## Track A confirmation and remaining team work

The independent tests construct an observational joint with exact Fraction
arithmetic and use propensity reweighting for intervention references, separately
from both numerical adapters and benchmark/witness calculations. The merged
confounded witness has P(X,Y)=0.25 in all cells and effects +0.30/-0.30. Generated
small-pilot numeric labels also agree; limited-evidence runtime calls remain gated.
Arunima's historical `local_checked_awaiting_anish` export tags are preserved;
this verification is documented separately, without silently rewriting her labels.

Kris still supplies real selected samples, matched packages, prompts and durable
S1 receipts; Faizah supplies eligible data, evaluation-only source groups/labels
and development scoring. A frozen tau, shared dataset mapping, real-data pilot
and live model run remain team integration/evaluation work, not claimed results.


## Saved baseline verification and production replay — 2026-11-17

`discovery/replay.py` prepares baseline reproduction without changing ANM settings.
It recursively finds saved attempts, including interrupted attempts without a
result, and validates their original request, sample, configuration, split,
execution marker, result and reproducibility bindings. A standalone experiment
`benchmark/config.json` is not mistaken for an ANM attempt.

Check existing artifacts without fitting regression:

```bash
uv run --extra anm python -m causalbridge.discovery.replay \
  --attempt-root /path/to/original-attempts \
  --output runs/baseline-artifact-check \
  --expected-count 192
```

Use `192` only for the complete original validation run described by the external
report. For a different run, supply its independently known count. Without a count,
the report explicitly leaves count checking unset. Count agreement alone does not
verify the exact dataset/orientation/split schedule or frozen benchmark identities.

To repeat the producer locally, use a second fresh output directory and add
`--recompute`. All original attempts must validate and the requested count must
match before any new fit starts. The tool saves the exact original inputs/configs
under the new output, verifies request equality, and computes using the existing
producer. Scores/margin use tolerance `1e-10 + 1e-7 * abs(original)`; decisions,
thresholds and typed failure outcomes must match exactly. Original producer files
are hashed before and after. Existing outputs and output paths inside originals
are rejected, including symlink aliases. Inspect `report.json` and its `passed`
field; the CLI exits nonzero for failed checks. Matching a typed method error is
reported as an error result, not successful causal recovery.

This is **production replay**, not a new independent reference. It does not compute
causal accuracy, split stability, the scientific progression gate, or new parameter
choices. It performs no LLM calls and needs no GPU. The current producer source
hashes and Python/NumPy versions are saved for later comparison; they do not attest
to the unavailable frozen source used by the original study.

Local evidence is recorded in [verification.md](verification.md). The three
external validation reports are available outside this repository, but their
`benchmark/validation` source and `runs/anm-validation-01` bundle are absent from
all fetched branches and this workspace. Obtain that exact bundle and its frozen
source before claiming reproduction of the 48-dataset statistical results. Do not
replace it with fresh synthetic cases or the 17-pair scripted integration run.
