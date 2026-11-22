# Independent numerical and relative-ranking adequacy audit

Read `docs/reviews/anm-decision-audit-v1.md` for the interpretation. This exploratory follow-up uses all 17 pilot and 38 primary later-panel pairs; it does not tune ANM or change historical directions. There are 110 directional reference calculations and 439,780 new permutation statistics (110 directions × two schemes × 1,999). The synthetic table reuses the previous component-study outcomes rather than running new synthetic fits.

`records.json` contains both independent-fit scores and reference HSIC computed from original residuals, numerical discrepancies, original outcomes, and every nominal IID/block p-value. `tables.md` reports all cases and denominators. `manifest.json` freezes inputs and executable source before the complete run; its internal protocol version v2 records an amendment after a preliminary row-order-sensitive mismatch. The config filename remains `anm-decision-audit-v1.json` for traceability. All preliminary failure records remain in the raw archive.

The report command's `matched_directions` field counts the 110 fixed-original-residual HSIC checks, which all passed. It does not mean all eigen-fit scores matched: 16 exceeded the strict comparison tolerance, but zero decisions changed. See the review for details. Likewise execution log text `numerically matched` indicates completion of each case's fixed-residual formula check, not perfect agreement of all end-to-end calculations.

## Replay saved tables

```sh
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_decision_audit.py report --plan artifacts/anm-decision-audit-20261121 --output /tmp/anm-decision-audit-tables.md
```

No fits, permutations or LLM calls are required. The saved record digest is checked. The synthetic summary additionally reads `artifacts/anm-mechanism-study-20261121/case-results.json`, whose exact bytes are hash-bound in the execution manifest and included with the frozen source.

## New execution from current source

Use a fresh plan directory:

```sh
uv run python scripts/anm_decision_audit.py prepare --plan runs/decision-audit-new
uv run python scripts/anm_decision_audit.py run --plan runs/decision-audit-new
uv run python scripts/anm_decision_audit.py report --plan runs/decision-audit-new --output runs/decision-audit-new/tables.md
```

Preparation verifies the previous real-noise raw archive and copies complete original records. It selects all primary pairs from the previous saved `real-records.json`, and copies their fixed original residual vectors for adequacy testing. The latter originate from the prior reconstruction, so are not an independent ground truth for software correctness. The new eigensolver fit independently uses the saved sample rather than those residuals.

## Frozen-source full rerun

The 466-member `run-records.tar.gz` contains the complete plan, original inputs, frozen vectors, source, lockfile, build context, old synthetic summary, outputs and preliminary failure. `raw-manifest.json` supplies member sizes/hashes and the archive SHA-256.

```python
from pathlib import Path
import shutil
from causalbridge.evaluation.anm_failure_audit import verified_archive, materialize

artifact = Path("artifacts/anm-decision-audit-20261121")
root = Path("/tmp/anm-decision-audit-restored")
materialize(verified_archive(artifact / "run-records.tar.gz", artifact / "raw-manifest.json"), root)
new = root / "rerun"
new.mkdir()
for name in ["manifest.json", "frozen-vectors.json"]:
    shutil.copy2(root / "plan" / name, new / name)
shutil.copytree(root / "plan" / "originals", new / "originals")
```

```sh
cd /tmp/anm-decision-audit-restored/plan/frozen-source
uv sync --frozen --extra anm --group dev
uv run python scripts/anm_decision_audit.py run --plan ../../rerun
uv run python scripts/anm_decision_audit.py report --plan ../../rerun --output ../../rerun/tables.md
```

Compare `records.json`, `completion.json` and `tables.md` in the restored `plan/` and fresh `rerun/`. Preserve originals; do not retry an existing execution directory. Platform/library differences can affect floating-point results and tie-sensitive bandwidths; do not overwrite saved results to hide discrepancies. No GPU or live model is required. Hashes check integrity, not third-party authentication or scientific validity.

`validation.json`, the test log, and the clean-environment replay log record final checks. `source-manifest.json` inventories this phase only. Previous committed investigations and production ANM are unchanged.
