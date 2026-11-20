# Final project acceptance review

Review basis: dedicated post-merge branch `codex/postmerge-track-b-evaluation-20261119` from final-delivery commit `d266004` and merged `main` commit `7c7198d`; original pilot and ANM archives; fresh local Track A inference; new integrated Track B inference; final scorer, analysis, report and presentation. This is a research-evidence acceptance decision, not a claim that the model became causally reliable.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Contributor work reconstructed and original records preserved | `final-execution-audit.md`; original Track B ZIP; 128-row ANM tar; tracked 7,125-file ANM archive | Complete |
| Live-model provenance established | Track B native journal/raw Ollama payloads and first-run summary; Track A 50 raw traces and `/api/tags` digest | Complete |
| Missing Track A live pilot executed | 50 unique frozen cases, 102 model stages, hidden oracle joined afterward in `artifacts/final-delivery/analysis/` | Complete, negative result |
| Track B saved results independently checked | Current scorer output compared byte-for-byte with archived `pilot-scores.json`; 136 live S0/S1 generations and 68 cached S2 checks | Complete |
| Post-merge pilot equivalence audited | Current 17-pair replay compared all 136 original prompts, packages, selected rows and method receipts; ANM/evidence/integration/predictor source hashes unchanged | Complete; redundant 17-pair live rerun unwarranted |
| Final integrated Track B panel executed | Frozen 38-pair, 12-group cohort; 51 exact saved-live responses plus 253 new `qwen3:8b` generations; 152 S2 checks | Complete, exploratory opened-label panel |
| Interrupted model service handled without data substitution | First attempt archived with 51 responses and 253 transport failures; resumed run logs 3 retries; independent 304-trial provenance audit passed | Complete; failures excluded from performance scores |
| ANM experiments reconciled | 128-row failed gate, 512-row synthetic confirmation, 38-pair real validation; manifest checked against all 7,125 archived files | Complete; real labels remain fallible |
| Checker evaluated independently | 68 cached checks, 5 suppressions, 2 correct answers sacrificed, 0 E4 changes; typed and free-text limits recorded | Complete |
| Source overlap and holdout validity checked | Frozen roster: 17 pilot pairs and 38 validation pairs share no IDs or source groups; 38 outcomes opened before the new LLM panel | Complete; no post-outcome independent confirmation claimed |
| Alternative direction methods reviewed | `postmerge-track-b-audit.md` evaluates IGCI/RECI assumptions against ANM failures using primary method papers | Complete; no post-label method search without new holdout |
| Baseline implementation verified | Fresh `bash scripts/verify-final.sh`: 995 tests passed, 2 snapshot-dependent skips; lint, format, demos, handshake, build and all archive checks passed | Complete with documented environmental skips |
| Direction, coverage, uncertainty and failure analysis | `final-results-analysis.md`, both Track B panel reports, case-level JSON, grouped exploratory intervals and SVG figures | Complete within grouped/opened-label limits |
| Report matches public course page | Three-page `report/CausalBridge-final.pdf`, including references; public limit is four pages excluding references | Complete for published requirement |
| Project presentation prepared | Ten-slide `presentation/CausalBridge-final.pptx`, ZIP/package validator passed | Complete; second render unavailable without LibreOffice |
| Reproducibility and handoff | `final-reproducibility.md`, `scripts/final_analysis.py`, `scripts/verify-final.sh`, report and slide build sources | Complete |
| Final critical review | Claims checked against raw/case-level artifacts; negative outcomes and opened validation set retained | Complete |

## Critical findings from the final review

The Track A verifier marked `G006_sign_complete` as `verified` for a misparsed intervention-probability query. The original question was about effect sign and its oracle answer was negative. The final scorer uses the original question and marks the release wrong. No prompt or semantic rule was retuned on those 50 cases. A revised Track A pipeline needs a new graph-group holdout.

Track B's S2 checker is a cached release filter. It does not provide a second model generation. Its five suppressed citations in the 17-pair pilot improved process integrity but did not change E4 direction decisions. In the new 38-pair panel, 14 answered S1 proposals were suppressed, seven benchmark-correct and seven wrong; three correct E4 answers were lost and no wrong E4 arrow was filtered. E4/S0 and S1 copied ANM on all 38 cases, including 13 benchmark-wrong directions. The 38 real ANM validation labels were opened before this run, and the source-description name mapping was not blinded; this cannot establish independent performance for a revised method. Group bootstrap intervals are exploratory because group counts are small and benchmark reference quality is not sampled.

## External details and technical limitations

The [public Fall 2026 DSC 261 course page](https://bsalimi.github.io/dsc261-fa26/) specifies the four-page final report cap and in-person presentation. Canvas is authoritative for the exact deadline, submission channel and private rubric adjustments, which were not accessible from this repository. The clean worktree omits the ignored Tübingen snapshot, causing two explicit test skips; the source snapshot exists in the preserved older checkout and is hash-pinned. LibreOffice was not installed, so the PowerPoint passed structural validation and a title-slide Quick Look render, but no full-deck second render.

No required inference is blocked. The project is ready for the team to check Canvas submission particulars and present the negative result accurately. Do not state that CausalBridge improved direction accuracy. The larger panel changes the sign of the matched correct-yield contrast relative to the original pilot, but its broad interval spans zero and the checker reduces E4 correct coverage; the main conclusion remains bounded.
