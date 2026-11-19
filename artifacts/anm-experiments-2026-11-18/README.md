# Saved ANM experiment records

This bundle preserves the local ANM runs produced before this commit. The implementation and interpretation are documented in `docs/anm_development.md`, `docs/anm_synthetic_panel.md`, and `docs/anm_validation_results.md`.

- `run-records.tar.gz` contains all 7,125 files from the twelve `runs/anish-anm-*` paths, including original ANM requests, inputs, results, configurations, reports, and audit records.
- `manifest.json` records the archive SHA-256 and each archived file's relative path, size, and SHA-256. Every archived file was read back and checked against its original before commit.
- `summaries/` provides readable copies of the principal development, larger-sample, synthetic, and real-validation reports without extracting the archive.

The preliminary development runs are retained as historical records. They are not additional independent datasets. Local paths in the original records are preserved for provenance; those paths need not exist on another machine.

## Results

- Synthetic confirmation, predeclared primary configuration: 26 correct, zero wrong, six abstentions on 32 compatible datasets (100% accuracy among answered cases; 81.25% coverage). This demonstrates recovery under the tested synthetic assumptions.
- Real validation, predeclared primary configuration: 13 correct, 13 wrong, twelve abstentions on 38 pairs (50% unweighted accuracy among answered cases; 48.1% weighted accuracy). These results do not establish reliable causal-direction recovery on real data.
- The 38 validation pairs have now been evaluated. Future tuning informed by these results cannot treat them as an untouched final test.

## Restore

From the repository root, extract into a new directory so existing local runs are preserved:

```sh
mkdir -p /tmp/causalbridge-anm-records
tar -xzf artifacts/anm-experiments-2026-11-18/run-records.tar.gz -C /tmp/causalbridge-anm-records
```

The archive contains experiment records, not the full upstream Tuebingen snapshot or a Python environment. Reproduction prerequisites and commands are in the linked documentation. No new numerical experiments were run to package these records.
