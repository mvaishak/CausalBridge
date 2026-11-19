# Final integration review

Baseline: `7c7198d` on Python 3.12.11. `bash scripts/check.sh` completed on the delivery branch: Ruff check and format passed, 995 tests passed, 2 snapshot-dependent tests skipped, both eight-case scripted demos completed, the synthetic ANM handshake passed, and source and wheel packages built. The skipped tests are `tests/test_data_audit.py:67` and `tests/test_evaluation_roster.py:68`, because this clean worktree lacks the ignored Tübingen snapshot. The snapshot exists in the older checkout and is pinned by `configs/pilot-data.json`.

The 50-case benchmark generator ran and its independent witness tests are included in the passing suite. The saved Track B pilot was rescored with the current scorer using archived analysis, mapping and evaluator files; the output compared byte-for-byte with the saved score. The ANM archive and each of its 7,125 members passed manifest checks. No source defect requiring a code change was established by these checks.

The typed checker binds S1 attempts and evidence packages to S2 outputs, checks row and summary citations, and compares bound continuous values at 1e-12 relative/absolute tolerance. It permits empty claim lists and does not semantically verify arbitrary prose. A checker `pass` on an abstaining proposal is distinct from a released answer. Historical free-text contradictions remain in the original run; they were preserved and are analyzed separately.

Reproduce the same checks with `bash scripts/check.sh`, then the artifact commands in `docs/reviews/final-reproducibility.md`. Demo outputs are scripted, and the ANM handshake uses scripted model text. Neither is counted as live inference.
