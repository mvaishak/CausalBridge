# Diagnostic-following investigation: offline evidence

This directory contains **saved-result diagnosis and software validation only**.
The controlled-cue experiment has not been run with a real LLM.

- `saved-diagnosis/report.md`: exact propagation and harmful-switch counts.
- `saved-diagnosis/metrics.json`: numeric denominators and frozen-archive hashes.
- `saved-diagnosis/observations.json`: 408 upstream observations, including explanations
  and the ablation's separate thinking text where recorded.
- `saved-diagnosis/transitions.json`: 102 E3/E4 comparisons with original ANM directions.
- `saved-diagnosis/manual-review.csv`: unfilled human coding sheet, not a completed review.
- `software-validation.log`: actual full repository check, 1,053 passed and two existing
  optional-snapshot skips; lint, format, demos, handshake and builds pass.
- `smoke-validation.log`: 20 preflight + 170 full scripted cells, no live model calls.
- `validation.json`: machine-readable performed checks and remaining work.
- `source-manifest.json`: SHA-256 inventory of this change set, excluding itself.

The saved diagnosis verifies 8/8 wrong-ANM copying in both thinking-on styles and
4/4 harmful switches among eligible original S0 cases. In the new thinking ablation,
each thinking-on style had 2/2 eligible correct E3 answers become wrong E4 answers.
These small selected denominators describe preserved runs, not a general rate.
The one thinking-off S1 truncation remains a failure (7/8 wrong copies + 1/8 failure).

New inference requires the [runner handoff](../../docs/team-handoff/diagnostic-investigation-v1.md).
It returns a separate raw archive and analysis for human interpretation. Do not
replace these records or the original frozen results with new experimental scores.
