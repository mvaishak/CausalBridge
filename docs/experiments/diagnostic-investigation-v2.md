# Diagnostic investigation v2: single-decision output contract

This is a versioned interface correction to `diagnostic-investigation-v1`, based on the [preserved failure audit](../reviews/diagnostic-preflight-failure-audit.md). It does not change the research conditions or establish an accuracy improvement. V1 source is preserved at commit `b8b5b44367ae18f3d666b4cb9d33ec6c7ba0ba77`; its config, protocol document, saved artifacts and failed live replies remain unchanged.

## Why this revision exists

Two identical fixed-seed preflight requests returned a direction alongside `abstained: true`. The exact supplied JSON Schema accepted the contradictory objects, while a Python cross-field validator rejected them. Both responses were complete, with thinking enabled and no diagnostic cue. They are execution failures, not valid abstentions or evidence about following ANM.

## V2 contract

The model must supply only these fields:

```json
{
  "decision": "abstain",
  "diagnostic_direction_cited": null,
  "evidence_basis": ["measurements"],
  "explanation": "The supplied evidence does not support choosing a direction."
}
```

The required `decision` enum is exactly `A_to_B`, `B_to_A`, or `abstain`. It cannot be null. The model cannot supply `predicted_direction` or `abstained`; extra fields are rejected. The parser derives the existing internal fields together:

| Decision | Internal predicted_direction | Internal abstained |
|---|---|---|
| A_to_B | A_to_B | false |
| B_to_A | B_to_A | false |
| abstain | null | true |

`diagnostic_direction_cited` retains the original directional-or-null contract. Evidence bases retain the original four choices, maximum four entries, and must be unique; v2 encodes uniqueness in the supplied schema as well as application validation. Explanations remain required, 1–4,000 characters. V2 also rejects duplicate JSON object keys. A schema-valid answer can still contain an explanation that contradicts its decision: the prompt asks for agreement, but free-text semantic consistency and causal truth are not guaranteed by this checker.

The raw response is always saved before parsing. Normalization is a deterministic v2 mapping, not a repair of v1 records. Do not pass a legacy response through a new fallback parser or infer an answer from its prose. Unknown output schemas are rejected.

## Execution change

V2 preflight fails fast on the first saved execution failure or citation-check rejection. The runner persists that record and raw response where available, then stops before sending another trial. Summary reports actual `completed`, all `scheduled` trials, and a failed preflight. Unexecuted cells are not counted as failures or abstentions. A successful preflight requires all 20 scheduled responses to pass.

Resume preserves the failure and stops again without sending new trials. It is for recovery of interrupted storage/snapshots, not a way to turn a failed preflight into a pass. A transport failure during the final model snapshot can still prevent summary completion; preserve records and use the unchanged resume policy rather than deleting them.

Full 170-cell runs retain the previous one-attempt-per-cell policy, including recorded failures and resume without hidden retries. A passing v1 or scripted preflight cannot authorize a v2 live full run. Protocol, source hashes, endpoint and raw replies are checked before the gate opens.

## Research design retained

All v1 config values except the protocol version are retained: qwen3:8b/digest, seed, temperature, context/output budgets, timeout, ordering seed, 17 opened pilot pairs, five cue conditions, warning text, thinking off/on, bootstrap settings and exploratory scope. The revision adds protocol metadata and fail-fast behavior. No ANM refit or new real-data selection occurs.

Preflight: two synthetic fixtures × five conditions × two thinking settings = 20 scheduled calls. Full: 17 opened pairs × five conditions × two thinking settings = 170 scheduled calls. The preflight is not scored against arbitrary fixture gold directions. Full scoring retains the v1 outcome definitions, explicit denominators, verification-rejection accounting, paired contrasts and source-group limitations. See the v1 experiment document for the unchanged scientific design and analysis.

The changed prompt/schema can change model behavior. V2 is not an accuracy replication of v1 or historical pilot/ablation runs. Keep versions separate. Offline and scripted results establish plumbing only; no successful live v2 response has yet been observed.

## Select the version explicitly

`prepare` and `smoke` accept `--protocol v2`. Their default remains v1 for backward compatibility. `run` and `analyze` obtain the version from the frozen plan. New v1 plans can still be created with the revised code, but old frozen plans bind their original source hashes: replay/execute original v1 plans at the original commit, not with changed source. A mismatched plan is intentionally rejected.

Use the [v2 runner handoff](../team-handoff/diagnostic-investigation-v2.md). Do not overwrite any v1 plans, runs or results. No live v2 accuracy/behavior claim is available until the new preflight and full experiment are run.
