# Saved pilot: measured resources and baseline comparisons

Opened 17-pair, seven-source-group exploratory pilot. Original source, samples, journal/method bindings, score lineage and scores were reverified on current main. No new predictions or numerical fits. Independent human annotation is deferred.

## Measured generation resources

Unique original generations: 136. Input tokens: 128,270; output tokens: 22,896. Summed client generation latency: 1537.17 seconds (25.62 minutes). This is a sum of client request latencies, not a measured full-pipeline wall time. Original invocation and resume summaries are not added to journal receipts.

| Package | Prompt | Calls | Input tokens | Output tokens | Total seconds | Median seconds | P95 seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E1 | S0 | 17 | 8,392 | 2,625 | 173.72 | 7.33 | 17.37 |
| E1 | S1 | 17 | 9,055 | 2,358 | 144.97 | 6.96 | 16.03 |
| E2 | S0 | 17 | 14,750 | 2,245 | 142.09 | 7.29 | 16.66 |
| E2 | S1 | 17 | 15,413 | 1,935 | 133.23 | 7.58 | 10.00 |
| E3 | S0 | 17 | 14,912 | 3,248 | 211.39 | 10.15 | 18.80 |
| E3 | S1 | 17 | 15,575 | 2,477 | 157.46 | 7.35 | 19.27 |
| E4 | S0 | 17 | 24,755 | 3,988 | 285.98 | 18.31 | 21.03 |
| E4 | S1 | 17 | 25,418 | 4,020 | 288.33 | 17.91 | 22.04 |

Generation/parsing/binding failures: zero in this saved pilot. Checker/ANM wall times and local monetary cost are unmeasured, not zero. S2 and SIMPLE_GATE reuse S1 generations; ANM-only reuses the cached method result. Their additional generation count is zero. Existing parent generation/method costs still matter when comparing end-to-end systems.

## Explicit baseline comparisons

All percentages are benchmark-weighted with all 17 cases retained. Answered accuracy is undefined with no releases. Gate means SIMPLE_GATE.

| Package | Condition | Coverage | Correct yield | Wrong yield | Answered accuracy | New generations | Reused S1 generations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E1 | S0 | 28.8% | 5.5% | 23.3% | 19.0% | 17 | 0 |
| E1 | S1 | 23.3% | 6.8% | 16.4% | 29.4% | 17 | 0 |
| E1 | S2 | 0.0% | 0.0% | 0.0% | undefined | 0 | 17 |
| E1 | SIMPLE_GATE | 23.3% | 6.8% | 16.4% | 29.4% | 0 | 17 |
| E2 | S0 | 32.9% | 32.9% | 0.0% | 100.0% | 17 | 0 |
| E2 | S1 | 0.0% | 0.0% | 0.0% | undefined | 17 | 0 |
| E2 | S2 | 0.0% | 0.0% | 0.0% | undefined | 0 | 17 |
| E2 | SIMPLE_GATE | 0.0% | 0.0% | 0.0% | undefined | 0 | 17 |
| E3 | S0 | 67.1% | 39.7% | 27.4% | 59.2% | 17 | 0 |
| E3 | S1 | 24.7% | 0.0% | 24.7% | 0.0% | 17 | 0 |
| E3 | S2 | 4.1% | 0.0% | 4.1% | 0.0% | 0 | 17 |
| E3 | SIMPLE_GATE | 24.7% | 0.0% | 24.7% | 0.0% | 0 | 17 |
| E4 | S0 | 89.0% | 35.6% | 53.4% | 40.0% | 17 | 0 |
| E4 | S1 | 89.0% | 35.6% | 53.4% | 40.0% | 17 | 0 |
| E4 | S2 | 89.0% | 35.6% | 53.4% | 40.0% | 0 | 17 |
| E4 | SIMPLE_GATE | 89.0% | 35.6% | 53.4% | 40.0% | 0 | 17 |
| E4 | ANM_ONLY | 89.0% | 35.6% | 53.4% | 40.0% | 0 | 0 |

E1–E4 SIMPLE_GATE retains S1's directions on this pilot. E4 S0/S1/S2/SIMPLE_GATE/ANM-only are directionally identical: 14 answers, six correct, eight wrong, three abstentions. The checker removes one wrong and two correct E1 answers, and two wrong E3 answers. It changes no E4 direction. These are completed findings, not a reason to tune the opened cohort until a positive result appears.

## Before the midterm rerun

1. Treat a same-cohort rerun as repeatability/sensitivity, not a fresh final test. Preserve the original pilot and use a new output directory.
2. Freeze exact code/model artifact, prompts/schema, source hashes, selections, ANM configuration, threshold, primary seed and call budget before generation. Log any changed condition order or prompt as a protocol change; do not overwrite history.
3. Inspect existing templates for zero-based row-reference clarity and explicit method caveats. Any wording change is a new version, not an unreported correction.
4. Produce a compact controlled-checker perturbation table from existing fixtures, separate from natural error prevalence; close the Track A live-model gap if feasible.
5. Report ANM as a bounded diagnostic with weak observed real-data performance. Anish's synthetic checks support numerical fidelity; parameter tuning has not established robust transfer. A new method/preprocessing idea needs a specific mechanistic rationale and clean evaluation, not an unbounded pre-midterm search.
