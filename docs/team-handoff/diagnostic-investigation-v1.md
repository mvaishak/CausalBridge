# Diagnostic investigation: runner and analysis handoff

Branch: `codex/anm-evidence-investigation-20261121`.
Protocol: [diagnostic-investigation-v1](../experiments/diagnostic-investigation-v1.md).
This handoff does **not** request ANM refits, prompt tuning, new data acquisition or
changes to the final submitted report. Original experimental artifacts stay frozen.

## 1. Checkout and offline verification

After the branch has been published, use a clean checkout. Record the exact commit.
Use Python 3.12 and uv, matching the existing project environment.

```sh
git fetch origin
git switch --track origin/codex/anm-evidence-investigation-20261121
git rev-parse HEAD
uv sync --frozen --dev --extra anm
uv run python -m pytest tests/test_diagnostic_investigation.py -q
uv run python scripts/diagnostic_investigation.py diagnose --output runs/cue-diagnosis-01
uv run python scripts/diagnostic_investigation.py smoke --output runs/cue-smoke-01
```

All outputs require new directories. Diagnosis reads the committed pilot and thinking
archives without extracting them. The smoke is **scripted plumbing, not research**.
It covers 20 preflight and 170 full cells with no model calls.

## 2. Freeze plans and run the live synthetic preflight

The JSON config pins the model and budgets. Set up the usual Ollama SSH tunnel;
substitute the actual endpoint if different. No API key is required for local Ollama.
Do not substitute a different model, digest, protocol or budget to get a run through.

```sh
uv run python scripts/diagnostic_investigation.py prepare --phase preflight --output runs/cue-preflight-plan-01
uv run python scripts/diagnostic_investigation.py prepare --phase full --output runs/cue-full-plan-01
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-preflight-plan-01 --output runs/cue-preflight-live-01 --base-url http://127.0.0.1:11435
```

Expect 20 real calls. Proceed only if `summary.json` says `preflight_passed: true`.
This requires schema validity, thinking activation and citation consistency, not
correct answers to the arbitrary synthetic fixture labels. If it fails, preserve
all artifacts and report the error; do not edit the prompt and continue v1.

## 3. Run the frozen exploratory experiment

```sh
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-full-plan-01 --output runs/cue-full-live-01 --base-url http://127.0.0.1:11435 --preflight-run runs/cue-preflight-live-01
```

Expect **170 calls**, not 400: 17 already-opened pairs × five controlled cue conditions
× thinking off/on. The new diagnostic messages are explicitly experimental cues,
not fabricated ANM receipts. No gold metadata is posted to the model.

A saved failure is retained, not retried. If the process is interrupted, restart
with exactly the same command and add `--resume`. Completed responses and failures
are checked and skipped; durable raw responses are recovered; only unsaved cells
are called. Do not delete failed records, change ordering, or count resumed runs as
independent replications. Keep the same endpoint and record the interruption.

## 4. Replay and interpret without further model calls

```sh
uv run python scripts/diagnostic_investigation.py analyze --plan runs/cue-full-plan-01 --run runs/cue-full-live-01 --output runs/cue-analysis-01
```

Outputs: `case-results.json`, `metrics.json`, `report.md`. Raw replay must pass before
interpreting results. The report has all ten cells and paired comparisons. JSON
also contains matched thinking effects and harmful-switch denominators.

Read the report and inspect paired cases to answer:

- Did wrong cues increase wrong-answer yield relative to no cue?
- Did changing only the diagnostic direction change predictions?
- Did warnings help through correct resistance, abstention, or execution failure?
- Did warnings also lose correct answers under correct cues?
- Did thinking change these effects? Do not use historical budget differences as
  evidence of a thinking effect.
- How many outputs explicitly attributed the diagnostic? A passed attribution
  check does not verify measurement claims, explanations or causal correctness.

Interpret intervals with seven source groups, opened outcomes, one seed/model,
fallible reference labels and multiple exploratory comparisons. Zero differences
or results contrary to our hypothesis are valid results. Do not claim held-out
confirmation, calibrated confidence or a discovered internal cognitive mechanism.

## 5. Return and preserve results

Return the complete preflight/full plans, live run directories, analysis directory,
command log, exact code commit and any interruption notes. `runs/` is ignored by
Git. Do not assume pushing source code publishes the results. Preserve originals
and package a new archive with a SHA-256 manifest in a separately reviewed results
change. Do not overwrite existing pilot/ablation artifacts or alter the final report
without the team's review. Human reasoning annotation can use the saved diagnosis's
`manual-review.csv`; fill it honestly rather than fabricating completed reviews.

Example packaging (run once; use a new destination):

```sh
tar -czf cue-investigation-live-01.tar.gz runs/cue-preflight-plan-01 runs/cue-full-plan-01 runs/cue-preflight-live-01 runs/cue-full-live-01 runs/cue-analysis-01
shasum -a 256 cue-investigation-live-01.tar.gz
```

## Prompt for Vaishak's agent

> Work on `codex/anm-evidence-investigation-20261121`. Read
> `docs/experiments/diagnostic-investigation-v1.md` and this handoff first. Record
> the exact checked-out commit. Run the offline tests and smoke, prepare the frozen
> preflight/full plans, then run the 20-call live synthetic preflight against our
> pinned Qwen3:8b endpoint. If the preflight passes, run the 170-call full experiment
> with both thinking settings. Do not change prompts, schema, budgets, conditions,
> reference labels or exclusions, and do not refit ANM. Preserve every raw response
> and failure. Use `--resume` for interruption; never silently retry a failed cell.
> Stop and report model/digest, schema, attribution or protocol problems rather
> than editing v1 to make it pass. Then run the offline analyzer, inspect paired
> cases and produce a concise interpretation with exact counts, denominators,
> source-group intervals, abstentions, failures and checker rejections. Evaluate
> whether wrong cues cause harmful switches and whether warnings/thinking reduce
> them at a coverage cost. Treat this as exploratory controlled-cue evidence on
> opened cases, not an ANM improvement or held-out accuracy result. Return the
> complete plans, raw run, analysis, commit identity and interruption notes in a
> new hash-manifested archive for team review. Do not modify frozen experiments,
> merge branches or rewrite the final report automatically.

## Group-chat draft

Vaishak, I've prepared the diagnostic-following investigation on
`codex/anm-evidence-investigation-20261121`. It includes the saved-result diagnosis,
frozen conditions, runner, offline scoring and interpretation report. Could you run
it with the LLM? It's 20 preflight calls, then 170 full calls across the 17 opened
pilot pairs, five cue conditions and thinking off/on. The aim is to test whether
wrong diagnostic cues change answers and whether warnings help—not to claim an
accuracy improvement. Please give your agent the prompt in
`docs/team-handoff/diagnostic-investigation-v1.md`; it has all commands and return
instructions. After the run, it can replay the results and draft the interpretation
without more model calls. This message is ready to send **after branch publication**.
