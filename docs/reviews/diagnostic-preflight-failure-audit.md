# Diagnostic-cue v1: preserved live preflight failure audit

Baseline: `b8b5b44367ae18f3d666b4cb9d33ec6c7ba0ba77`, branch `codex/anm-evidence-investigation-20261121`. This inspection used the two user-supplied archives from Downloads. No model calls, prompt/schema edits, experimental reruns or historical outcome repairs were performed.

## Integrity and replay

| Archive | SHA-256 | Regular files excluding Apple metadata |
|---|---|---:|
| `cue-investigation-preflight-schema-failed-04.tar.gz` | `7652551b26b2728c522b9b27aed1556823907e2a5f2288c450f9a2473d5b637c` | 473 |
| `cue-investigation-repeat-schema-failed-05.tar.gz` | `1462f1ef5560479164239ca693096153a9c7c7905c838a869719375bcf6f1565` | 416 |

Downloads and workspace copies have identical archive hashes. All six included SHA256SUMS inventories passed (five in the first archive, one in the second). Inventories overlap and should not be counted as independent observations. Archive paths, duplicate names and links were checked before reading regular members; originals were not modified. Checksums establish internal consistency, not independent authentication.

Both saved live raw-response digests and request digests match their records. Replaying the frozen `diagnostic_runtime.decode` on each raw response reproduced the saved failure string exactly. Independent Draft 2020-12 JSON Schema validation accepts both response objects against the exact schema in their respective saved requests. The archived schema equals the local baseline-generated schema. Per-archive and per-response evidence is in `artifacts/diagnostic-preflight-failure-audit/validation.json`.

## What actually happened

The two schema failures are runs 04 and 05, with one saved response each. Both use the same first trial `sha256:3ee69948c853b44f18800586e2061dbfedf4c9c3a5d06e3f0e44f0641dbd26dc` and request digest `sha256:b26b6e779ffafb2ed352523f063771e8cd493351d312b81b7b2b12fd46fa6f1e`.

This trial has **thinking enabled, no external diagnostic, anonymous A/B labels, and three synthetic display rows**. It is a software preflight fixture, not a real benchmark case. Requests pin qwen3:8b, seed 261, temperature zero, context budget 8192 and output budget 4096. Saved model snapshots report the intended model digest. Both responses have HTTP 200, matching model name, `done: true`, `done_reason: stop`, nonempty reported thinking, and evaluation count 400. The recorded evidence does not support attributing these two failures to truncation, transport failure, missing thinking, or an ANM directional cue.

The model's final output contains:

```json
{
  "predicted_direction": "B_to_A",
  "abstained": true,
  "diagnostic_direction_cited": null,
  "evidence_basis": ["variable_names", "measurements"],
  "explanation": "No external diagnostic provided. While measurements show B increases with A, correlation does not imply causation. Abstaining due to lack of experimental cues or causal mechanisms."
}
```

The final explanation explicitly says it is abstaining. The structured direction contradicts that statement and the abstention flag. The reported thinking also discusses abstention, but it is generated text, not independently verified access to an internal mechanism. Do not infer or repair a valid answer from it.

The request payload, final content, and reported thinking are identical across the two replies. Complete raw response bytes differ. This reproduces a problem under the same fixed-seed cell; it is not evidence that all conditions fail or two independent experimental replications.

## Verified interface cause and limits

The JSON Schema supplies independent constraints: direction may be A_to_B, B_to_A or null; abstained may be true or false. It contains no cross-field rule binding the two. The system prompt permits abstention but never explicitly describes the required relationship. Python's `CuePrediction.consistent` enforces `abstained == (predicted_direction is None)` after generation, so a response permitted by the supplied schema fails application validation.

This is a verified **generation-contract versus application-contract mismatch**. The application is correct to reject a contradictory response. We have not established why the model selected the particular conflicting token, whether explicit wording alone would solve it, or how the backend implements the supplied grammar. None of these artifacts establishes that ANM evidence was followed: there is no diagnostic cue in this trial.

The earlier live runs 01 and 02 each contain 20 saved transport-failure records (19 ReadError, one RemoteProtocolError) and no raw responses. These are separate infrastructure failures. Run 03 has no saved raw reply/record in the archive; do not infer that remote computation never started. Runs 04/05 were interrupted after the first saved schema failure, with the next request reportedly already in flight and no durable result for it. Neither 20-call live preflight completed successfully. The 170-call live experiment is absent; the archived 170-cell scripted smoke is software plumbing, not research results.

## Recommended correction

Create a separately versioned v2 contract with one model-generated decision enum: A_to_B, B_to_A, abstain. Derive normalized internal `predicted_direction` and `abstained` together from that enum. Explain all three choices explicitly. This removes the redundant generated state; it does not guarantee that free-text explanations, evidence attribution or causal answers will be correct.

Add regression cases for all decisions, unknown/missing decisions, extra contradictory legacy fields, malformed/truncated JSON, thinking activation and citation checks. Verify the generated schema and parser accept exactly the intended model-facing states. Preserve all v1 records as execution failures. Do not treat them as valid abstentions based on the prose. Test both thinking settings and retain the original five cue conditions.

Run offline tests and scripted end-to-end smoke, freeze fresh v2 requests and plans, then ask the model runner for a fresh 20-call live preflight. Only a passing preflight can authorize the existing 170-cell exploratory design. Consider explicit fail-fast behavior for preflight so a known failure does not launch further calls; document that execution-policy change. Do not retry indefinitely or tune prompts against the real cohort to manufacture a passing result.

These two archives are sufficient to prepare this interface correction locally. No further records from Vaishak are required to address this verified gap. Live validation still requires model infrastructure. No correction, commit or publication was performed as part of this inspection.
