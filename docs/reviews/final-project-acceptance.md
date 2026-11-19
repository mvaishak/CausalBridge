# Final project acceptance review

Review basis: dedicated branch `codex/final-delivery-20261119` from `main` commit `7c7198d`; original pilot and ANM archives; fresh local Track A inference; final scorer, analysis, report and presentation. This is a research-evidence acceptance decision, not a claim that the model became causally reliable.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Contributor work reconstructed and original records preserved | `final-execution-audit.md`; original Track B ZIP; 128-row ANM tar; tracked 7,125-file ANM archive | Complete |
| Live-model provenance established | Track B native journal/raw Ollama payloads and first-run summary; Track A 50 raw traces and `/api/tags` digest | Complete |
| Missing Track A live pilot executed | 50 unique frozen cases, 102 model stages, hidden oracle joined afterward in `artifacts/final-delivery/analysis/` | Complete, negative result |
| Track B saved results independently checked | Current scorer output compared byte-for-byte with archived `pilot-scores.json`; 136 live S0/S1 generations and 68 cached S2 checks | Complete |
| ANM experiments reconciled | 128-row failed gate, 512-row synthetic confirmation, 38-pair real validation; manifest checked against all 7,125 archived files | Complete; real labels remain fallible |
| Checker evaluated independently | 68 cached checks, 5 suppressions, 2 correct answers sacrificed, 0 E4 changes; typed and free-text limits recorded | Complete |
| Source overlap and holdout validity checked | Frozen roster: 17 pilot pairs and 38 validation pairs share no IDs or source groups; 38 outcomes now opened | Complete; no post-outcome revised-method test claimed |
| Baseline implementation verified | Fresh `bash scripts/verify-final.sh`: 995 tests passed, 2 snapshot-dependent skips; lint, format, demos, handshake, build and archives passed | Complete with documented environmental skips |
| Direction, coverage, uncertainty and failure analysis | `final-results-analysis.md`, case-level JSON, grouped exploratory intervals, `outcomes.svg` | Complete within small-sample limits |
| Report matches public course page | Three-page `report/CausalBridge-final.pdf`, including references; public limit is four pages excluding references | Complete for published requirement |
| Project presentation prepared | Nine-slide `presentation/CausalBridge-final.pptx`, schema/package validator passed | Complete; second render unavailable without LibreOffice |
| Reproducibility and handoff | `final-reproducibility.md`, `scripts/final_analysis.py`, `scripts/verify-final.sh`, report and slide build sources | Complete |
| Final critical review | Claims checked against raw/case-level artifacts; negative outcomes and opened validation set retained | Complete |

## Critical findings from the final review

The Track A verifier marked `G006_sign_complete` as `verified` for a misparsed intervention-probability query. The original question was about effect sign and its oracle answer was negative. The final scorer uses the original question and marks the release wrong. No prompt or semantic rule was retuned on those 50 cases. A revised Track A pipeline needs a new graph-group holdout.

Track B's S2 checker is a cached release filter. It does not provide a second model generation. Its five suppressed citations improve process integrity but do not change E4 direction decisions. The 38 real ANM validation pairs have opened labels and cannot be recycled as an independent final test for any revised method. Group bootstrap intervals are exploratory because group counts are small and benchmark reference quality is not sampled.

## External details and technical limitations

The [public Fall 2026 DSC 261 course page](https://bsalimi.github.io/dsc261-fa26/) specifies the four-page final report cap and in-person presentation. Canvas is authoritative for the exact deadline, submission channel and private rubric adjustments, which were not accessible from this repository. The clean worktree omits the ignored Tübingen snapshot, causing two explicit test skips; the source snapshot exists in the preserved older checkout and is hash-pinned. LibreOffice was not installed, so the PowerPoint passed structural validation and a title-slide Quick Look render, but no full-deck second render.

No required inference is blocked. The project is ready for the team to check Canvas submission particulars and present the negative result accurately. Do not state that CausalBridge improved direction accuracy.
