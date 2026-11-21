# Final execution progress

Working branch: `codex/final-delivery-20261119`, based on `main` at `7c7198d`. The older `codex/pilot-readiness` checkout and its untracked work remain untouched.

## Phase 1, reconstruction

- Read the current architecture, pilot protocols, ANM reports, roster, and archived run records. Located the ignored original 17-pair pilot and 128-row synthetic ANM experiment in the older checkout. The 512-row confirmation and 38-pair real validation are preserved in `artifacts/anm-experiments-2026-11-18/` on `main`.
- Confirmed the 17 pilot IDs and 38 real-validation IDs are disjoint in the frozen roster. They remain separate source groups by design. The 38 outcomes are now opened and cannot serve as a fresh holdout for later tuned methods.
- Found the public [Fall 2026 DSC 261 course page](https://bsalimi.github.io/dsc261-fa26/): the final artifact/report is capped at four pages excluding references, and the project presentation is in person. Canvas remains authoritative for exact deadlines and adjustments; those details were not available in the repository.
- The user-supplied `@RTK.md` and `@PROCESS.md` references do not resolve inside this project. A separate neighboring project has files with those names; they were not treated as this project's instructions.

## Phase 2, baseline

- `bash scripts/check.sh` on the working branch: 995 passed, 2 skipped because the Tübingen snapshot was not in this checkout; Ruff lint and format, both scripted demos, synthetic ANM handshake, and source/wheel build passed. The 2 skipped tests are `test_data_audit.py:67` and `test_evaluation_roster.py:68`.
- Regenerated the 50-case Track A oracle with the established generator. This output is evaluator-only and ignored by Git.
- Independently reran the current scorer against the archived 17-pair analysis and archived evaluator records. Its JSON is byte-for-byte equal to the saved `pilot-scores.json`.
- No implementation defect was established by this baseline. No source fix was made.

## Phase 3, experiments

- The local Ollama `/api/tags` response identified `qwen3:8b`, digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` at `http://127.0.0.1:11435`.
- A one-case Track A smoke completed with real model requests and raw responses. The full 50-case run is in progress with a saved configuration and dedicated output files.
- Copied the historical pilot ZIP and selected diagnostic files into `artifacts/final-delivery/`. The ZIP is unmodified; SHA-256 is `b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a`.

## Phase 3, completed experiments

- The Track A 50-case live run saved 50 raw traces with 102 actual model stages. Scoring against the hidden oracle found 1 correct answer, 1 wrong answer, 21 correct abstentions, 24 missed answerable cases without execution error, and 3 planning errors on answerable cases. The model parsed only 9/50 intended query types correctly. Its two releases were both in graph group G006. Raw traces and oracle are archived under `artifacts/final-delivery/track-a-live/`.
- Archived the original 128-row synthetic ANM run read-only. The 512-row synthetic and 38-pair real runs already have tracked originals. Independently checked the tracked ANM archive manifest against all 7,125 files.
- Recomputed 38 real ANM primary case outcomes and source-group uncertainty from saved case records. Retained all abstentions and the opened-holdout warning.
- Checker audit on 68 cached S1 checks: 5 invalidly cited outputs suppressed; 2 were benchmark-correct. E4 release outcomes were unchanged.

## Phase 4, analysis

- Generated case-level Track A and real ANM joins, exploratory cluster intervals and a vector outcome figure with `scripts/final_analysis.py`. Separate Track B source-group intervals and matched transitions remain in the archived diagnostic records. Wrote `final-results-analysis.md` and the four experiment reports.

## Phase 5, deliverables

- At initial delivery, the public DSC 261 course page specified a maximum four-page final report excluding references. The PDF rendered to three pages including references, with Markdown source beside it. The initial presentation had nine slides and passed the PowerPoint package/schema validator. No LibreOffice executable was available for a second visual render of the deck. The post-merge version is documented below.
- Wrote `final-reproducibility.md`, `scripts/verify-final.sh`, and report/presentation build sources. The exact Canvas deadline and any private rubric adjustments remain unavailable.

## Phase 6, independent review

- `bash scripts/verify-final.sh` completed: 995 tests passed, two snapshot-dependent skips, Ruff lint and format passed, both scripted demos and ANM handshake completed, source/wheel built, all 7,125 ANM archive members verified, and the Track A/B archives, PowerPoint package and report page limit checked.
- PowerPoint schema/package validation passed independently. A macOS Quick Look thumbnail confirmed the title slide renders. Full-deck visual rendering was unavailable because LibreOffice is absent.
- `final-project-acceptance.md` maps each requirement to evidence and records the Canvas deadline/rubric limitation. No unapproved paid service, deployment, protected-branch merge, or historical-artifact overwrite occurred.
# Post-merge Track B corrective run (19 November 2026)

- Audited the original 17-pair live journal against a current 17-pair deterministic pipeline replay: all 136 model-visible messages, evidence packages, selected rows, method requests and receipts match. The changed ANM 512-row validation setting is a separate study configuration. A redundant 17-pair live rerun is not required.
- Verified the final 108-pair roster: 17 pilot, four development, 38 eligible validation, 49 unscorable. The 17 and 38 panels have disjoint pair IDs and source groups, but the 38 reference outcomes were opened by the numerical ANM study.
- Froze a 38-pair exploratory integrated protocol and reviewed variable-name mapping. Reused the archived 512-row ANM requests only after exact request binding; no ANM outcome-based filtering.
- Completed a 38-pair scripted integration check (304 fixture calls) and one-pair live integration check (eight actual pinned `qwen3:8b` calls). The full 38-pair live run is now executing under `runs/postmerge-track-b-38-live/`. Raw journals are durable; model references are not included in prompts.
- The first full live attempt preserved 51 responses before a tunnel disconnect. The remaining 253 scheduled attempts were transport failures, not model abstentions. The failed journal was archived unchanged. A resumable run now binds the 51 saved responses to identical requests and invokes the model for the remaining trials, recording provenance and transport retries per generation.
- The resumed 38-pair panel completed: 51 bound saved-live responses plus 253 new live responses, with three logged transport retries. Native and independent provenance audits passed. E4/S0, S1, gate and ANM-only agreed on all 38 direction decisions (13 correct, 13 wrong, 12 without release). E4/S0 and S1 had 11 model abstentions and one binding failure; ANM-only had 12 method abstentions. Checker S2 suppressed three benchmark-correct E4 answers and no wrong E4 answers. Matched tables, intervals, raw archive, figure and failure cases are in `docs/reviews/final-track-b-integrated-38.md` and `artifacts/final-delivery/postmerge-track-b/`.
- Rebuilt the three-page academic report and ten-slide presentation from updated source; the final baseline check again passed 995 tests with two snapshot-dependent skips, lint/format, deterministic demonstrations, ANM handshake and package builds. The complete `scripts/verify-final.sh` also reproduced the archived 304-response provenance audit and integrated metrics byte for byte.
- Independently reviewed IGCI and RECI assumptions using primary papers. Neither was added after examining the 38 labels, since no untouched source-separated holdout remains for a revised-method generalization claim.

