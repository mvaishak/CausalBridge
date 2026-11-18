# Run the exploratory pilot

Scope: prepare and run the pilot, inspect failures and pilot scores. Do not run
held-out groups, produce a final report or claim statistical improvement.

## First live pilot completed

The first live run is saved at `runs/real-pilot-01/` (14 November 2026).
It used all 17 pairs and seven source groups: 136 live generations, 68 cached S2
checks, zero execution/ANM errors and a passing independent audit. Resume added
zero model calls. `first-run-summary.json` preserves original usage;
`pilot-summary.json` and `pilot-scores.json` contain the pilot outcomes.

E4 S0/S1/S2 and ANM-only chose identical arrows on all 17 cases: 14 answers,
six reference-correct, eight wrong, three abstentions. Weighted coverage is 89.0%
and weighted selective accuracy 40.0%. The checker rejected five outputs outside
E4 for unavailable/mismatched evidence, but added no benefit on E4. Settings and
predictions remain unchanged; these are exploratory pilot findings.

## What is ready

- Main `1dd84b4` plus local pilot-readiness changes on `codex/pilot-readiness`.
- Official Tübingen archive, pinned by 218 per-file SHA-256 hashes in
  `configs/pilot-data.json`. Download location and verified format: [source notes](api/tuebingen.md).
- 17 selected scalar pairs from seven reviewed source families: DWD weather,
  Auto MPG, Arrhythmia, GAG urine, UNdata, apartment rentals and bone measurements.
- The other 91 entries stay out of this pilot. Twelve are locked to the pilot
  families, including every unused UNdata and Auto MPG pair. Eligible remaining
  source groups are assigned to development or test in
  [the data audit](data_audit.md). Ineligible groups have a recorded reason.
- Separate runtime/evaluator files, deterministic A/B orientation and samples,
  native runner/auditor, method-only/simple-gate baselines and weighted pilot scores.
- Pilot-affecting context isolation, ANM export, Track A truncation/usage and schema
  inconsistencies fixed. Existing local Ollama thinking support is retained.

The prepared files already exist locally:

```text
runs/pilot-preparation/raw/                      frozen source files
runs/pilot-preparation/prepared/runtime/pairs.jsonl
runs/pilot-preparation/prepared/evaluator/records.json
runs/pilot-preparation/prepared/evaluator/audit.json
```

## Reproduce data preparation on another checkout

From the repository root:

```bash
uv sync --frozen --dev --extra anm
mkdir -p runs/pilot-preparation/raw
curl --fail --location https://webdav.tuebingen.mpg.de/cause-effect/pairs.zip \
  -o runs/pilot-preparation/pairs.zip
unzip -n -j runs/pilot-preparation/pairs.zip -d runs/pilot-preparation/raw
uv run --extra anm python -m causalbridge.discovery.loader \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --output runs/pilot-preparation/prepared
```

The loader fails if the official URL's contents have changed. Do not refresh hashes
to bypass that failure; audit a new snapshot as a new manifest. It also fails on
nonfinite/constant included data, unreviewed names, reversed/multicolumn metadata
misuse, missing files, or a source family split between pilot and reserved data.
It does not silently remove observations or reorder columns toward the reference
cause. Re-preparation requires a fresh output path.

## Offline check before live calls

```bash
uv run --extra anm python examples/real_data_pilot.py \
  --prepared runs/pilot-preparation/prepared \
  --output runs/pilot-offline-check --scripted
```

This uses real observations and ANM but scripted replies. Expected: 136 fixture
generations, 68 saved S2 checks, no ANM errors and a passing audit. Repeating the
same command with unchanged code/settings issues zero generations and reuses ANM.
Any scores derived from scripted replies are pipeline checks only; keep their
filenames explicitly labeled `scripted-*`, separate from live pilot results.

## Live pilot

Use the existing Qwen3 server/tunnel. `configs/pilot-model.json` selects
`qwen3:8b`, port 11435, temperature 0, seed 261, thinking off, 4096 context and
512 output tokens. It retains the compact smoke protocol with 16 displayed rows
and up to 128 method rows. No model is downloaded or server started by this command.

The pinned digest below matches the earlier synthetic smoke model. The entry point
checks `/api/tags` and fails before generation if the installed name/digest differs.
Changing model, endpoint, source files or settings requires a new output directory.

```bash
uv run --extra anm python examples/real_data_pilot.py \
  --prepared runs/pilot-preparation/prepared \
  --config configs/pilot-model.json \
  --model-digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41 \
  --output runs/real-pilot-01
```

For a fresh 17-case run, the schedule is 136 S0/S1 calls and 68 deterministic S2
checks. The default budget is 160 calls; no automatic retries are made. Resume
the same command to reuse terminal outcomes, including failures. Code changes
invalidate the session deliberately. Inspect prompt lengths, truncations, raw
generations and usage: synthetic smoke context measurements are not proof that
every real pair fits. If this pilot exposes budget problems, version the revised
settings and use a new output directory rather than overwriting it.

Inspect `pilot-run.json`, `audit.json`, `analysis.jsonl`, and the durable native
traces under `experiment/`. `pilot-run.json` reports invocation usage; the first
invocation remains preserved in `experiment/invocations/` after a cached rerun.
The code accepts 1–20 cases for small transport checks; the prepared cohort is 17.

## Score only after inference

The inference entry point never opens evaluator labels. Join them explicitly afterward:

```bash
uv run --extra anm python -m causalbridge.evaluation.scoring \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --output runs/real-pilot-01/pilot-scores.json
```

Scores report weighted coverage, correct/wrong-answer yield, selective accuracy
(null with no releases), failures and source-group counts. All 17 scheduled cases
remain in every applicable denominator. Missing/duplicate conditions, incorrect
source/mapping joins and unusable released predictions are errors, not dropped rows.
S2 and the simple gate reuse the saved S1 proposals. Review the accompanying
claim findings/reason codes and original versus suppressed releases; aggregate
accuracy alone is not evidence that checking helps.

## Diagnose the saved run

Do this before another live run. It joins the same files, adds the unweighted
rates, the E1–E4 contrasts, checker removals, source groups and a margin curve.
A saved ANM result is used only when its scores, margin, direction, mapping and
original request agree. It does not call the model or choose a new threshold.

```bash
uv run --extra anm python -m causalbridge.evaluation.diagnosis \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --anm-root runs/real-pilot-01/anm \
  --experiment-journal runs/real-pilot-01/experiment/events.jsonl \
  --output runs/real-pilot-01/diagnosis.json
```

## Frozen evaluation handoff

Before another ANM change, use [the evaluation handoff](evaluation_handoff.md).
`configs/evaluation-roster.json` separates the 4 development pairs, the 38
validation pairs, and the frozen 17. The live directory `runs/real-pilot-01/`
is not in this checkout.

## Pilot limitations and deferred work

Threshold 0.001 is an exploratory pilot setting, not a calibrated causal cutoff.
Use the pilot to inspect/calibrate it; development calibration and a final freeze
are prerequisites for future held-out claims, not for this exploratory execution.

The cohort includes spatially dependent weather observations, rounded measurements
and country aggregates. Source notes record those limitations. UNdata reference
directions are benchmark references, not proof that latitude causes life expectancy.
Names omit uncertain units; pair 23's description has inconsistent weight units,
so none are guessed. No model outputs were consulted to choose the cohort.

Checker 0.3 permits zero claims and qualified disagreement with ANM; a passing
process check is not a correctness certificate. Inspect all pilot outputs for
missing support and unsupported causal language, including free text in reason codes.

Deferred: protocol freeze and the held-out run itself; paired source-group
bootstrap intervals and inferential plots; full error-study/report/presentation;
optional robustness experiments and a new minimum-citation policy. None is needed
to execute and inspect this bounded pilot. The original preparation used scripted
replies; the subsequent first live run is recorded above.


Saved-margin diagnosis requires the independently retained original experiment
journal (`--experiment-journal`), whose hash chain is checked read-only. Each
ANM result must match the original method-result digest and the E4 package/mapping
identity in the analysis export. A valid result from a different sample is rejected.
Without those receipts, omit `--anm-root`: directional analysis remains available,
but no threshold curve is reported. Do not reconstruct receipts from replacement
results or modify historical artifacts.

Agreement summaries use only completed answers or deliberate abstentions in their
`comparable_case_count`. Failures, unavailable methods, checker suppression and
unknown outcomes have separate counts. Those exclusion counts may overlap (both
model and method can fail); `excluded_case_count` counts distinct excluded cases.

PR #14 review follow-up: pilot scoring now rejects mixed manifests and requires
exact saved S1 attempt/package/run bindings for S2 and SIMPLE_GATE. A derived
release cannot invent/reverse an arrow, release after a failed/abstaining parent,
or contradict its checker/gate outcome. Include S1 in a custom condition subset
when scoring either derived condition. Case denominators and valid metric values
are unchanged. Diagnosis reports checker execution errors separately from
completed checks that suppress answers, including separate error counts/weights.
