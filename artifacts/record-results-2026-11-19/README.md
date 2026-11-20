# Recorded-results package — 19 November 2026

**Status update — 20 November 2026:** this directory preserves the original
17-pair results package. Current delivery is on
[`codex/postmerge-track-b-evaluation-20261119` at `d773118`](https://github.com/mvaishak/CausalBridge/blob/d773118951986a2bd25d57a98adb4c9d0881a6b9/docs/reviews/final-execution-audit.md).
Track A's live 50-question evaluation and the larger integrated Track B panel
(38 pairs, 304 real-model responses) are complete. The 17-pair repeatability
plan is historical/optional; do not launch duplicate inference from these notes.
The 38-pair panel uses already opened labels and is exploratory, not a fresh holdout.

This extends the earlier exploratory pilot analysis with measured resources,
explicit baselines, an accuracy–coverage figure and bounded mechanism controls.
The opened data are not a fresh final test. Human validation remains deferred.

Start with [report.md](report.md) and the [team handoff](../../docs/team-handoff/2026-11-19/README.md).

## Contents

| File | Evidence |
| --- | --- |
| generation-costs.csv/json | Unique primary generation token/latency/failure accounting by package/prompt |
| baseline-comparisons.csv/json | S0/S1/S2/SIMPLE_GATE/ANM-only on fixed cases and weights |
| accuracy-coverage.png/svg | Exact measured rates; no-answer accuracy stays undefined |
| process-controls-summary.json | Counts and expected codes for 14 unchanged controls and 56 artificial perturbations |
| anm-independent-recount.json | Archive integrity, saved-score direction checks and primary 38-case recount |
| audit-summary.json | Original binding audit status, counts, limitations and relocation disclosure |
| validation.json | Completed checks on the results code and original records |

Full case-level process trials, evaluator joins, diagnosis, session, local service
query and absolute-path provenance are local reproduction outputs, excluded from
this GitHub handoff. They can be regenerated with the commands below.

128,270 input tokens + 22,896 output tokens were used in 136 unique original
generations. Summed client generation latency is 1,537.17 seconds / 25.62 minutes.
Resume added zero calls. These figures exclude duplication from invocation/export
copies and cached S2. Checker and ANM latency and monetary cost are unknown.
Derived baselines reuse existing work; zero extra generation is not zero total compute.

The current main already includes #12's mapping fix plus later lineage/diagnosis
corrections. #12 was closed as superseded on 19 November 2026 with user
authorization; it was not merged. See the [review](../../docs/reviews/pr12-after-main-integration.md)
for exact heads and limits.

## Reproduce

From a fresh checkout of this PR branch, first retrieve the preserved archive
from the pinned final-delivery commit without switching your checkout. This
requires GitHub read access; it makes no model calls and does not refit ANM.
Run from the repository root, using a fresh destination:

```bash
git fetch origin d773118951986a2bd25d57a98adb4c9d0881a6b9
mkdir -p runs/pr16-reproduction
test ! -e runs/pr16-reproduction/original-real-pilot-01.zip
git show d773118951986a2bd25d57a98adb4c9d0881a6b9:artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip > runs/pr16-reproduction/original-real-pilot-01.zip
python3 - <<'CHECK_ARCHIVE'
import hashlib
from pathlib import Path
archive = Path("runs/pr16-reproduction/original-real-pilot-01.zip")
expected = "b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a"
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit("Pilot archive hash mismatch; stop without extracting")
CHECK_ARCHIVE
test ! -e runs/pr16-reproduction/real-pilot-01
unzip -n runs/pr16-reproduction/original-real-pilot-01.zip 'real-pilot-01/*' -d runs/pr16-reproduction
```

Each command must succeed before continuing; stop on an existing destination or
hash mismatch. The archive hash above identifies the preserved original pilot.
Fetch the separate 218-file source snapshot using the **Reproduce data preparation on another checkout**
commands in [the pilot guide](../../docs/pilot_run.md). Verify it against
`configs/pilot-data.json`; do not update hashes to accept different source bytes.
The snapshot is required to independently reselect observations, not to recreate
historical model responses. The original evaluator joins are regenerated from
that verified snapshot and roster by the analysis script.

With the archive extracted and snapshot verified:

```bash
uv sync --cache-dir /tmp/causalbridge-results-uv --frozen --dev --extra anm
PYTHONPATH=src .venv/bin/python examples/finish_record_results.py \
  --pilot runs/pr16-reproduction/real-pilot-01 --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --original-method-root \
    '/Users/mvaishak/Documents/ChatGPT/DSC-261 Project/runs/real-pilot-01/anm' \
  --output runs/pr16-reproduction/record-results-new
PYTHONPATH=src .venv/bin/python examples/check_saved_process_controls.py \
  --pilot runs/pr16-reproduction/real-pilot-01 --output runs/pr16-reproduction/record-results-new/process-controls.json
.venv/bin/python examples/review_saved_anm_validation.py \
  --archive-root artifacts/anm-experiments-2026-11-18 \
  --output runs/pr16-reproduction/record-results-new/anm-independent-recount.json
python3 examples/plot_record_results.py --results runs/pr16-reproduction/record-results-new
```

Use fresh outputs. The plotter requires Matplotlib in its Python environment;
no plotting dependency was added to the production lockfile. Source data setup
is documented in [the pilot guide](../../docs/pilot_run.md). Identity relocation changes read-only
lookup, not original journal/receipt bytes.

Full repository checks: 1,008 tests pass, no skips, lint/format, demos, synthetic
handshake and builds pass. The scientific resource analysis also repeated with
generation, predictor, method-execution and HTTP calls blocked; all six counters
remained zero. The normal repository suite separately executes existing synthetic
numeric tests/handshake. No new scientific model outputs or ANM fits are claimed.

Do not send evaluator records, reports or controlled-checker outcomes to people
who are meant to review the corresponding content blind. No server was started and no source branch was overwritten. The results are
being shared through a draft PR; no team messages were sent automatically.
