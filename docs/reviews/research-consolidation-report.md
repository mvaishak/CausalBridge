# Scientific consolidation verification and release gates

Date: 2026-11-22 (America/Los_Angeles). Base: `origin/main` `fb81b96a92c8cc78360276e54bd3d9be0a974e56`, fetched without pruning. Integration branch: `codex/scientific-consolidation-20261122`. [Index](../research/README.md) and [file-level manifest](scientific-integration-manifest.md).

## Incorporated and excluded work

The branch includes unchanged main final-delivery sources and archives; thinking ablation `ecd1b3054bb290830f9a9dfa0b1b6763fe2030d1`; diagnostic v1/v2/v3 through `7d4a408cc8fcb0b1238971c04141c0fd579a5a20`; ANM diagnosis `d3be02c76d7e20fa5395301e5e9c2922baa25133`; prepared synthetic cue study `368d6486261452ff7e5fee85f75e1a113e48509b`; alternate v2 design documents `71ff36ae0dfc528b831b8206afb8103bb11bf01a`; and historical pilot review tools `1d59c848637c09b32bbcdf97acf30b2446421467`. Older incorporated branches are accounted for by the [lineage audit](branch-lineage-and-provenance-audit.md). Runtime conflicts and exclusions are recorded in the [manifest](scientific-integration-manifest.md). The alternate prompt-only v2 implementation was not installed. The submitted report and presentation were not changed.

The exact 495,579-byte original completed v3 archive is tracked at [`artifacts/diagnostic-v3/cue-investigation-v3-7d4a408-complete-01.tar.gz`](../../artifacts/diagnostic-v3/cue-investigation-v3-7d4a408-complete-01.tar.gz), SHA-256 `6974769bfd774c2cb38819f637e5e41e38cb6eddbe8e22363c699b1b0e4fd1a1`. The original in the v3 worktree remains unchanged. All 819 archive members have safe paths, 818 manifest-listed sizes/hashes match, all 67 frozen source hashes match `7d4a408`, and the frozen plan describes 17 opened pairs, five arms and both thinking settings. The full study completed 170 calls after 4 diagnostic and 20 preflight live calls. Its 82 correct, 47 wrong, 40 abstentions, one execution failure and three overlapping checker rejections are separate from the 96 *planned* synthetic cue calls.

The tracked [archive inventory](../research/experiment-registry.md#frozen-archive-inventory) records all final and new small archives with bytes and SHA-256. Two additional failed-preflight archives are tracked. Four other frozen failed-preflight tarballs contain a personal login address; they were **not pushed or modified**. They remain only at their original v3 worktree location, with names and reason recorded in the manifest. A transient unpublished local branch that had copied those four packages was removed before PR creation. The public integration branch and draft PR never contained that commit. A restricted preservation location is still required for those original failed attempts if the team needs them shared. Offline-only plan packages were not copied.

## Verification performed

- Baseline `fb81b96`: `uv run pytest -q` 1,025 passed, two snapshot-dependent skips; `uv run ruff check .` passed.
- After v3 source: 1,145 passed, same two skips; Ruff passed. After ANM: 1,207 passed, same skips; Ruff passed. After synthetic cue: 1,215 passed, same skips; Ruff passed. Historical review/diagnostic targeted tests: 39 passed; Ruff passed.
- Consolidated full suite: 1,225 passed, same two skips. `ruff check` and `ruff format --check` passed. `scripts/verify-final.sh` passed: it reran 1,225 tests with the same two skips, built source/wheel distributions, reproduced saved final analyses byte-for-byte, reported zero new scientific generations/fits, and verified all 7,125 files in the existing ANM archive.
- All 130 tracked JSON documents parsed. All links in `docs/research/` resolve after this report was created. Selected files added from the v3, ANM and synthetic cue tips had zero byte differences from their source commits. The final report and presentation have zero differences from `origin/main`.
- Every tracked TAR/ZIP archive was opened, had no unsafe member path, and was scanned for credential/private-key/email patterns. The one apparent hit in the real-noise archive was an embedded compressed copy of the separately scanned ANM archive, which had no hits. ZIP CRC checks passed.
- The thinking ablation verifier passed raw recount, identity, budgets, source hashes and request matches after safe extraction into ignored `runs/` in this isolated worktree.
- The v3 full run was replayed using a temporary `git archive` checkout of its exact frozen `7d4a408` source plus the **tracked** v3 tarball. `scripts/diagnostic_investigation.py analyze` completed; `case-results.json`, `metrics.json`, and `report.md` were byte-identical to the frozen archived versions. The exact historical source is required because the original plan guards the complete source file set: additive ANM modules in this consolidated tree change that set, even though none of the 67 frozen files changed. No frozen source or archive was patched to bypass the guard.
- No new LLM inference, ANM fit, raw-response rewrite, source-branch mutation, or main merge was performed.

## Release gates

| Gate | Verdict | Reason |
| --- | --- | --- |
| A. Source completeness | PASS | Every fetched pushed branch was inventoried; meaningful divergent additions are integrated or explicitly excluded. |
| B. Artifact integrity | FAIL | V3 and other selected small archives are tracked and verified, but four important v1 failed-preflight packages cannot be published unchanged because they contain a personal login address. They remain only in the original local worktree. |
| C. Reproducibility and regression | NOT VERIFIED | Feasible full tests, static checks, thinking verification and exact v3 replay pass. The two baseline snapshot-dependent tests remain skipped; not every historical ANM raw replay was rerun during consolidation. |
| D. Scientific reporting consistency | PASS | Separate protocols, opened labels, independent units, failure/abstention categories and prepared versus completed status were checked against original reports and manifests. |

**NO-GO for merging into main.** A draft PR can be reviewed, but Gate B is FAIL and Gate C remains NOT VERIFIED. Resolve restricted preservation of the four frozen failed archives and complete the remaining reproduction checks before considering a merge. No branch or historical record should be rewritten to satisfy a gate.

## Exact v3 replay route

Use a temporary directory, `git archive 7d4a408cc8fcb0b1238971c04141c0fd579a5a20` to populate the frozen source, and safely extract the tracked v3 archive there. Then run `uv sync --all-groups --extra anm` and `uv run python scripts/diagnostic_investigation.py analyze --plan runs/cue-v3-full-plan-7d4a408-01 --run runs/cue-v3-full-live-7d4a408-01 --output runs/consolidation-replay-01`. Compare the three generated files against `runs/cue-v3-analysis-7d4a408-01/`. This uses the consolidated repository's historical commit and tracked archive without switching the active branch or changing frozen files.

## Missing historical sources

No `REPRODUCIBILITY.md`, `RTK.md`, `PROCESS.md`, or repository `AGENTS.md` exists at the fetched base or in this checkout. Reproduction guidance was reconstructed from [final reproducibility](final-reproducibility.md), the experiment-specific reports, committed manifests and the external lineage/reconciliation audit files copied unchanged into this directory. No newer cross-branch audit was found in the inspected repository and supplied audit outputs.
