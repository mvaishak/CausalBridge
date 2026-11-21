# CausalBridge follow-up: Does the LLM follow a misleading diagnostic?

**Protocol:** `counterfactual-diagnostic-cue-v1` · **Frozen preparation seed:** `20261121` · **Status:** prepared / not yet live-tested. The bundled `sample_prepared/` files are the authoritative byte-locked case inputs.

## Motivating observation

On the saved 38-pair exploratory Track B panel, E4/S0 and E4/S1 copied the ANM direction whenever the diagnostic released one: 13 benchmark-correct, 13 benchmark-wrong, 11 model abstentions and one binding failure. E3/S0, with matched numerical evidence but no ANM card, had nine correct and five wrong answers. These were observational comparisons on already-opened reference labels; they **do not establish why** the model followed ANM or whether a prompt intervention would improve causal accuracy.

## Research question and one primary prediction

**Question:** Holding the observations, generic A/B labels, model, prompt instructions and case constant, how often does an LLM change its direction toward an externally supplied *counterfactual* directional cue?

**Predeclared primary contrast:** Wrong-direction yield for `reversed` minus wrong-direction yield for `no_card`, calculated over **all prepared cases**, counting abstentions and execution failures as nonreleases but reporting them separately.

**Support for cue-following:** A positive paired contrast means wrong directional cues caused more benchmark-wrong answers than having no cue in this controlled synthetic sample. The result does not establish why the original real-world ANM was wrong, nor prove that the LLM can diagnose a method's correctness.

## Freeze before inference

- 24 *new* independently generated synthetic causal mechanisms, 12 each direction, with deterministic but randomly shuffled orientation assignment.
- 256 rows per pair; **16 displayed rows** to the LLM, drawn with a frozen seed. No historical Tübingen case or reference label is reused.
- Four matched arms, each with the same numerical observations and **generic, anonymized variable labels** (`Measurement A`, `Measurement B`). This experiment does not manipulate or test the semantic variable names used in the original real-data E3 condition:

| Arm | Experimental input | Purpose |
| --- | --- | --- |
| `no_card` | Anonymized observations with generic `Measurement A/B` labels, no diagnostic | Within-case baseline (not the historical semantic-names E3 treatment) |
| `aligned` | Same anonymized observations, with an assigned cue favoring the true generated direction | Does the model follow a right cue? |
| `reversed` | Same-strength assigned cue favoring the opposite direction | Does the model follow a wrong cue? |
| `uncertain` | Assigned cue with absolute margin below 0.001, decision `abstain` | Does the model abstain or fall back on its own answer? |

- A and B card strengths are matched at absolute margin **0.006**, threshold **0.001**; uncertain margin is **0.0006**. **These scores are deliberately constructed, not fitted or calibrated ANM scores.** No outcome can be described as ANM performance.
- Each case receives every arm exactly once in deterministic shuffled order. The runner checks the **actual Ollama `/api/tags` digest** before and after inference against locked `qwen3:8b` SHA-256 `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`. It also refuses changes to temperature 0, seed 261, 4096 context tokens, 512 output tokens or `think=false`. An unverified endpoint or changed model blocks the run. Do not retune the prompt, generator or score choices after examining outcomes.
- The model is explicitly informed that a card is a **hypothetical experimental cue rather than a real ANM result**. This warning is identical across arms; although it lowers ecological similarity to the historical E4 run, it prevents incorrectly presenting an invented method fit as authentic evidence.
- `public.jsonl` contains model-facing `evidence` plus scheduling metadata. **Only `evidence` is passed in the model message**; hidden `private-oracle.json` is read only for post-inference evaluation. Generated public evidence includes neither the true direction nor the arm label.

## Primary and secondary outcomes

Compute for each arm (all 24 cases): raw correct/wrong/released/abstained/failed counts, coverage, correct yield, wrong yield and answered accuracy (undefined if no release). Keep failures and abstentions separate. A **case-paired bootstrap** of the wrong-yield difference (`reversed` − `no_card`) reports an exploratory 95% interval using 2,000 case resamples; it is not a calibrated confidence probability.

Secondary, **not selection criteria**: aligned and uncertain arms compared against no-card; agreement with the assigned card; transitions from baseline abstention/correct/wrong to the counterfactual arm; sensitivity by generated mechanism type. Report whether an answer copied the card and whether it matches synthetic ground truth **as two independent axes**. Do not select a favorable subset or alternative prompt from these results.

## Frozen sample and reproducibility controls

**Use the exact verified `sample_prepared/` directory distributed with the review bundle.** It contains 24 private oracle labels, 96 model-facing evidence records, and the original preparation protocol. The locked byte SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `sample_prepared/public.jsonl` | `a0eac1ec4cee514effd6262c2444dae9979e0f90e9e015689aa14a4744ad78be` |
| `sample_prepared/private-oracle.json` | `27b5b435ee0a8652df989c133b562705d4ffb6d2a462b2d2a45b192bbe3445c9` |
| `sample_prepared/protocol.json` | `f1cb36d12d2a0fb97a4e9626b9f3159b07f787a637d39c76c9223d1ccccb4841` |

Some Mac/Python math environments reproduce a few floats differently at about 1e-16; **do not regenerate** the original v1 prepared files on another machine and silently treat them as equivalent. The runner now validates exact source bytes plus the canonical public digest, independent of changes to the newer inference/auditing script. The stored original generation-script SHA remains historical provenance, while a fresh `runner_sha256` is recorded at execution.

`prepare` remains available for a **separate new pilot/protocol**, but its output will not pass the frozen-v1 `run-live` lock. This is intentional. New cases or generated samples require a new explicit protocol version and a new freeze, not reuse of the old study ID.

## Preflight, execution, independent audit, and scoring

Run from the repository root after installing dependencies and extracting the **frozen** sample directory. The local Ollama model must be reachable at the URL in `configs/pilot-model.json` and must expose the above exact digest. No model is downloaded automatically. Every output path must be new.

```bash
# 1. Verify that frozen sample files match the original reviewed fixture.
shasum -a 256 sample_prepared/public.jsonl sample_prepared/private-oracle.json sample_prepared/protocol.json

# 2. Opt-in live run: checks /api/tags first, writes pre-call requests,
#    raw Ollama responses, model identity and a completion receipt.
python examples/diagnostic_counterfactual_probe.py run-live \
  --prepared sample_prepared \
  --model-config configs/pilot-model.json \
  --output runs/diagnostic-cue-v1-live

# 3. Separate, read-only audit: checks full 96-trial schedule, frozen
#    evidence, independently saved request messages, raw HTTP response
#    bodies, returned predictions, digests and model identity.
python examples/diagnostic_counterfactual_probe.py audit-live \
  --prepared sample_prepared \
  --run runs/diagnostic-cue-v1-live \
  --output runs/diagnostic-cue-v1-live/independent-audit.json

# 4. Only the successful audited run may be scored with private labels.
python examples/diagnostic_counterfactual_probe.py analyze \
  --prepared sample_prepared \
  --responses runs/diagnostic-cue-v1-live/responses.jsonl \
  --audit runs/diagnostic-cue-v1-live/independent-audit.json \
  --output runs/diagnostic-cue-v1-live/analysis.json
```

A `live_ollama` value in a JSON record is only a claim. It is **not** evidence of a genuine server call. Scores cannot be produced by the command-line workflow until the raw-response audit has passed, its output hash matches `responses.jsonl`, and the 96 planned cases have all been accounted for. The audit cross-checks raw server receipts against the *separately written pre-call request journal*, but does not cryptographically attest the remote model or replace independent human inspection of provenance. Any failed/incomplete run must be kept separate and never silently repaired by inventing responses.

The same native `DirectionPrediction` schema and `predict_direction` function are reused without modifying the production 17/38-pair inference. No S2 verification is run on the hypothetical cards: they do not have genuine saved ANM requests/receipts, and passing them to production `NativePackage` would misrepresent their origins. This study measures cue susceptibility only.

## Interpretation and scientific boundary

1. A model that follows both aligned and reversed cards equally strongly is **cue-sensitive**, not selectively reliable.
2. A model that abstains more under the uncertain card may be responsive to explicit uncertainty, but abstention is not proof it identified the true causal direction.
3. A model that resists the reversed card might simply distrust all artificial cards; compare the aligned and no-card arms.
4. Inference from 24 generated cases is limited to this model, prompt, generator family and intervention. The original 17/38 real-panel observations are motivating evidence, not independent confirmation of this mechanism.
5. Any method/prompt repair belongs in a *later, new* protocol with new held-out mechanisms and new real source groups. The opened historical Tübingen labels cannot become untouched evaluation data again.

**Not completed:** live Ollama inference, independent prompt/trace provenance review, measured intervention effects, or real-data follow-up. Do not append any estimated result to the final course report until these stages are complete and the team reviews them.