# Diagnostic investigation v3 protocol amendment

Parent: Anish's v2 implementation at `4f600b4c507bda66c0923a1a1a6546347a0b28f3`. This is a separate protocol; all v1/v2 plans, raw failures, and archives remain separate and unchanged.

## Exact changes from v2

- The model-facing `evidence_basis` field changes from an array of up to four unique category strings to an object with exactly four required strict booleans: `measurements`, `variable_names`, `diagnostic`, `background_knowledge`. There are no additional fields. The schema forbids extras and requires all four booleans. Raw JSON is decoded with duplicate-key detection before Pydantic validation.
- The model-visible system prompt describes these four flags and their meaning, replacing v2's array/list wording. The scientific question, cue warning, freedom to agree or disagree, and prohibition on invented scores remain. `decision`, `diagnostic_direction_cited`, and `explanation` retain their v2 meanings and validation.
- True flags map deterministically to the existing internal evidence-basis list in this order: measurements, variable_names, diagnostic, background_knowledge. The existing citation checker then applies unchanged. No model output is deduplicated, repaired, or retried.
- A separate four-cell diagnostic probe uses independent synthetic cases. Cue absent/present and thinking off/on each occur once. It has no research denominator. It uses the same model, seed, options, schema, checker, raw-first recording, and fail-fast behavior as the formal preflight.
- V3 plan validation additionally reconstructs the seeded request order. The full-run gate independently reconstructs the expected v3 preflight requests before raw replay. V1/v2 paths remain available.
- `protocol_version`, `revises`, `output_contract`, and `revision_reason` metadata change. All other configuration fields match v2 byte-for-byte in value, including cohort, arms, thinking settings, model digest, generation budgets, seeds, timeout, bootstrap, evaluation scope, and preflight fail-fast rule.

## Gates and interpretation

Run offline tests, lint, format check, and scripted smoke first. Freeze and validate diagnostic, preflight, and full plans at the committed source. Verify model digest and GPU. Run the four diagnostic cells once. If any response fails transport/completion/schema/checker, stop and preserve the evidence. If all pass, run one fresh 20-cell preflight. All 20 must complete with zero failures and zero checker rejections; verify planned order and replay raw responses. Only then run the 170-cell exploratory experiment and analyze saved raw records offline. Use resume solely for an interruption; saved failures are never retried. A failed diagnostic or preflight is an execution finding, not a scientific result. Scripted smoke is software plumbing only.
