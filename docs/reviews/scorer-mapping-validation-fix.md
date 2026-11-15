# Pilot scorer mapping validation fix

The scorer previously compared mapping-ID strings without checking their payload.
Changing only an external column order could therefore silently reverse reference
labels and change scores, even with an unchanged valid ID and source digest.
This was reproduced on synthetic acceptance records; it does not establish that
the original real pilot was scored incorrectly.

Before joining references, score_pilot now requires:

- Exact integer columns forming the permutation (0,1) or (1,0); no bools/floats.
- A present, nonnegative exact-integer mapping seed; no bools/floats.
- The exact canonical mapping ID over case_id, order and seed.
- An order matching selection-v1's deterministic case/seed randomization.
- The existing source-digest, analysis-ID, case-set and completeness checks.

The change does not modify predictions, sampling, thresholds or metrics.
It rejects inconsistent metadata, not jointly forged original inputs and receipts.
Authentic original data and correspondence with saved runtime evidence still need
an independent artifact audit. Schemas or a matching hash cannot certify reference
truth or causal assumptions.

Thirteen added regressions cover a flipped order with unchanged ID, a coherently
rewritten order/ID that disagrees with the seed, bool/float/duplicate columns,
missing/bool/float/negative/changed seeds, wrong IDs/cases and preserved valid scores.
The actual-consumer tests from PR #11 are also exercised in an isolated combined
checkout against all 17 metric oracles and the fixed paired family resamples.

## What the independent audit is

It is a separate read-only reconstruction of the saved pilot, not a new model run:

1. Verify the original journal, hashes, manifest and declared code/model/settings.
2. Reconstruct evidence selection, A/B order and labels from retained original
   runtime/evaluator records; verify correspondence to the actual saved requests.
3. Check each S2 record references its exact S1 parent and never changes the arrow;
   retain abstentions, failed attempts and rejected answers in schedule accounting.
4. Independently recompute every package/condition's weighted numerators,
   denominators and scores, then reconcile saved summaries and call/usage counts.
5. Report discrepancies and preserve originals; never repair predictions in place.

This checks implementation/accounting fidelity, not whether ANM is statistically
reliable or an observational reference is scientifically true. It makes no new
LLM calls and requires no threshold changes. The original real-pilot bundle is
still unavailable in the accessible checkouts, so that audit remains pending.
