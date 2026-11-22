# Fixed adequacy-policy replay

This is exploratory replay of opened data, not new independent validation or a deployed ANM modification. See `docs/experiments/anm-adequacy-policy-comparison-v1.md` and `docs/reviews/anm-adequacy-policy-comparison-v1.md`.

- `manifest.json`: frozen rules and source/evidence hashes, created before the complete replay.
- `inputs.json`: all 55 original primary case records and joined source metadata.
- `case-results.json`: 550 case/scheme/policy records. This is still 55 underlying cases, not 550 independent observations.
- `metrics.json`: every fixed policy's count, yield, coverage, directional accuracy, paired removal, source-weighted metric and source-group breakdown.
- `tables.md`: all 20 panel/scheme/policy configurations. It retains the unfavourable pilot and IID results alongside the later-panel strict-block 9/10 accuracy result.
- `run-records.tar.gz` / `raw-manifest.json`: self-contained frozen inputs, outputs, source/build context and every archived member's size/SHA-256.
- Validation logs and `validation.json`: exact checks, limitations and fresh-environment replay.
- `source-manifest.json`: this phase's changed/new files, excluding the inventory itself.

Original and warning-only outcomes are identical by design. Conservative policies withhold answers; they never flip directions. Total abstentions retain original abstentions plus separately counted policy abstentions. Execution failures are not converted to abstentions. These are pre-LLM, pre-checker hypothetical ANM decisions, not modified historical releases.

## Replay from saved inputs

```sh
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_adequacy_comparison.py replay --plan artifacts/anm-adequacy-policy-comparison-20261121 --output /tmp/adequacy-policy-replay-new
```

The destination must be new. Compare `case-results.json`, `metrics.json` and `tables.md` byte-for-byte. This uses no ANM fits, new permutation tests, model calls or new observations. Saved protocol/input binding is checked. Replay intentionally uses the frozen protocol rather than requiring the current evidence/source paths to match historical source; verify the archive and inventory separately.

## Clean-environment frozen-source replay

```python
from pathlib import Path
from causalbridge.evaluation.anm_failure_audit import verified_archive, materialize

artifact = Path("artifacts/anm-adequacy-policy-comparison-20261121")
root = Path("/tmp/adequacy-policy-frozen-new")
materialize(verified_archive(artifact / "run-records.tar.gz", artifact / "raw-manifest.json"), root)
```

```sh
cd /tmp/adequacy-policy-frozen-new/frozen-source
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_adequacy_comparison.py replay --plan ../plan --output ../replayed
```

Compare the three outputs with `../analysis/`. This path requires no acquisition of previous real datasets or live inference. Hashes establish integrity, not independent authentication or scientific validity. Earlier audit artifacts contain the original ANM requests and samples.

For a new preparation from current originals, use the experiment guide. Do not overwrite any original or frozen result. A preliminary software table-rendering failure was resolved with a fresh frozen plan without changing rules or input data; it remains documented and was not used as a completed result.
