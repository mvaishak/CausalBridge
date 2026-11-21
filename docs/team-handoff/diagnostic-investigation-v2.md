# Diagnostic investigation v2: runner handoff

**Publication status:** this handoff describes the local v2 correction on `codex/anm-evidence-investigation-20261121`. Use it only after the correction is committed and published. Commit `b8b5b44` contains v1 and does not contain this correction. Record the exact new commit you actually check out; do not invent a commit identifier.

Read `docs/experiments/diagnostic-investigation-v2.md` and `docs/reviews/diagnostic-preflight-failure-audit.md` first. Preserve all v1 archives. No ANM refits, scientific-condition changes, historical response repairs, report rewrites or automatic merges are requested.

## 1. Checkout and offline checks

In a clean checkout of the published feature branch:

```sh
git fetch origin
git switch codex/anm-evidence-investigation-20261121
git pull --ff-only origin codex/anm-evidence-investigation-20261121
git rev-parse HEAD
uv sync --frozen --dev --extra anm
uv run python -m pytest tests/test_diagnostic_investigation.py tests/test_diagnostic_investigation_v2.py -q
uv run python scripts/diagnostic_investigation.py smoke --protocol v2 --output runs/cue-v2-smoke-new
```

The smoke executes 20 scripted preflight cells and 170 scripted full cells, with no model calls. If directories exist, choose fresh names; never delete earlier failed runs to reuse a name.

## 2. Freeze v2 plans and run the live preflight

Set up the existing pinned Ollama endpoint/tunnel. Keep the model digest and all inference settings as configured. Do not change context/output budgets, seeds, prompts or conditions to make a run pass.

```sh
uv run python scripts/diagnostic_investigation.py prepare --protocol v2 --phase preflight --output runs/cue-v2-preflight-plan-new
uv run python scripts/diagnostic_investigation.py prepare --protocol v2 --phase full --output runs/cue-v2-full-plan-new
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-v2-preflight-plan-new --output runs/cue-v2-preflight-live-new --base-url http://127.0.0.1:11435
```

Expect at most 20 preflight calls. V2 stops after the first saved execution failure or citation rejection, before launching the next trial. Check the raw response and actual completed/scheduled counts. Do not interpret unsent cells as failures or abstentions. If preflight fails, preserve outputs and report the issue. Do not repeatedly retry until it passes. For an interruption, `--resume` retains saved failures and does not retry them.

Proceed only if all 20 trials completed and `summary.json` reports `preflight_passed: true`. V1 or scripted passes cannot serve as this gate. A server failure during the final model snapshot may leave the response records without a summary; preserve everything and report it rather than claiming a pass.

## 3. Full live run after a passing v2 preflight

```sh
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-v2-full-plan-new --output runs/cue-v2-full-live-new --base-url http://127.0.0.1:11435 --preflight-run runs/cue-v2-preflight-live-new
uv run python scripts/diagnostic_investigation.py analyze --plan runs/cue-v2-full-plan-new --run runs/cue-v2-full-live-new --output runs/cue-v2-analysis-new
```

The full run schedules 170 calls and preserves one outcome per cell, including execution failures. Unlike preflight it does not stop after an ordinary per-cell failure. Use `--resume` only to recover an interruption with the same endpoint/plan/source; saved failures are not retried. The offline analyzer replays raw replies without more inference.

Report all ten condition/thinking cells, explicit denominators, correct/wrong yields, abstentions, execution failures and separate citation-check rejections. Assess paired cue effects, harmful switches and warning/thinking trade-offs. Do not call scripted outcomes research evidence, treat cited evidence as causal truth, pool v1/v2 outcomes, or claim an internal reasoning mechanism from reported thinking text.

## 4. Return artifacts

Return complete plans, raw preflight/full run directories, analysis, exact code commit, commands, model snapshots and interruption notes. Preserve the original files and create a fresh archive with SHA-256 inventories. Runs are Git-ignored; pushing code alone does not publish results. No code/report merge is requested.

## Prompt for Vaishak's agent

> Check out the published v2 correction on `codex/anm-evidence-investigation-20261121` and record the exact commit. Do not use the original b8b5b44 as if it contained v2. Read `docs/experiments/diagnostic-investigation-v2.md` and `docs/team-handoff/diagnostic-investigation-v2.md`. Run both protocol test files and the v2 scripted smoke. Freeze fresh plans using `prepare --protocol v2`, then run the pinned model's 20-call synthetic preflight. Stop and preserve artifacts on any failure or citation rejection; do not retry failed cells or edit the protocol. Only after all 20 pass, run the 170-call experiment and replay the saved results with the analyzer. Keep all v1 failures intact and separate. Report exact counts, denominators, paired effects, uncertainty and limitations. This is exploratory cue-following research, not an ANM improvement or held-out accuracy result. Return the complete hash-manifested evidence and execution details without automatically committing, pushing, merging or rewriting the final submission.
