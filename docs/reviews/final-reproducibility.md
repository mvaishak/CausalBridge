# Final reproducibility guide

## Environment and sources

Use Python 3.12, `uv`, and the repository at or after commit `7c7198d`. From the repository root run `uv sync --frozen --dev --extra anm` and `bash scripts/check.sh`. The latter runs lint, format, the full test suite, scripted Track A demos, the synthetic ANM handshake, and both package builds. Scripted output is a software check, not live inference.

The Track A visible benchmark is committed at `data/pilot/track_a_10_groups.jsonl`. Generate its evaluator-only oracle with `uv run --extra anm python -m causalbridge.benchmark.pilot`. Keep `data/oracle/track_a_10_groups.jsonl` out of model requests. The saved live model config is `configs/final-track-a-model.json`; verify the local `/api/tags` model name and digest before repeating inference. Run `uv run --extra anm causalbridge run --input data/pilot/track_a_10_groups.jsonl --output runs/a-new-track-a-run.jsonl --backend engine --config configs/final-track-a-model.json`. The output path must be new to preserve the original. A repeat inference may vary despite seed and temperature settings.

The original Track B pilot is preserved byte-for-byte in `artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip` (SHA-256 `b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a`). Extract it into a new directory. Reproduce its scores without model calls:

```sh
mkdir -p /tmp/causalbridge-final-pilot
unzip -oq artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip 'real-pilot-01/*' -d /tmp/causalbridge-final-pilot
uv run --extra anm python -m causalbridge.evaluation.scoring \
  --analysis /tmp/causalbridge-final-pilot/real-pilot-01/analysis.jsonl \
  --evaluator artifacts/final-delivery/track-b-pilot/evaluator-records.json \
  --mapping /tmp/causalbridge-final-pilot/real-pilot-01/evaluation_mapping.json \
  --output /tmp/causalbridge-final-rescore.json
cmp /tmp/causalbridge-final-rescore.json /tmp/causalbridge-final-pilot/real-pilot-01/pilot-scores.json
```

The upstream Tübingen snapshot can be downloaded and checked with the instructions in `docs/pilot_run.md`. `configs/pilot-data.json` pins its per-file hashes and the loader rejects changed bytes. The clean delivery worktree does not contain this ignored snapshot. Do not change hashes to bypass a mismatch.

The 512-row synthetic confirmation and 38-pair real ANM validation are in `artifacts/anm-experiments-2026-11-18/`. Its manifest covers the archived 7,125 run files. Restore to a new directory using the command in that artifact's README. `docs/anm_validation_results.md` gives the fixed real-validation command; `docs/anm_synthetic_panel.md` gives the synthetic-panel protocol. Repeating the real experiment is a replication of an opened set, not a fresh holdout. The initial 128-row panel is archived at `artifacts/final-delivery/anm-128-panel/original-run.tar.gz`; its frozen gate and full analysis are documented in `docs/reviews/anm-independent-validation.md`.

## Recompute final analyses and files

### Post-merge integrated Track B panel

`docs/reviews/postmerge-track-b-audit.md` records why the archived 17-pair pilot does not need a new live rerun. To reproduce the exact request comparison, use a hash-verified snapshot to regenerate the pilot runtime rows with the current loader, run `examples/real_data_pilot.py --scripted` on them in a **new** output directory, then run `scripts/audit_postmerge_track_b.py` with the original ZIP and that directory. `artifacts/final-delivery/postmerge-track-b/pilot-request-comparison.json` contains the saved result.

For the additional 38-pair integrated panel, read the frozen `configs/final-track-b-integrated-38.json` and reviewed labels in `configs/final-track-b-validation-names.json`. Restore the archived `sample_512` ANM requests without editing them:

```sh
mkdir -p runs/postmerge-anm-cache
tar -xzf artifacts/anm-experiments-2026-11-18/run-records.tar.gz \
  -C runs/postmerge-anm-cache \
  runs/anish-anm-validation-test-01/execution/attempts/sample_512
uv run --extra anm python scripts/run_final_track_b_38.py \
  --snapshot /path/to/hash-verified/tuebingen-snapshot \
  --output runs/a-new-integrated-38-run --scripted
```

The scripted command checks all 38 ANM bindings, evidence packages, S0/S1, S2, gate, and scoring, but does not invoke the LLM. A live run omits `--scripted` and must use a **new** output directory. It verifies the exact `/api/tags` model digest before scheduling up to 304 calls. The runner journals each raw request/response before parsing and joins reference directions only after inference. The original 38 labels have already been examined, so any live score on this panel is exploratory. Analyze a completed live run with `uv run --extra anm python scripts/analyze_final_track_b_38.py --run runs/a-new-integrated-38-run --output artifacts/a-new-analysis`. This script rejects scripted output.

Run `uv run --extra anm python scripts/final_analysis.py` after generating the Track A oracle and placing the original Track A live JSONL at `runs/final-track-a-live-20261119.jsonl`. This script asserts exactly 50 unique Track A cases and 38 real ANM cases, writes case-level joins and metrics to `artifacts/final-delivery/analysis/`, computes exploratory graph/source-group bootstrap intervals with 10,000 resamples and seed 261, and regenerates the SVG outcome figure. It reads saved outputs; it makes no LLM calls or ANM fits. The archived Track B bootstrap is in `artifacts/final-delivery/track-b-diagnostics/uncertainty.json` with 20,000 source-group draws.

Build the concise report PDF with `bash scripts/build-final-report.sh`. Build the nine-slide PowerPoint with `npm install pptxgenjs` in a Node environment and `node scripts/build_final_presentation.js`. The Markdown report source and presentation generator are editable. The official public course page caps final analysis/results at four pages excluding references; the current PDF has three pages total. Canvas remains authoritative for exact submission instructions and deadlines. Run `bash scripts/verify-final.sh` for the combined baseline and artifact check.

## Boundaries

Track A is a synthetic pilot with dependent graph-group cases. Track B is a 17-pair, seven-group exploratory live pilot. Its S2 and simple-gate records reuse S1 generations. The ANM 38-pair outcomes are opened and benchmark labels are not guaranteed causal truth. The checker validates typed evidence, not arbitrary free text or causal truth. Keep the raw traces, exclusions, abstentions, and negative results when reproducing or extending the study.
