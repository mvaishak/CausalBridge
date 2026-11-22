# Fixed ANM adequacy-policy comparison

This is a deterministic exploratory replay on the 17 opened pilot and 38 opened later-panel pairs. It compares diagnostic annotations and withholding rules. It does not fit ANM again, generate new p-values, call an LLM, change producer code, or create a held-out evaluation. Rules were frozen after the earlier adequacy findings had been inspected, before this replay's complete tables were calculated. This is not prospective preregistration.

## Inputs and freeze

`configs/anm-adequacy-policy-comparison-v1.json` contains all rules, schemes and scope. Preparation verifies the independent decision audit's source/evidence inventory and its record digest. It joins source group and original dataset weight from the earlier saved real-noise records, checking request/result digests, reference, original direction and original outcome. All 55 primary cases must be present exactly once. It copies complete policy inputs and freezes source/evidence hashes before execution.

The original direction and the two saved nominal p-values are the only decision inputs to a rule. Reference labels are used for scoring after the policy decision; they are never used to choose which answer to retain. The audit's observed outcome remains a separate field. The original non-directional decisions remain non-directional. No rule may flip an answer to the alternative direction.

Both stored permutation schemes are reported independently: IID and saved-row-order blocks of length eight. The latter is a heuristic, not a validated temporal/spatial correction. Use the existing nominal p≤0.025 per direction, representing the prior audit's within-pair Bonferroni choice. There is no alpha, model, threshold or policy search, and no confirmatory guarantee across datasets or rules.

## Fixed rules

1. Original: unchanged historical output.
2. Warning only: unchanged historical output plus both/one/neither directional tests rejected, or unavailable. Do not call nonrejection a verified adequate model.
3. Withhold if both rejected: replace a directional answer with a policy abstention if both directional tests reject.
4. Withhold if selected rejected: withhold if the selected direction's test rejects.
5. Require unique nonrejected: keep the original direction only if its test does not reject and the opposite test rejects. Never substitute the opposite answer.

Missing diagnostics retain an unavailable status. Warning-only leaves the original answer unchanged. All three withholding rules conservatively withhold if either diagnostic is unavailable. This fallback was not exercised by these complete saved records. Existing execution failures remain execution failures, not abstentions. Invalid p-values raise an error instead of becoming evidence.

## Outcomes and denominators

These are hypothetical ANM-only decisions, before any LLM or evidence checker. They are not historical system releases or verifier rejections. All scheduled cases remain in each panel's denominator (17 or 38).

Report correct and wrong counts/yields, abstention count/rate, execution-failure count/rate, coverage and directional accuracy. Accuracy's denominator is the number of retained directional answers; coverage's denominator is all scheduled cases. Original abstentions and additional policy abstentions are separate. Paired transitions show wrong answers removed and correct answers lost. Removing a wrong answer is withholding, not correcting it.

JSON also includes original source-weighted descriptive metrics and all source-group breakdowns. Panels and schemes are not pooled. No confidence intervals or significance claims are inferred from these selected, opened and source-clustered cases. Do not select a winning rule from the tables. In particular, a high selective accuracy with very low coverage is not an increase in correct-answer yield.

## Reproduce

```sh
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_adequacy_comparison.py prepare --plan runs/adequacy-comparison-new
uv run python scripts/anm_adequacy_comparison.py run --plan runs/adequacy-comparison-new --output runs/adequacy-comparison-results-new
```

Execution checks frozen current source/evidence hashes. Outputs require fresh directories. Reproduce published tables from self-contained saved inputs without refits or permutation runs:

```sh
uv run python scripts/anm_adequacy_comparison.py replay --plan artifacts/anm-adequacy-policy-comparison-20261121 --output /tmp/adequacy-comparison-replay-new
```

Replay uses the saved protocol and input digest; it does not require current originals/source to match historical paths. The archive and source inventory provide external integrity checks. Compare `case-results.json`, `metrics.json` and `tables.md` byte-for-byte. The artifact README describes the frozen-source clean-environment replay.

During software development a preliminary table-rendering error occurred after metrics were calculated. It was corrected without changing policies, cutoffs or input data, and the successful execution used a fresh frozen plan/output directory. The preliminary run remains in ignored local runs; no partial table was substituted for a completed result.
