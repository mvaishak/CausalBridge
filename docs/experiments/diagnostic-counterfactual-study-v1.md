# CausalBridge follow-up: Does the LLM follow a misleading diagnostic?

**Protocol:** `counterfactual-diagnostic-cue-v1` · **Frozen preparation seed:** `20261121` · **Status:** prepared / not yet live-tested.

## Motivating observation

On the saved 38-pair exploratory Track B panel, E4/S0 and E4/S1 copied the ANM direction whenever the diagnostic released one: 13 benchmark-correct, 13 benchmark-wrong, 11 model abstentions and one binding failure. E3/S0, with matched numerical evidence but no ANM card, had nine correct and five wrong answers. These were observational comparisons on already-opened reference labels; they **do not establish why** the model followed ANM or whether a prompt intervention would improve causal accuracy.

## Research question and one primary prediction

**Question:** Holding the observations, names, model, prompt instructions and case constant, how often does an LLM change its direction toward an externally supplied *counterfactual* directional cue?

**Predeclared primary contrast:** Wrong-direction yield for `reversed` minus wrong-direction yield for `no_card`, calculated over **all prepared cases**, counting abstentions and execution failures as nonreleases but reporting them separately.

**Support for cue-following:** A positive paired contrast means wrong directional cues caused more benchmark-wrong answers than having no cue in this controlled synthetic sample. The result does not establish why the original real-world ANM was wrong, nor prove that the LLM can diagnose a method's correctness.

## Freeze before inference

- 24 *new* independently generated synthetic causal mechanisms, 12 each direction, with deterministic but randomly shuffled orientation assignment.
- 256 rows per pair; **16 displayed rows** to the LLM, drawn with a frozen seed. No historical Tübingen case or reference label is reused.
- Four matched arms, each with the same numerical observations and variable labels:

| Arm | Experimental input | Purpose |
| --- | --- | --- |
| `no_card` | E3-equivalent names + numbers, no diagnostic | Within-case baseline |
| `aligned` | E4-equivalent card favoring the true generated direction | Does the model follow a right cue? |
| `reversed` | Same-strength E4-equivalent card favoring the opposite direction | Does the model follow a wrong cue? |
| `uncertain` | E4-equivalent card with absolute margin below 0.001, decision `abstain` | Does the model abstain or fall back on its own answer? |

- A and B card strengths are matched at absolute margin **0.006**, threshold **0.001**; uncertain margin is **0.0006**. **These scores are deliberately constructed, not fitted or calibrated ANM scores.** No outcome can be described as ANM performance.
- Each case receives every arm exactly once in deterministic shuffled order. Use the same pinned Ollama model digest, decoding settings and separate fresh request per arm. Do not retune the prompt, generator or score choices after examining outcomes.
- The model is explicitly informed that a card is a **hypothetical experimental cue rather than a real ANM result**. This warning is identical across arms; although it lowers ecological similarity to the historical E4 run, it prevents incorrectly presenting an invented method fit as authentic evidence.
- `public.jsonl` contains model-facing `evidence` plus scheduling metadata. **Only `evidence` is passed in the model message**; hidden `private-oracle.json` is read only for post-inference evaluation. Generated public evidence includes neither the true direction nor the arm label.

## Primary and secondary outcomes

Compute for each arm (all 24 cases): raw correct/wrong/released/abstained/failed counts, coverage, correct yield, wrong yield and answered accuracy (undefined if no release). Keep failures and abstentions separate. A **case-paired bootstrap** of the wrong-yield difference (`reversed` − `no_card`) reports an exploratory 95% interval using 2,000 case resamples; it is not a calibrated confidence probability.

Secondary, **not selection criteria**: aligned and uncertain arms compared against no-card; agreement with the assigned card; transitions from baseline abstention/correct/wrong to the counterfactual arm; sensitivity by generated mechanism type. Report whether an answer copied the card and whether it matches synthetic ground truth **as two independent axes**. Do not select a favorable subset or alternative prompt from these results.

## Reproduce in the repository

```bash
# Preparation (offline, no model calls). Output path MUST be new.
python examples/diagnostic_counterfactual_probe.py prepare \
  --output runs/diagnostic-cue-v1-prepared \
  --seed 20261121 --cases 24 --rows 256 --display 16

# The prepared public manifest is hashed and checked against the generator source.
# Run only after reviewing the generated public/private separation and model config.
python examples/diagnostic_counterfactual_probe.py run-live \
  --prepared runs/diagnostic-cue-v1-prepared \
  --model-config configs/pilot-model.json \
  --output runs/diagnostic-cue-v1-live

# Scores after the raw live run completes; no new inference.
python examples/diagnostic_counterfactual_probe.py analyze \
  --prepared runs/diagnostic-cue-v1-prepared \
  --responses runs/diagnostic-cue-v1-live/responses.jsonl \
  --output runs/diagnostic-cue-v1-live/analysis.json
```

The `run-live` script preserves each native `PredictionExecution`, including the **actual output text, request messages, usage and generated package digest**. It does not use the native E4 `NativePackage` or S2 verification because the experimental cards do **not** have independently executed ANM requests/receipts. Feeding them to those production contracts would misrepresent their provenance. This experiment measures **model behavior under conflicting cues**, not the process checker's trust of genuine cached method evidence.

## Interpretation and scientific boundary

1. A model that follows both aligned and reversed cards equally strongly is **cue-sensitive**, not selectively reliable.
2. A model that abstains more under the uncertain card may be responsive to explicit uncertainty, but abstention is not proof it identified the true causal direction.
3. A model that resists the reversed card might simply distrust all artificial cards; compare the aligned and no-card arms.
4. Inference from 24 generated cases is limited to this model, prompt, generator family and intervention. The original 17/38 real-panel observations are motivating evidence, not independent confirmation of this mechanism.
5. Any method/prompt repair belongs in a *later, new* protocol with new held-out mechanisms and new real source groups. The opened historical Tübingen labels cannot become untouched evaluation data again.

**Not completed:** live Ollama inference, independent prompt/trace provenance review, measured intervention effects, or real-data follow-up. Do not append any estimated result to the final course report until these stages are complete and the team reviews them.