# Fixed ANM mean-estimator robustness check

Read `docs/reviews/anm-mean-robustness-v1.md` for bounded interpretation and `docs/experiments/anm-mean-robustness-v1.md` for the frozen protocol. This is exploratory diagnostic research on already-opened pilot cases, not an ANM accuracy improvement.

- `manifest.json`: pre-execution estimator/case schedule, spread protocol, original input hashes, and source hashes.
- `records.json`: all 32 real configurations and 64 synthetic configurations, predictions, residual vectors, MSE, nominal diagnostic p-values and real-case Holm adjustments. All configurations are retained.
- `tables.md`: deterministic tables for every configuration; no fits needed to regenerate.
- `started.json` / `completion.json`: freeze binding and results digest. No timestamps or elapsed time enter deterministic comparisons.
- `run-records.tar.gz` / `raw-manifest.json`: self-contained original inputs, frozen source/build context/lockfile, and exact execution artifacts; every archive member has a size and SHA-256. The original input and source directories are stored inside this archive.
- `validation.json` and logs: regression, formatting, and clean-environment numerical replay results.
- `source-manifest.json`: hashes of the new phase's source, documentation, and artifacts, excluding the inventory itself. Earlier phase artifacts are preserved.

## Replay existing tables only

```sh
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_mean_robustness.py report --plan artifacts/anm-mean-robustness-20261121 --output /tmp/mean-robustness-tables.md
```

This command verifies the saved record digest and requires no regression fits, new observations, or LLM inference.

## Reproduce all numerical results from frozen inputs

Restore to a fresh directory, verifying every archived member first:

```python
from pathlib import Path
from causalbridge.evaluation.anm_failure_audit import verified_archive, materialize

artifact = Path("artifacts/anm-mean-robustness-20261121")
files = verified_archive(artifact / "run-records.tar.gz", artifact / "raw-manifest.json")
materialize(files, Path("/tmp/mean-robustness-restored"))
```

The destination must be fresh. Keep restored execution artifacts unchanged. Create a new sibling run containing only the frozen manifest and original inputs:

```python
from pathlib import Path
import shutil

root = Path("/tmp/mean-robustness-restored")
run = root / "new-run"
run.mkdir()
shutil.copy2(root / "manifest.json", run / "manifest.json")
shutil.copytree(root / "originals", run / "originals")
```

Then:

```sh
cd /tmp/mean-robustness-restored/frozen-source
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_mean_robustness.py run --plan ../new-run
uv run python scripts/anm_mean_robustness.py report --plan ../new-run --output ../new-run/tables.md
```

Compare `records.json`, `completion.json`, and `tables.md` with the restored originals. All three matched byte-for-byte in a fresh Python 3.12.16 / NumPy 2.5.4 environment. Cross-platform BLAS, NumPy, or floating-point differences may prevent byte identity; do not overwrite frozen outputs in response. Hashes establish integrity, not independent provenance authentication.

The original producer is reconstructed in both directions as a preservation check, but alternate estimators are applied only in the reference direction. Across the numerical execution there are 16 original directional reconstructions, 32 real diagnostic fits, and 64 synthetic diagnostic fits, plus auxiliary cross-fitted residual correction. No new causal decisions are made. The four random draws in the synthetic controls are reused across the two functions and two noise regimes. Confidence and generality are correspondingly limited.
