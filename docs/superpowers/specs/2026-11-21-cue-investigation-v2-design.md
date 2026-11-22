# Cue investigation v2 design

## Intent

Retain the controlled directional-cue study while making the existing structured-output consistency rules explicit to the model. The first v1 live preflight response contained a direction and `abstained=true`; local validation correctly rejected it. V1 artifacts remain frozen at commit `b8b5b44367ae18f3d666b4cb9d33ec6c7ba0ba77`.

## Approach

Use the existing runner and analyzer with a version-selected config and system instruction. The v2 config changes only `protocol_version`. The v2 instruction appends explicit rules for abstention, diagnostic citation and unique evidence bases. All request fields, response fields, validators, checker rules, fixtures, conditions, settings, scoring, and preflight pass threshold stay the same.

This keeps v1 behavior selectable and makes the scientific protocol difference visible in frozen request payloads. A separate copied runner would duplicate failure and replay logic, while editing the v1 system instruction in place would lose the original request contract.

## Boundaries

- Create new v2 plans and offline smoke outputs in new directories.
- Never reinterpret or repair a saved response.
- Require all 20 live preflight cells to pass before any v2 full run.
- This task ends after offline verification and plan preparation. No live inference.
