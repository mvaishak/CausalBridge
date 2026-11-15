# CausalBridge Track B integration contract

The implemented Python classes are authoritative for exact behavior. The
November 8 [detailed roadmap](planning/Detailed_Implementation_Roadmap.pdf)
sets the scientific scope and ownership. The [team agreement](planning/track_b_team_interfaces.md)
records conventions; its proposed examples aren't executable replacements for
these contracts. Phase 1/2 implementation is preserved in commit `6e7232e`.

PR #4 is now merged into main at `48d6cda`. Anish's additive numerical producer
implements these existing schemas without changing them; see
[ANM producer and saved originals](anm_producer.md) for exact APIs, digest scopes,
files, errors and the computed synthetic handshake. Historical verification
counts below describe Vaishak's delivery, not the current combined suite.

This handoff adds documentation and an offline example. It preserves all public
interfaces, release decisions and statistical assumptions. Historical
[Phase 1](track_b_phase1.md) placeholder checks are superseded by
[Phase 2](track_b_phase2.md).

## Implemented interfaces

```python
from causalbridge.discovery.schemas import DirectionEvidence, DirectionPrediction, PromptCondition
from causalbridge.llm.client import JSONModel
from causalbridge.llm.predictor import PredictionExecution, predict_direction
from causalbridge.verifier.bindings import VerificationContext
from causalbridge.verifier.checks import PredictionCheck, check_prediction


def predict_direction(
    evidence: DirectionEvidence,
    prompt_condition: PromptCondition,
    model_client: JSONModel,
) -> PredictionExecution: ...


def check_prediction(
    evidence: DirectionEvidence,
    saved_prediction: DirectionPrediction,
    *,
    context: VerificationContext | None = None,
) -> PredictionCheck: ...
```

`predict_direction` makes exactly one synchronous
`model_client.generate(messages, DirectionPrediction.model_json_schema())` call.
`JSONModel.generate(messages: list[dict[str, str]], schema: dict) -> Generation`
is the existing transport protocol. Use `OllamaModel(ModelConfig(...))` for the
live transport; the offline example injects a scripted implementation.

The predictor appends shared format/evidence instructions to the runner's prompt
and asks: “Which direction is more plausible, A → B or B → A? You may abstain.”
It never chooses S0/S1, executes ANM, caches a result or joins evaluator metadata.
No retry or automatic model download occurs. Supplied model clients must honor
the JSONModel protocol; optional `.config` must be a valid ModelConfig or null.

Evidence and prompt-condition validation happen before generation. Invalid
typed inputs raise to the caller without an execution trace. For valid inputs:

| failure_stage | Trace behavior |
| --- | --- |
| null | Successful parsing and case/package binding; prediction may answer or abstain |
| generate | Transport/model exception; error retained, generation and prediction normally null |
| parse | Malformed/oversized/duplicate-key/schema-invalid output; raw Generation retained, prediction null |
| binding | Parsed prediction refers to another case/package; raw Generation and parsed prediction retained for audit |

**Never use a non-null prediction from a trace with non-null failure_stage.**
The existing parser accepts one JSON object, rejects duplicate keys and replies
over 64,000 characters, and validates against the supplied Pydantic schema.
Ollama truncation/incomplete-response errors occur inside transport, so no
Generation is returned for those failures. Don't invent raw text or token counts.

`check_prediction` revalidates saved records, checks original bindings and typed
claims, and returns an indexed finding per claim when schema validation permits.
It never calls a model/method, resolves files/URLs, reads evaluator records,
mutates S1 or emits a replacement direction. Unknown/malformed context schemas
raise ValidationError. JSON-representable malformed evidence/proposals return
fail; malformed non-JSON or nonfinite objects bypassing normal validation can
raise at the API boundary. Log caller/storage exceptions separately from
PredictionCheck reason codes.

If malformed evidence has a missing, empty or non-string case_id, its failing
check uses the diagnostic marker `<invalid_case_id>`. This marker isn't an
inferred case identity. Preserve the original candidate package/proposal digests
and runner linkage when logging it; the result remains invalid_evidence/fail
with release=false.

## Runtime schemas and digest conventions

All schemas inherit `causalbridge.schemas.Record`: extra fields forbidden,
frozen models, finite numbers. Python tuples serialize as JSON arrays.
Below, “required nullable” means the key must be supplied even when null.
Normal finite integer measurements are normalized to float by numeric fields;
booleans aren't accepted as measurements, strict counts, seeds or row indices.

### Evidence and model output

`causalbridge.discovery.schemas.DirectionEvidence`:

| Fields | Required/default | Type or accepted values |
| --- | --- | --- |
| case_id, ab_mapping_id | Required | Nonempty strings; opaque, runtime-safe IDs |
| package | Required | E1, E2, E3, E4 |
| mapping_seed | Required | Strict integer, independent of reference direction |
| schema_version | Default 0.1 | Literal 0.1 |
| task | Default causal_direction | Literal causal_direction |
| variable_labels | Default null | Two nonempty sanitized strings, ordered A/B |
| units | Default null | Two strings-or-null, ordered A/B |
| display_rows | Default null | Array of finite A/B numeric pairs |
| display_sampling_seed | Default null | Strict integer |
| summary | Default null | NumericSummary |
| method_result | Default null | ANMResult |

| Package | Enforced contents |
| --- | --- |
| E1 | Labels required; optional units; no rows/summary/display seed/method |
| E2 | Nonempty rows, summary and display seed; labels/units/method forbidden |
| E3 | Same numeric fields as E2; labels required, optional units; method forbidden |
| E4 | E3 fields plus one ANMResult, including an error/unconfigured result |

The runner must keep E2/E3/E4 observations, summaries and orientation matched.
The schema validates each package separately, not a group of conditions.
64 displayed/256 method rows are pilot defaults, not hard-coded requirements.
Two-row fixtures are transport examples, not sufficient pilot evidence.

`NumericSummary`: required `n_display` is a strict nonnegative integer matching
the displayed count; `source` defaults to literal `display_rows`. Optional fields
default null: `mean`, `std`, `minimum`, `maximum` are A/B numeric pairs;
std is nonnegative; `correlation` is a finite scalar in [-1,1]. The checker quotes
saved statistics rather than recalculating them or assuming a std convention.

`PromptCondition`: required nonempty strings `condition_id`, `version`,
`instructions`. There is no S0/S1 enum or built-in template selection.
Kris uses stable external condition IDs S0/S1 and freezes instructions/version.

`DirectionPrediction`:

| Fields | Required/default | Type or accepted values |
| --- | --- | --- |
| case_id, package_digest | Required | Nonempty string; Digest |
| predicted_direction | Required nullable | A_to_B, B_to_A, null |
| abstained | Required | Strict boolean; true exactly when direction is null |
| reason_code | Default null | Nonempty string if present; mandatory for abstention |
| claims | Default empty tuple | Discriminated union below |

| Claim schema | Required fields and literals |
| --- | --- |
| MethodDirectionClaim | type=method_direction, evidence_ref=method_result, direction=A_to_B/B_to_A/null |
| DisplayRowClaim | type=display_row, evidence_ref=display_rows, row_index=strict nonnegative integer, values=finite A/B pair |
| SummaryClaim | type=summary, evidence_ref=summary, statistic=mean/std/minimum/maximum/correlation/n_display, value=finite scalar or numeric pair |

Checker `direction-checker-0.3` uses the numeric evidence policy below for
continuous row/statistic citations. Scalar/vector shape, A/B order, row indices
and statistic names remain exact. The discrete count n_display=2 may be quoted
as numeric 2.0, but fractional count deviations are rejected. Null method direction
is valid only as a citation of configured ANM abstention. Error/unconfigured results
cannot support a method_direction claim, including a null one. The model may
choose the opposite arrow while accurately citing ANM's actual preference.

No confidence/probability/LLM-score fields or unrestricted text claims exist.
Extra fields or unknown claim types/references are schema errors. The checker
doesn't interpret reason_code prose or detect information hidden in allowed text.

### Numeric evidence tolerance: checker 0.3

For finite **continuous numeric claim values only**, compare a claimed scalar or
each element of an A/B pair against the cited saved evidence with
`math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)`:

`abs(actual - expected) <= max(1e-12 * max(abs(actual), abs(expected)), 1e-12)`.

The criterion is inclusive. Near zero, the absolute tolerance controls; at large
magnitudes, the relative tolerance controls. Negative values follow the same
rule. This is deterministic comparison slack for decimal serialization/rounding,
not measurement uncertainty, statistical significance, or causal evidence.

Tolerance is evaluated only after strict schema/citation validation and exact
binding of the proposal to its original evidence receipt. A display-row citation
must have evidence_ref=display_rows and an existing strict integer row_index;
a summary citation must have evidence_ref=summary and a supplied statistic.
Only that selected field is compared; the checker does not search other rows or
statistics for a nearby number. Missing fields/values, wrong shape, wrong A/B
order, invalid reference types, NaN and infinity are rejected. Nonfinite bypass
objects may raise ValueError at canonical JSON validation before a check record
exists; callers must record this as an invalid-input failure, never a release.
Unbound exact matches still cannot release; unbound approximate matches do not
receive tolerance. Existing fail/abstain precedence is retained.

Exact equality remains mandatory for evidence/case/mapping identifiers, package/
proposal/display/method/config/source digests, method settings, counts, seeds,
row indices, categorical values, directions, reason codes and all nonnumeric
fields. n_display is a discrete count and does not receive tolerance. Categorical
ANM direction claims are unchanged. No field is rounded, normalized or rewritten
before hashing or comparison. A passed check still cannot change the saved arrow.

This addresses smoke-v2 mean -0.18179807460923827 versus -0.1817980746092382
and row value -0.12044657480477401 versus -0.1204465748047740, differences of
about 8.3e-17 and 1.4e-17. Material numeric discrepancies remain failures.
The policy can accept a small nonzero value near zero or larger absolute offsets
at very large magnitudes; it cannot determine whether a model understood a value.
Empty-claim releases and qualified ANM disagreement remain permitted. No new
minimum-citation, directional-agreement, prompt or generation policy is added.

This is an explicit checker/release-policy revision from 0.2, not a change to
cached S1 predictions. Checker-version cache keys separate deterministic replays.
Preserve original checks; write updated replay outputs to a separate artifact
bundle and report versions alongside decisions. Do not pool release outcomes
from different checker versions without identifying the change.

### Execution, transport and check output

`causalbridge.llm.predictor.PredictionExecution`:

| Fields | Required/default | Content |
| --- | --- | --- |
| evidence, package_digest, display_sample_digest | Required; display digest nullable | Original typed evidence snapshot and identities |
| prompt_condition, prompt_digest, request_messages, output_schema | Required | External condition, exact messages and structured output schema |
| generation_config | Required nullable | ModelConfig when model client exposes it |
| latency_seconds | Required | Nonnegative total call/parse time |
| schema_version | Default 0.1 | Literal 0.1 |
| run_id | Generated UUID hex | Unique execution ID, not the case ID |
| prompt_version | Default direction-0.1 | Shared formatting-prompt version |
| generation | Default null | Generation containing raw model reply |
| prediction | Default null | Parsed DirectionPrediction, even on binding failure |
| failure_stage, error | Default null | generate/parse/binding; exception type/message |

`Generation` (`llm.client`): required `text`, `model`; optional nullable
nonnegative `input_tokens`, `output_tokens` default null; nonnegative
`latency_seconds` defaults 0. Raw text is preserved, not replaced by normalized JSON.

Live execution additionally preserves `status` (complete/truncated/incomplete;
default complete for historical records), nullable `failure_reason`, and nullable
`raw_response` containing the original HTTP response body. A response terminated
by the output limit is truncated and remains a generation failure even if its text
is valid JSON. The predictor must not parse it or create a verification context.
`GenerationFailure` carries the received Generation through durable storage and
recovery; no-response failures retain generation=null and unknown token usage.
There are no automatic retries.

The optional `integrated-track-b-v2-compact` protocol uses prompt version
`direction-0.2-compact`: identical concise output constraints in S0/S1, at most
three relevant claims and citations only to available evidence. S1 retains its
additional caution instruction. These are prompt instructions, not a new claim
count release rule. The directional schema and permitted abstention are unchanged.
The original v1 protocol and historical prompt version remain selectable.
Transport provenance (live/scripted) is recorded separately from observation
provenance (synthetic/real/unspecified); a live synthetic smoke is not a real-data
evaluation. Empty-claim releases are reported explicitly, without claiming
checked evidential support or reference correctness.


`ModelConfig` (`llm.client`) defaults: model=qwen2.5:3b,
base_url=http://127.0.0.1:11434, timeout_seconds=120 (>0), temperature=0 ([0,2]),
seed=261, max_tokens=1024 (>0), context_tokens=8192 (>=1024).
All fields can be supplied externally. Configuration/Generation have no
scientific confidence interpretation and no built-in monetary cost estimate.

`causalbridge.verifier.checks.PredictionCheck`: required `case_id`,
`package_digest`, `proposal_digest`, `status` (pass/fail/abstain), strict boolean
`release`, and nonempty tuple `reason_codes`. `checker_version` defaults to
direction-checker-0.3; `claim_findings` defaults empty. Historical saved checks
retain their original version, including direction-checker-0.2. Each `ClaimFinding`
requires `claim_index` (strict nonnegative integer), `status`
(pass/fail/abstain), and nonempty `reason_code`. Only pass may release.
Persist every finding, not just the aggregate status.

### Digests

`Digest` is `sha256:` followed by exactly 64 lowercase hexadecimal characters.
`canonical_digest(payload)` hashes UTF-8 `json.dumps(payload, sort_keys=True,
separators=(",",":"), ensure_ascii=True, allow_nan=False)`. It is a Python
canonicalization convention, not RFC 8785. Sequence order and 1 versus 1.0 matter;
hash validated `model_dump(mode="json")` payloads for consistent numeric types.

| Identity | Exact scope |
| --- | --- |
| display_sample_digest | Computed property: ab_mapping_id, mapping_seed, display_rows, display_sampling_seed; null for E1; excludes labels/package/summary |
| package_digest | Computed property: entire validated DirectionEvidence JSON, including defaults and cached method/provenance |
| proposal_digest | Computed property: entire validated DirectionPrediction JSON |
| prompt_digest | Exact outgoing message sequence |
| method_result_digest | canonical_digest of entire validated ANMResult JSON, saved before prediction |
| method sample_digest | Original method sample/orientation identity from Anish's request, compared only to ANMProvenance.sample_digest |
| config_digest | Original frozen method-configuration identity, compared only to ANMProvenance.config_digest |
| reproducibility_ref | Content digest of linked immutable method reproducibility record |

Computed properties aren't serialized fields in DirectionEvidence/Prediction.
Persist them beside the original records; PredictionExecution already saves its
package/display/prompt identities. The checker recomputes public record hashes.
It also revalidates undeclared fields inserted through model_copy rather than
silently dropping them.

The method sample can be larger than the display sample. **Their digests must
not be required to match.** In the smoke fixture, method sample hashing uses
`{ab_mapping_id, rows}` with four fixed rows; production sample/config byte
conventions still need Kris/Anish agreement. Hashes detect substitution against
trusted originals; they don't authenticate the originals or prove correct computation.

## Verifier release policy and reason codes

| Status | Release | Existing behavior |
| --- | --- | --- |
| fail | false | Contradictory bindings, schema-invalid or unsupported/false claims |
| abstain | false | Required original trust records missing, absent known contradictions |
| pass | true | All applicable bindings/declared evidence claims consistent; S1 answered |
| pass | false | All checks consistent; S1 already abstained |

Known contradictions dominate missing trust data. An abstaining S1 with false
claims fails. No minimum claim count is imposed; empty claims can pass after
bindings validate. A check pass establishes process consistency only.
Honest disagreement with ANM remains permitted. Method ambiguity/error or an
unconfigured threshold doesn't force LLM abstention when no false method claim
is made. A locally accurate claim with unverifiable relevant bindings gets an
abstain finding; unrelated correct claims remain independently checkable.

All 32 existing codes follow. Aggregate codes are deduplicated in encounter
order. Claim success codes appear in findings; they don't become new top-level
success policies.

| Code | Meaning |
| --- | --- |
| evidence_consistent | Pass with directional S1; release=true |
| prediction_abstained | Pass with abstaining S1; release=false |
| invalid_evidence | Evidence/package/ANM schema revalidation failed |
| invalid_prediction | Proposal/claim schema revalidation failed |
| claim_schema_invalid | Indexed malformed claim finding |
| case_id_mismatch | S1 or receipt case differs from evidence |
| package_digest_mismatch | S1 or receipt package differs from supplied evidence |
| proposal_digest_mismatch | Candidate proposal differs from the cached S1 receipt |
| ab_mapping_mismatch | Receipt mapping/seed or original method mapping differs |
| display_sample_mismatch | Display identity differs from original receipt |
| verification_context_missing | No independent original verification receipt |
| method_result_binding_missing | E4 receipt lacks original cached result digest |
| method_result_mismatch | Cached ANMResult differs from original digest |
| method_request_missing | E4 lacks independently saved original method request |
| method_case_mismatch | Original method request belongs to another case |
| method_sample_mismatch | Result sample differs from original method request |
| method_config_mismatch | Config digest/threshold/method version/config version differs |
| method_sampling_mismatch | Selected/train/evaluation counts or sampling/split seeds differ |
| method_unavailable | Method claim/context supplied where no result was shown |
| method_execution_error | A method-direction claim cites an execution error |
| method_threshold_unconfigured | A method-direction claim cites a result with no configured decision |
| method_direction_mismatch | Claimed method direction differs from saved decision |
| rows_unavailable | Row claim where no rows were displayed |
| row_unavailable | Cited index is outside displayed rows |
| row_value_mismatch | Quoted A/B row differs from saved values |
| summary_unavailable | Summary claim where no summary was shown |
| statistic_unavailable | Optional requested statistic wasn't supplied |
| summary_value_mismatch | Statistic number or scalar/vector shape differs |
| method_claim_consistent | Method citation matches saved configured decision |
| row_claim_consistent | Row citation matches original displayed values |
| summary_claim_consistent | Statistic citation matches supplied summary |
| claim_binding_unverified | Citation locally matches but relevant original bindings aren't verified |

## Kris: predictor, saved S1 and S2

1. Receive/build schema-valid E1–E4 packages using opaque case IDs and sanitized
   labels/units. Keep orientation independent of gold. Freeze matched E2/E3/E4
   rows, summary, mapping and sampling seed. Never pass evaluator rows through.
2. Receive Anish's cached method result and independently saved original request
   for E4. Validate both; preserve originals and the result digest before prediction.
3. Supply separate external PromptCondition records for S0/S1 on identical
   evidence. Each predict_direction call makes one generation. Persist complete
   executions even on failure: raw reply, parse/binding failure, model settings,
   actual usage, latency, condition/version, exact messages, schema and IDs.
4. On first successful S1 save, persist its exact prediction/evidence and attach
   proposal_digest to the original evidence receipt. Use durable storage outside
   evaluator records. The smoke uses JSON round-trips to illustrate this boundary.
5. When deriving S2, retrieve those original records; don't recompute expected
   identities from newly supplied candidate evidence or proposals. Construct
   VerificationContext from the saved receipt and original request below.
6. Call check_prediction(saved_evidence, saved_s1, context=context). Preserve
   every status/reason/finding and checker_version. Link it to S1 run_id externally.
   If S1 failed, don't check its partial proposal; save an explicit S2-not-run
   operational record. Do not relabel that as a scientific abstention.
7. Release exactly saved_s1.predicted_direction only when release=true. Never
   retry an LLM, execute ANM, regenerate S1, or read reference labels inside S2.
8. Send immutable runtime executions and S2 decisions, linked by case/package/
   proposal and S1 run_id, to Faizah's evaluator. Reference joins happen afterward.

`VerificationContext` (`verifier.bindings`) fields:

| Field | Requirement |
| --- | --- |
| case_id, package_digest, proposal_digest, ab_mapping_id, mapping_seed | Required original identities; seed is a strict integer |
| display_sample_digest | Required nullable; null for E1 |
| method_result_digest | Optional/default null; original result hash required to release E4 |
| method_request | Optional/default null ANMRequestBinding; original request required to release E4 |

For non-E4, method context must be null. If trust records are missing, preserve
that absence so the checker abstains. Never fill gaps by copying the current
result's fields. An invalid context schema raises and must be logged as a caller/
storage failure, with the original case/run IDs, rather than dropped.

The example envelope keys S0/S1/S2, model_calls, s2_source_run_id and
s2_skip_reason are **example logging fields**, not new library schemas or new
verifier reason codes. PredictionCheck has no run_id or latency field; the runner
must link it to cached S1 and measure checker wall time externally if needed.

## Anish: original request and cached ANM result

Implemented producer: `discovery.anm_requests.save_anm_request(...)` persists the
originals; `discovery.anm.execute_anm_request(folder)` fits only after loading
those files. `load_anm_request(folder).request` returns this exact binding type,
independently of any result. `load_anm_artifacts(folder)` additionally verifies
the saved result and reproducibility record. The sample digest covers normalized
`{ab_mapping_id, rows}`; config digest covers all validated ANMConfig fields/defaults.
Use a fresh artifact directory per attempt. See [producer guide](anm_producer.md).

Save `ANMRequestBinding` before running ANM, using the actual method sample,
mapping, split and frozen configuration inputs. Every field below is required;
threshold is required nullable. The class defines no standalone threshold_version.

| Original request field | Checker compares against |
| --- | --- |
| case_id | DirectionEvidence.case_id |
| ab_mapping_id | DirectionEvidence.ab_mapping_id; result mapping is also schema-bound to evidence |
| sample_digest | ANMResult.provenance.sample_digest |
| config_digest | ANMResult.provenance.config_digest |
| selected_row_count, training_row_count, evaluation_row_count | Corresponding provenance counts |
| sampling_seed, split_seed | Corresponding provenance seeds |
| method_version, configuration_version | Corresponding provenance versions |
| threshold | ANMResult.threshold, including null |

Counts are strict nonnegative integers and must partition selected rows. Seeds
are strict integers. Digests follow the Digest syntax; versions/IDs are nonempty
strings. Pass the original request as context.method_request; also provide the
original cached method_result_digest. Neither field can substitute for the other.

Persist threshold-selection/version details within the frozen config digest and
configuration_version, plus the linked reproducibility record. Don't invent a
new transport field: exact config/version bytes must be agreed with Kris.

`ANMProvenance`: all fields required: sample_digest, ab_mapping_id, selected/
training/evaluation_row_count, sampling_seed, split_seed, config_digest,
method_version, configuration_version, reproducibility_ref,
validation_findings and input_quality_warnings. Last two are string tuples and
may be empty. Successful results require nonempty train/evaluation subsets.

`ANMResult`: required status (ok/error), provenance, and a nonempty limitations
tuple of nonempty strings. Optional/default-null fields: score_ab, score_ba,
margin (finite numbers); threshold (finite nonnegative); decision
(A_to_B/B_to_A/abstain/null); predicted_direction (A_to_B/B_to_A/null);
reason_code (nonempty string if present); error_category
(input_validation/configuration/regression/dependence/null).

| ANM state | Enforced response |
| --- | --- |
| Configured directional success | Both scores and margin; decision/direction A_to_B or B_to_A; reason null; no error category |
| Configured ambiguous success | decision=abstain, predicted_direction=null, reason_code=ambiguous_margin; status=ok |
| Unconfigured success | Scores/margin present; threshold/decision/direction null; reason_code=threshold_not_configured |
| Execution error | status=error, reason and category required; scores/margin/decision/direction null; threshold may be retained |

score_ab is HSIC(A, held-out residuals of predicting B from A); score_ba is the
reverse. margin=score_ba-score_ab. The code checks reported margin with
math.isclose(rel_tol=1e-9, abs_tol=1e-12), then derives the decision from the
recomputed saved-score difference: >tau chooses A_to_B, <-tau chooses B_to_A,
and the closed interval [-tau,tau] abstains. Keep full float precision near
boundaries. Unconfigured tau produces no directional decision.

No nonnegative HSIC range is imposed because estimator choice isn't frozen.
Specific method error codes remain nonempty strings until Anish freezes them;
the four broad categories above are the actual enum. Scores/margins are
uncalibrated diagnostics under ANM assumptions, never causal probabilities/proof.

The immutable reproducibility record must preserve transforms per variable,
training-only means/scales, residual scaling, evaluation transforms, regression/
kernel/hyperparameters, HSIC estimator/bandwidth/score convention and threshold
version. Row indices/dependency versions may be linked. This verifier doesn't
resolve the reference or independently verify ANM computation/preprocessing.

## Faizah: evaluator-only joins and outcomes

Keep gold/reference directions, original pair IDs/descriptions, source groups,
weights, source-family splits and exclusions in evaluator records. Join after
runtime completion using the opaque case/mapping key. No such record is an
input to predictor, checker, original method request or ANM calculation.

Retain case/package/display identity, condition ID/version, run_id, prompt_digest,
model/prompt/checker versions, raw/parsed outputs, proposal_digest, usage/latency,
failure_stage/error, checker status/release/reasons/findings, and the original
method-result/config/sample identities. Store an explicit S1 run_id-to-S2 link
outside PredictionCheck. Derive model settings from actual trace/Generation,
not planning estimates; preserve null usage and record failure-stage denominators.

| Outcome | How to identify it |
| --- | --- |
| S0/S1 directional answer | Corresponding external condition ID, failure_stage=null, prediction.abstained=false |
| Original S1 abstention | S1 failure_stage=null, prediction.abstained=true; retain its reason |
| Cached S2 release | Checker release=true; use the exact linked S1 direction |
| S2 pass without answer | status=pass, release=false, prediction_abstained |
| Verifier rejection | status=fail; keep codes/findings and linked S1 answer/abstention |
| Missing-trust checker abstention | status=abstain, release=false; distinguish missing context/request/result-binding codes |
| Generation failure | failure_stage=generate, error; Generation can be null |
| Parsing failure | failure_stage=parse, raw Generation retained; no parsed prediction |
| Binding failure | failure_stage=binding; parsed output retained but unusable |
| S2 not run | S1 failed or caller/context validation raised; operational log, no fabricated PredictionCheck |

For fixed eligible cases and weights w_i, let R_i indicate a released direction
and C_i indicate agreement with evaluator-only reference direction:

| Metric | Definition |
| --- | --- |
| Weighted coverage | sum(w_i R_i) / sum(w_i) |
| Correct-answer yield | sum(w_i R_i C_i) / sum(w_i) |
| Wrong-answer yield | sum(w_i R_i (1-C_i)) / sum(w_i) |
| Selective accuracy | sum(w_i R_i C_i) / sum(w_i R_i), undefined if no releases |
| Process-error rate | Weighted rate under a predeclared code/claim-violation taxonomy and denominator; report schema/runtime failures separately |

Use successful non-abstaining S0/S1 as their directional releases. S2 only gates
cached S1 on identical cases and fixed denominators: correct-answer yield and
wrong-answer yield cannot increase. Report wrong answers removed, correct answers
sacrificed and coverage alongside selective accuracy. Don't count a missing-trust
abstention as an ANM ambiguity or proof of scientifically insufficient evidence.

Keep every scheduled eligible attempt in accounting; don't silently drop generation,
parsing, binding, cache or checker failures. Freeze process-error definitions and
denominators before held-out scoring. Deliberate process injections are a separate
mechanism-test set, never an estimate of naturally occurring prediction errors.
Use source-group paired bootstrap and raw weighted denominators as the roadmap
requires. Scoring, ANM-only and simple-gate baselines remain outside this code.

## Arunima: Track A compatibility

PR #1 is merged at `7a47465`; its implementations are unchanged:

- `causalbridge.benchmark.generate_dag(node_count, edge_count, max_in_degree, *, seed)`:
  reproducible NetworkX DAG with 2–8 explicit N0… nodes, exact edge count, bounded
  in-degree and preserved isolates. Invalid requests raise ValueError.
- `generate_cpts(graph, *, seed) -> tuple[CPT, ...]`: sorted node/parent order,
  complete binary assignment keys, generated probabilities in [0.1,0.9].
- `tools.graph.parents/ancestors/descendants(case, node)` and
  `valid_adjustment_sets(case, query)` augment existing has_path/valid_adjustment.
- `benchmark.observational_marginal(model, variables)` and
  `validate_witness(first, second, visible_joint, query, *, visible_cpts=(),
  tolerance=1e-9, minimum_effect_difference=1e-6, opposite_signs=True)` remain
  evaluator/development witness tools. The latter returns WitnessValidation
  (visible_joint, first_effect, second_effect) and uses tools.reference.intervention.

RuntimeCase/CPT remain v1.0: unique explicit graph_nodes (including isolates),
ordered [source,target] graph_edges, and CPT(node, parents, p_one). Binary keys
follow the explicit parent order; for parents=[X,Z], key 01 means X=0,Z=1.
Complete RuntimeCase models use visible_cpts; the team document's bare `cpts`
example is only a graph/CPT fragment, not the serialized RuntimeCase field name.

Exact artifacts: `tests/test_benchmark_generator.py::witness_models` and
`test_confounded_witness_matches_visible_xy_and_opposite_effects`,
`src/causalbridge/benchmark/witness.py`, and `benchmark/README.md`.
For Z→X, Z→Y, X→Y, both models yield all four P(X,Y) cells=0.25.
M+ gives P(Y=1|do(X=1))=0.65 versus do(X=0)=0.35, effect +0.30;
M− reverses them, effect −0.30. Anish still needs independent numerical
confirmation; rerunning the development adapter isn't that confirmation.

```bash
uv run pytest tests/test_benchmark_generator.py tests/test_reference.py -q
```

Track A ToolBackend.execute(request, case), CausalBridge.run, numeric-effect
contracts, schemas and CLI exports remain intact. Track B adds separate schemas
and verifier modules; A_to_B/B_to_A are hypothesized arrows, not Track A effect
signs positive/negative/zero. Hidden complete witnesses/reference labels never
belong in insufficient-evidence runtime prompts or tools.

## Runnable smoke example

```bash
uv run python examples/track_b_integration.py > /tmp/track-b-integration.jsonl
uv run pytest tests/test_track_b_integration.py -q
```

The script uses real implemented classes with a fixed JSONModel, reusing the
seven Phase 1 and four Phase 2 JSONL fixtures. It constructs mock original
requests from declared sample/config inputs, never result fields. Each case makes
one S0 call and one S1 call, saves complete JSON execution records, reloads the
receipt and applies S2 to cached S1. It never loads evaluator metadata or runs ANM.
JSON round-trips illustrate persistence; durable storage, scheduling and scoring
remain teammate work. All results are scripted, not scientific performance.

| Example | S2 status / release |
| --- | --- |
| E1 / E2 / E3 / E4 | pass / true |
| E4 ambiguous / unconfigured / error | pass / false for these scripted abstaining S1 replies |
| qualified_disagreement | pass / true, while citing ANM accurately |
| false_method_attribution | fail / false, method_direction_mismatch |
| missing_original_request | abstain / false, method_request_missing and claim_binding_unverified |
| saved_s1_abstention | pass / false, prediction_abstained |

The smoke tests also inject generate/parse failures and prove S2 isn't called,
raw malformed replies survive persistence, no network occurs, no cached prediction
changes, and the original request is independent of altered returned provenance.

## Validation, review and remaining integration work

Initial audit: all 241 existing tests passed; full lint/format, eight-case Track A
demo and wheel/sdist builds passed before preserving implementation. A diff
against PR #1 confirmed unchanged Track A schemas, graph/numeric/witness modules,
pipeline, parser, transport, verifier and exported schemas. No secrets or generated
build/run/cache files were staged; unrelated root proposal PDFs remain local.
Only whitespace formatting changed in the originally supplied team-interface doc.

Independent read-only adversarial review checked incorrect releases/rejections,
stale or self-derived trust records, schema errors, gold leakage, mutation, extra
calls and failure handling. It found one pre-existing failure-path bug: malformed
case IDs could crash construction of the invalid_evidence rejection. Five
regressions reproduced the issue before the minimal diagnostic-identity fix.
No additional release/provenance defects were reported.

Final `bash scripts/check.sh`: **261 tests passed**, no warnings, Ruff lint and
format passed, eight-case Track A demo passed, wheel/sdist builds succeeded.
Overall statement coverage is 92%; predictor coverage is 100%, checker 98%.
The 20 additions comprise 15 integration smoke cases and 5 review regressions.
The standalone script emitted 11 complete offline example records. Track A and
the existing predictor/schemas remain unchanged from their audited baselines.

### Committed file manifest

The original feature branch was `codex/track-b-integration`, now merged by PR #4.
`6e7232e` preserves the completed implementation and source specifications.
The follow-up commit contains the handoff/smoke example and the review fix. These
are the exact 24 distinct paths changed relative to PR #1:

```text
docs/implementation_inventory.md
docs/planning/Detailed_Implementation_Roadmap.pdf
docs/planning/HighLevelPlan.pdf
docs/planning/track_b_team_interfaces.md
docs/plans/track-b-phase1.md
docs/plans/track-b-phase2.md
docs/plans/track-b-integration.md
docs/track_b_phase1.md
docs/track_b_phase2.md
docs/track_b_integration_contract.md
examples/track_b_phase1.jsonl
examples/track_b_phase2.jsonl
examples/track_b_integration.py
src/causalbridge/discovery/__init__.py
src/causalbridge/discovery/demo.py
src/causalbridge/discovery/schemas.py
src/causalbridge/llm/predictor.py
src/causalbridge/verifier/bindings.py
src/causalbridge/verifier/checks.py
tests/conftest.py
tests/test_direction.py
tests/test_prediction_checks.py
tests/test_prediction_process_injections.py
tests/test_track_b_integration.py
```

| Outstanding integration item | Owner |
| --- | --- |
| Real matched E1–E4 packages, frozen S0/S1 prompts, durable successful-S1 cache/receipts and S2-to-S1 links | Kris |
| Producer/request storage and exact byte conventions implemented; real-data adapter hookup and development-frozen tau remain | Anish with Kris/Faizah for integration and development evaluation |
| Sanitized eligible observational pair, opaque evaluator mapping, reference/weight/source-group records and scorer | Faizah |
| Independent numerical witness confirmation complete in test_pilot_numerical_confirmation.py; final dataset/status review remains | Arunima and Anish |
| Installed model/runtime availability and exact model settings | Kris with Vaishak |

Missing components don't block offline integration. They do block a defensible
live E4 scientific run. Hashes can't detect a consistently mislabeled original
mapping, producer-supplied hidden gold text, dishonest cache receipts or incorrect
ANM computation. Existing interfaces document these trust boundaries.

Smallest next live test: one sanitized eligible pair with a fixed A/B mapping,
matched E1–E4 packages, one independently saved live ANM request/result and one
frozen model. Make 8 model calls (S0/S1 × four packages), persist every trace,
then check the 4 cached S1 outputs with zero further model/method calls. Require
all bindings to round-trip before Faizah joins labels. This tests the handshake;
it doesn't establish accuracy. Freeze the protocol before a held-out study.

## Local external-handoff acceptance utilities

`evaluation.handoff.validate_loader_handoff` validates existing RuntimePair
records alongside separate evaluator-only metadata. Evaluator field names are
a provisional local adapter target pending Faizah's acceptance, not a finalized
source-loader API. `validate_analysis_handoff` checks native-analysis-v2 against
an independently supplied schedule, retaining failure and abstention slots.
Both are opt-in; no runtime protocol or historical artifact is changed.
See [Phase 3 handoff](kris-phase3-handoff.md) for fields, fixture examples,
source-group scope, invariants and limitations. Reference orientation conversion,
label joins and statistical scoring are separate phases.

`evaluation.joins.join_evaluator_records` supplies the Phase 4 opt-in evaluator-only
join: retained original RuntimePairs, exact mapping/source identities, seeded
orientation replay and exact S1-parent joins. It returns private reference
agreement records without mutating runtime exports. The reference truth table
and trust boundaries are in [Phase 4 evaluator joins](kris-phase4-evaluator-joins.md).
Weighted metrics and bootstrap remain outside this utility.

## Scorer acceptance examples (Phase 5)

[Scoring fixtures](../tests/fixtures/track_b_scoring/README.md) provide a reduced
private-joined input projection and exact rational targets for weighted metrics,
failure accounting, S2 suppression, H1/H2/H3 paired contrasts and fixed group
resamples. These are synthetic mechanism examples, not real results or a production
scorer implementation. Missing-trust abstention, checker error and original
abstention are separate in an additional tiny fixture. Null selective accuracy
is required when no direction is released. Faizah's actual consumer acceptance
and confidence-interval freeze choices remain pending.

Phase 6's [offline acceptance demo](kris-phase6-offline-acceptance.md) exercises the
merged PR #8 native runner/export/auditor through these handoff and join utilities
and matches all 136 scorer-input projection rows. It uses scripted synthetic
responses and intentional insufficient-row ANM errors; actual scorer consumption
and real-pair acceptance remain external gates.
