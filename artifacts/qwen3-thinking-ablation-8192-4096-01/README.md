# Qwen3 thinking ablation at 8192/4096

Raw archive includes 272 final-run requests/responses, separate reasoning, activation/preflight records, source fingerprints, per-case results, statistical summaries and software logs. One S1-Off/E4 observation truncated and remains a failure.

Extract into a fresh directory using `tar -xzf run-records.tar.gz -C /path/to/fresh-output`. Copy or point the extracted experiment directory under `runs/` before using the analysis scripts. The report and validation are in `docs/reviews/qwen3-thinking-ablation-8192-4096-01.*`. Run the analyzer, report generator, then independent verifier to reproduce results without inference.

All 271 valid final predictions had empty claim lists. Checker release does not certify evidentiary support. No independent holdout claim is made.
