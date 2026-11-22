# Controlled diagnostic investigation v1

Status: software prepared; **no new live inference has been performed**. This is
an exploratory investigation of output sensitivity to external directional cues,
not an accuracy improvement or proof of the model's internal reasoning.

## Starting evidence and ownership

Anish owns protocol preparation, saved-result diagnosis and offline software checks.
Vaishak or another runner can execute preflight/full inference and complete the
saved-response analysis and interpretation with the handoff commands.

Baseline: `codex/qwen3-thinking-ablation-20261121` at
`ecd1b3054bb290830f9a9dfa0b1b6763fe2030d1`, based on main `fb81b96`.
The latest available ablation already records source-group sensitivity, empty typed
claims and an execution failure. This work reuses its immutable raw archive and
Ollama settings. It does not modify its scripts or claim that its prompts/schema
are identical to this new experiment.

Run `diagnose` to independently join 136 original and 272 ablation observations.
For each of 102 E3/E4 pairs, retain reference direction, original ANM direction,
upstream final prediction, failure, explanation and separate reasoning. The output
contains an unfilled human-review sheet. Review the eight unique wrong-ANM cases
and correct-ANM controls; code mentions of method, assumptions and conflict with a
second reviewer where possible. Output explanations are not validated accounts of
internal cognition. Manual interpretation is not a prerequisite for execution.

## Question, controls and limits

Primary question: does adding an incorrect external direction change correct,
wrong, abstaining or failed outputs, and does a limitations statement mitigate it?
The experiment separates this from diagnostic accuracy by assigning the supplied
direction using evaluator-only benchmark references.

| Arm | Diagnostic | Qualification |
|---|---|---|
| no_diagnostic | None | None |
| correct_plain | Matches benchmark | None |
| wrong_plain | Opposes benchmark | None |
| correct_qualified | Matches benchmark | Fixed limitations statement |
| wrong_qualified | Opposes benchmark | Same fixed limitations statement |

All arms use the same names, 16 displayed rows, summary, neutral prompt and output
schema for a pair. No actual ANM scores, margins, thresholds or method receipts are
invented or altered. Diagnostic fields explicitly say `experimental_directional_cue`.
The model is told these are experimental external cues, not verified ANM results.
This tests a direction-only cue, not all the rich ANM evidence of the historical E4
condition. It cannot isolate tool prestige, numeric margins, calibration or internal
reasoning; those would be separate experiments.

Correctness labels are absent from model messages. The evaluator deliberately
uses reference direction to generate controlled correct/wrong cues, but does not
send the correctness tag, experimental arm, group, weight or reference label as
metadata. A correct cue naturally contains the reference-matching arrow; that is
the planned intervention, not independent evidence of recovery from raw data.

## Cohort and call budget

The documented roster has 17 pilot, four development, 38 eligible validation and
49 unscorable pairs. Pilot and validation outcomes have been opened; no pool of 40
untouched, source-separated eligible pairs is established by this repository.
V1 therefore uses **all 17 pilot pairs in seven source groups**, including cases
where the original ANM abstained. The latter still receive controlled arrows; this
is not an ANM-only diagnostic evaluation. No result is held-out confirmation.

- One fixed new prompt; five arms; thinking off/on: **170 full calls**.
- Two fixed synthetic preflight fixtures × five arms × two settings: **20 calls**.
- Total budget: **190 calls**, one attempt per cell, no automatic retries.
- Preflight cases are software fixtures, not causal benchmark evidence, and never
  enter the 17-pair scientific denominator. Do not tune against their accuracy.
- Settings: pinned `qwen3:8b` digest from config, temperature 0, seed 261,
  context 8192, output 4096, timeout 900 seconds. Actual token counts and client
  latency are recorded without inventing a reasoning/final-token breakdown.
- Seeded shuffle of all ten cells within each pair avoids the earlier fixed
  off-first S0/on-first S1 pattern. It does not eliminate server time effects.
- At the earlier ablation's observed latency, this is approximately one to two
  hours of sequential inference; hardware/load can change it substantially.

## Freeze and execution

`configs/diagnostic-investigation-v1.json` defines the protocol. `prepare` freezes
ordered requests, a separate evaluator file, request/evaluator digests, source and
input SHA-256 hashes, revision and runtime versions. Requests are reconstructed
before execution; even rehashed changes to prompts, budgets or leaked metadata
are rejected. The runner posts only the saved payload to the endpoint.

Live full execution requires a passing live preflight on identical sources,
configuration and endpoint. It checks raw preflight replies, not only a PASS flag.
A preflight failure means stop, preserve results and diagnose execution. A material
protocol change requires v2 and newly prepared plans; do not tune on full outcomes.

Raw HTTP status/body is written before parsing. Thinking activation, truncation,
JSON/schema validity and response model are checked. Failures remain scheduled
observations. `--resume` skips completed observations, including failures, and
reuses durable raw responses after interruption without another model call.
It runs only unsaved cells; it does not silently repair or replace failed outputs.
Unexpected model identity prevents scoring. Transport errors contain no fabricated
raw reply. Keep such records and disclose any resumed execution/time separation.

## Response and verification scope

The isolated `CuePrediction` schema requires direction, abstention status, diagnostic
attribution, a self-reported evidence basis and explanation. Case and request IDs
are bound by code rather than copied by the LLM. This is intentionally different
from the old schema, where all ablation claim lists were empty.

The checker tests only that a cited diagnostic direction exists and matches the
supplied arrow, and that a declared diagnostic basis includes attribution. It
allows accurately attributed disagreement. A model may produce a direction with
no diagnostic citation; citation coverage is reported, not inferred. Explanation,
measurement claims, self-reported evidence basis and causal truth are **not**
verified. No production checker policy or original ANM contract is changed.

## Analysis and denominators

Exclusive upstream categories: correct direction, wrong direction, explicit
abstention, execution failure. Verification rejection is orthogonal and retains
underlying outcome. All yields/coverage/failure rates use all 17 scheduled pairs
per arm/thinking cell. Directional accuracy uses correct + wrong outputs only.
After-verification release counts/yields are separate. Undefined ratios are null.

Primary descriptive contrasts, separately for each thinking setting:

1. `no_diagnostic` → `wrong_plain`: increase in wrong-answer yield (primary endpoint).
2. `wrong_plain` → `correct_plain`: sensitivity to the supplied arrow.
3. `wrong_plain` → `wrong_qualified`: warning effect, retaining abstention/failure changes.
4. `correct_plain` → `correct_qualified`: cost of warning when evidence is correct.

Secondary analysis: correct yield, accuracy, diagnostic copying, explicit
attribution, harmful switches among baseline-correct cases, and matched thinking
on/off effects within each arm. Copying alone is not proof of irrational trust.
A model without enough baseline information may rationally use the only cue.

Main paired effects are **unweighted** percentage-point changes on matched pairs.
Cells additionally report benchmark-weighted yields. Do not compare the unweighted
paired intervals directly with historical weighted rates. A source-family bootstrap
resamples seven families, retaining all cases/conditions in each selected family:
10,000 draws, seed 261, indexed 2.5/97.5 percentiles. Intervals are exploratory,
unadjusted for multiple comparisons, and omit uncertainty in reference labels.
There is no powered confirmatory hypothesis test, preregistration claim, or pooled
independence assumption over the 170 repeated observations.

The offline analyzer reparses raw content and recomputes citation checks and scores.
Missing/extra records, mismatched identities or changed raw contents fail validation.
A deterministic Markdown report describes outcomes and interpretation questions;
it does not automatically assert the expected negative finding. Human interpretation
must inspect counterexamples and uncertainty rather than merely accepting a PASS.

## Reproduction and next decision

See [runner handoff](../team-handoff/diagnostic-investigation-v1.md) for exact commands
and the agent prompt. Saved-result diagnosis and scripted smoke need no data download,
GPU, Ollama, API key or LLM calls. A smoke result is always labeled scripted.

If wrong cues induce errors and warnings do not prevent them, the project has a
stronger bounded error-propagation finding. If warnings help by abstaining, report
the accuracy/coverage cost. If the model resists, report that rather than suppressing
it. Any general accuracy-improvement claim needs a revised frozen method and a
new, source-separated real evaluation cohort beyond this submission.
