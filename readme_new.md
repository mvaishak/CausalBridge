# CausalBridge: status and next steps

This note is the working record for the `faizah` branch. It says what the
repository already does, what the 17-pair pilot found, and what to do next.
It does not replace `README.md` or `docs/pilot_run.md`. Those remain the
setup guide and the reproduction commands.

Branch base: `codex/pilot-readiness` at `a8ba5ba` (open pull request #10).
That pull request is not on `main`. `main` is still `1dd84b4`, through pull
request #8.

## What the project is testing

CausalBridge has two separate tasks.

Track A asks whether a known graph and exact probabilities support a causal
effect. A directed path from X to Y does not decide the sign. The checked
witness uses Z → X, Z → Y, X → Y. Both models have P(X, Y) = 0.25 in every
cell. The intervention effects are +0.30 and −0.30.

Track B asks which direction is more plausible, A → B or B → A, and allows
abstention. Four matched evidence packages isolate one change at a time:

| Package | What the model sees | Comparison |
| --- | --- | --- |
| E1 | Sanitized names and units, no rows | World knowledge |
| E2 | Anonymous A/B rows and a summary | Numbers without names |
| E3 | The E2 rows plus sanitized names | E3 − E2 is the effect of names |
| E4 | The E3 package plus one cached ANM card | E4 − E3 is the effect of the diagnostic |

S0 is the base prompt. S1 adds a caution paragraph and sees the same evidence.
S2 is a deterministic checker over the saved S1 answer. S2 does not call the
model again. ANM-only and a simple evidence gate are baselines.

The research claim stays testable: can the model make a more reliable
directional judgment from the evidence, and can the checker stop unsupported
claims from being released? Those are different questions. A process pass is
not a correct arrow.

## What is already built

| Piece | Where it stands |
| --- | --- |
| Track A graph checks, backdoor sets, intervention engine, +0.30/−0.30 witness | On `main`. 50 synthetic questions over 10 graph groups are in `data/pilot/track_a_10_groups.jsonl`. No completed live Track A run is stored. |
| ANM diagnostic | On `main`. Kernel ridge regression and HSIC in both directions. The request is saved before the fit. The pilot threshold 0.001 was not calibrated. |
| E1–E4 packages, S0/S1 predictor, S2 checker, durable runner, audit | On `main`. Gold labels never enter the prompt. |
| Tübingen loader and weighted scorer | On this branch, from pull request #10. `discovery/loader.py` checks 218 file hashes. `evaluation/scoring.py` joins labels only after the run. |
| Case-level diagnosis | Added on this branch in `evaluation/diagnosis.py`. It reads the saved run. |

The loader accounts for all 108 metadata rows: 17 included pairs, 12 unused
pairs inside those same families, and 79 reserved pairs that have not had an
eligibility audit. Included families are DWD stations (6), Auto MPG (4 of 5),
Arrhythmia (3), GAG urine (1), UNdata (1 of 12), Kamernet rent (1), and bone
measurements (1). The unused UNdata and Auto MPG pairs stay in the pilot
family. They cannot be moved into a later held-out set.

Names were reviewed before any model output. Units were left blank unless they
were independently known. Pair 23's description repeats height units for
weight, so no unit was guessed. Pair 56 keeps the benchmark's reversed
reference. That reference is not proof that latitude causes life expectancy.

## What the pilot already showed

The live run is `runs/real-pilot-01/` (14 November 2026). Those traces are
local and gitignored. The committed record is `docs/pilot_run.md`.

- 17 pairs, 7 source groups.
- 136 live generations and 68 cached S2 checks.
- About 26 minutes. Resume made zero additional model calls.
- Zero execution failures, zero ANM errors, audit passed.
- Model: pinned Qwen3 8B, temperature 0, seed 261, context 4096, 512 output tokens, 16 displayed rows, up to 128 method rows.

On E4, S0, S1, S2, and ANM-only returned the same arrows.

| | Count |
| --- | ---: |
| Answers | 14 |
| Correct | 6 |
| Wrong | 8 |
| Abstentions | 3 |

Weighted coverage is 89.0%. Weighted selective accuracy is 40.0%. Unweighted,
14/17 is 82.4% coverage and 6/14 is 42.9% accuracy. The difference is the
official pair weight. The paper has to show both, with the total weight beside
them. Selective accuracy is correct weight divided by released weight. It is
undefined when nothing is released.

Two findings are already solid enough to keep:

- On E4 the model copied ANM. The checker did not change any E4 release, so it
  did not improve directional accuracy there.
- Outside E4 the checker rejected five outputs for unavailable or incorrectly
  copied evidence. That count is not yet split into wrong answers removed and
  correct answers removed.

Some structured arrows contradicted the model's written explanation. The
analysis export stores reason codes, not the raw prose. That check is still a
read of the saved generations.

These numbers are exploratory. Seven dependent source groups are not a
confidence interval. The threshold 0.001 is the pilot setting, not a tuned one.
Do not describe 40% as a property of causal language models in general.

## Next steps, in order

Do not start a larger run until steps 1–4 are finished. Another 136 calls would
repeat a result that is not yet diagnosed.

### 1. Produce the case table from the cache

On a machine that has `runs/real-pilot-01/` and `runs/pilot-preparation/`:

```bash
uv sync --frozen --dev --extra anm
uv run --extra anm python -m causalbridge.evaluation.diagnosis \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --anm-root runs/real-pilot-01/anm \
  --output runs/real-pilot-01/diagnosis.json
```

`diagnosis.json` contains one row per pair, every package and condition,
weighted and unweighted rates, H1/H2/H3 differences, checker removals by
package, ANM agreement counts, per-group counts, and an ANM coverage curve at
thresholds 0, 0.001, 0.01, and 0.1. The curve recomputes arrows from saved
margins. It does not change the pilot threshold. If `anm/` is omitted, the
curve is marked `margins_unavailable` instead of inventing scores.

Confirm the E4 S1 block still prints coverage 0.890 and selective accuracy
0.400, and that the unweighted rates are about 0.824 and 0.429. Then list each
pair's weight next to correct, wrong, or abstention so a reader can see where
the 89% comes from.

### 2. Read the five rejections and the copied arrows

From the `checker` section, mark each rejection as a correct answer removed or
a wrong answer removed, and keep the reason code. A useful checker can matter
even when directional accuracy does not move, but only if the removed answers
and the coverage change are both reported.

From `anm_agreement`, confirm E4 is entirely `agree_answer` or `agree_abstain`.
Then read E1–E3. The useful split is: the model matched ANM, contradicted ANM,
or abstained. H1 is E3 minus E2. H2 is E4 minus E3, next to ANM-only. H3 is
E4 S2 minus E4 S1. On the reported pilot, H3 on E4 is zero.

### 3. Separate confident ANM mistakes from borderline ones

Use `threshold_curve` and each pair's `margin`. The eight wrong E4 answers need
a margin, not only a label. A large margin and a margin just above 0.001 are
different failures. Leave 0.001 as the labeled baseline. Choosing a new
threshold on these 17 pairs would be tuning on the same sample used to report
the result. A later threshold belongs on development groups that are not in
this pilot, and Anish owns that choice. Scoring the frozen threshold stays here.

### 4. Inspect prose against the structured arrow

Open the saved generations under `runs/real-pilot-01/experiment/`. Count, by
package and condition, how often the written reason names the opposite
direction from `predicted_direction`, or cites a row the package did not
contain. Do not launch a new model run to study this. Record the count. Do not
treat a fluent explanation as evidence the arrow was checked.

### 5. Report groups, not 136 calls

Six pairs are DWD stations and four are Auto MPG. `source_groups` in the
diagnosis file is the start of that table. Paired differences stay inside a
source family. Do not add a bootstrap interval yet. The scorer's scope is
`exploratory_pilot_no_confidence_intervals`. The roadmap's 2,000
source-group resamples wait until the protocol is frozen. Resample families,
not pairs and not packages, and use the same draw for every condition.

### 6. Freeze, then run the held-out groups

The eligibility audit and the source-group split are recorded in
[docs/data_audit.md](docs/data_audit.md). Development groups are census income,
MOPEX catchments, and NL schools. The 17 pilot pairs were not changed. Unused
UNdata and Auto MPG pairs stay in the pilot family.

- Freeze eligibility, weights, prompts, model digest, sample sizes, the ANM
  threshold, checker rules, metric definitions, and the bootstrap settings
  before any held-out execution.
- Fit a later ANM threshold on the development groups only.
- Run the test groups with no retuning.
- Put correct, wrong, and no-release side by side. Keep the negative E4 result
  if it still holds: the model did not beat ANM, and the checker did not change
  those releases.

## What this branch does not claim

The diagnosis tests use a two-case fixture so weighted and unweighted rates can
differ. They are not the Tübingen result. Scripted offline runs under
`runs/pilot-offline-check/` are pipeline checks. Only `runs/real-pilot-01/` is
the live pilot.

Track A's live 50-question run is still outstanding. It is a different task and
a different command (`causalbridge run` on `data/pilot/track_a_10_groups.jsonl`
with `--backend engine`). Do not mix its labels into the Track B prompts.

## Commands that already exist

Prepare the snapshot, without sending labels to the model:

```bash
uv run --extra anm python -m causalbridge.discovery.loader \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --output runs/pilot-preparation/prepared
```

Score after inference:

```bash
uv run --extra anm python -m causalbridge.evaluation.scoring \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --output runs/real-pilot-01/pilot-scores.json
```

The full check is `bash scripts/check.sh`.
