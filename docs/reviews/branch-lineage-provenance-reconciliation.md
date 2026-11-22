# CausalBridge: local artifact reconciliation of the branch lineage audit

Audit date: 2026-11-22 (America/Los_Angeles). This is a read-only reconciliation. No existing result, protocol, checkout, or branch was modified; no LLM experiment was run. The prior audit is at `/Users/mvaishak/Documents/Codex/2026-11-22/files-pasted-by-the-user-causalbridge/outputs/branch-lineage-and-provenance-audit.md` and in its detached audit worktree. It is **not** present at `docs/reviews/branch-lineage-and-provenance-audit.md` in the active `main` checkout.

## Verdict

**The 170-cell v3 diagnostic-following study completed and is preserved locally.** The prior branch audit's statement that no completed v3 live study was found was true only for the *checked-in tree*, but materially incomplete as a project-wide finding. The active v3 worktree holds both ignored live run directories and an untracked, self-contained 819-member archive, `cue-investigation-v3-7d4a408-complete-01.tar.gz`. Its 818-file SHA-256 inventory passed independent byte checks; the archive and local files match. The diagnostic gate passed 4/4, the live preflight passed 20/20, and the full run has 170 distinct planned requests, 170 records and 170 raw HTTP response wrappers. The full run has **82 benchmark-correct, 47 benchmark-wrong, 40 abstentions, and one execution failure before verification**. Three checker rejections are *also* upstream abstentions; they are not three additional failures or suppressed directional answers.

The evidence supports citing this as an **exploratory controlled directional-cue result on the already-opened 17-pair cohort**, with an explicit pointer to the external archive, exact source commit and manifest hash. It does not support a held-out accuracy claim, an ANM improvement claim, or a claim about the model's internal reasoning. The archive is currently untracked and thus not preserved by a Git clone or remote branch alone. Its local preservation is verified; its long-term/team-accessible preservation is not established.

## Where the evidence lives

| Evidence class | Exact path and role | Finding |
| --- | --- | --- |
| Committed source | `/Users/mvaishak/.codex/worktrees/68cd/DSC-261 Project` at `7d4a408cc8fcb0b1238971c04141c0fd579a5a20`; `configs/diagnostic-investigation-v3.json`, `scripts/diagnostic_investigation.py`, `src/causalbridge/evaluation/diagnostic_{protocol,runtime,analysis}.py` | All 67 source entries in each v3 plan's `source_sha256` match Git blobs at `7d4a408` and the local checkout. The commit contains the protocol and software, not the live results. |
| Uncommitted local evidence | V3 worktree `runs/cue-v3-{diagnostic,preflight,full}-{plan,live}-7d4a408-01/`, `runs/cue-v3-analysis-7d4a408-01/`, `runs/cue-v3-bundle-7d4a408-01/` | Exact plans, evaluator, requests, raw replies, records, model snapshots, summaries, analysis, and verification. These directories are Git-ignored. |
| External-to-Git archive | `/Users/mvaishak/.codex/worktrees/68cd/DSC-261 Project/cue-investigation-v3-7d4a408-complete-01.tar.gz` | 495,579 bytes; SHA-256 `6974769bfd774c2cb38819f637e5e41e38cb6eddbe8e22363c699b1b0e4fd1a1`; 819 regular members, including its own manifest. All 818 manifest-listed files matched size and SHA-256; no duplicate or unsafe member paths. All 818 files match the local worktree copies. |
| Archived verification | `runs/cue-v3-bundle-7d4a408-01/verification.json` within the archive | Records request-order and raw-replay checks for all three phases and lists the single failure and three rejections by trial ID. These are archived assertions, corroborated below by independent count/hash checks. |
| Archived analysis | `runs/cue-v3-analysis-7d4a408-01/{case-results.json,metrics.json,report.md}` within the archive | 170 case rows, 17 unique pairs and seven source groups. Independent grouping of case rows reproduces all 10 cell outcome counts in `metrics.json`. |

The v3 worktree's **10 untracked status entries are all tarballs**: five v1/offline failure or preparation packages, three v2 offline/failure packages, one v1 repeat schema failure package, and the completed v3 package. Its ignored `runs/` directory holds v1/v2/v3 software smokes and live attempts. The v2 `4f600b4` live preflight stopped after one of 20 scheduled calls with one failure; no v2 full live run was found. The various 170-cell v1/v2/v3 `cue-*-smoke-*` summaries explicitly have `research_result=false` and are scripted software checks, not additional live research results. The four-cell v3 diagnostic and 20-cell v3 preflight are completed live gates but not scientific denominators. No completed live counterfactual PR #21 run was found in the inspected worktrees or external cue archives.

The `main` checkout has **15 untracked status paths, comprising 19 files**: `configs/anm-validation-01.json`; eight historical ANM/pilot planning and review Markdown files; `scripts/dsmlp-qwen.sh`; five `src/causalbridge/benchmark/validation/` Python files; and four matching tests. They concern the earlier ANM validation/pilot, not v3. Its ignored `runs/` contains the 17-pair pilot, ANM validation, and Track B smoke working records (182, 1,830 and 47 files respectively). The main report already points to tracked packages of the pilot and ANM validation; the untracked files supply historical context but no additional completed v3 study. No active checkout files were changed.

## V3 provenance and completeness

| Check | Independently observed evidence |
| --- | --- |
| Protocol and code | All three plans record `source_commit=7d4a408cc8fcb0b1238971c04141c0fd579a5a20` and protocol `diagnostic-investigation-v3`; 67 listed source hashes equal the committed Git blobs. V3's checker uses the single-decision output contract plus four strict boolean evidence flags and checks **structured diagnostic attribution**. It does not check causal truth, numeric citations, or unrestricted explanation prose. |
| Dataset | Full plan records 17 selected, already-opened pilot pairs and `eligibility.roster_counts` of 17 frozen pilot, 4 development, 38 validation, 49 unscorable; no documented untouched pool. The 170 case rows resolve to 17 case IDs and seven source groups. Frozen roster, original pilot archive, evaluator records, thinking-ablation archive and config hashes are in the plan's `source_sha256`. |
| Frozen requests | Five arms (`no_diagnostic`, `correct_plain`, `wrong_plain`, `correct_qualified`, `wrong_qualified`) × thinking off/on × 17 pairs. Full plan request digest `sha256:9d0fdbc5ecefd87da55d7fc4065304efe1fbc7b4ef9ee07385c26564bd754744`; evaluator digest `sha256:ed14a6d5aefa3c417b5ed98289c5e0735c27b15b3496139cd0f9ba7fa2bb8b35`. Diagnostic and preflight digests are separately archived. |
| Model/runtime | Recorded `qwen3:8b` digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`; temperature 0, seed 261, request order seed 20261121, `num_ctx=8192`, `num_predict=4096`, timeout 900 s. Both thinking settings have 85 full requests. Saved before/after model snapshots name the same digest and Ollama `0.40.17`; endpoint recorded as `http://127.0.0.1:11435`. Runtime versions in plan: Python 3.12.11, Pydantic 2.14.1, HTTPX 0.28.1. The snapshots and raw wrappers evidence the recorded endpoint/model, not cryptographic remote attestation. |
| Gate 1 | Four unique diagnostic requests, records and raw wrappers; 2 thinking on and 2 off; zero failures/rejections; `diagnostic_passed=true`. |
| Gate 2 | 20 unique preflight requests, records and raw wrappers; 10 on and 10 off; zero failures/rejections; `preflight_passed=true`. |
| Full run | 170 unique request IDs equal the 170 record IDs and 170 raw-file IDs. Every record's canonical request digest matches its saved payload; every canonical raw-wrapper digest matches its saved raw file. All raw HTTP statuses are 200 and model names `qwen3:8b`; 169 have `done_reason=stop`, one `done_reason=length`. No missing or duplicate scheduled cell was found. |
| Failure and checker categories | One `ValueError: incomplete_or_truncated` at `D1028`, `wrong_qualified`, thinking on, trial `sha256:e4783f40102025e1ce1637e51e5fbf5c43f8ff059138b75ef1438913678acbaa`. Three `missing_or_unavailable_diagnostic_citation` checker rejections: `D1045` and `D1046`, `correct_qualified`, thinking on, and `D1084`, `wrong_qualified`, thinking off. Their upstream outcomes are all abstentions. |
| Analysis binding | `case-results.json` has 170 unique trial IDs; its grouped correct/wrong/abstain/failure counts equal all 10 metrics cells. The full run summary reports 170 completed, 1 failure, 3 rejections. The archive verification record reports all request orders and raw replays passed. |

The raw-digest check uses the repository's canonical JSON representation (`json.dumps(..., sort_keys=True, separators=(',', ':'))`, with Python's default ASCII escaping). A preliminary non-ASCII JSON serialization check would falsely flag four responses; the source-compatible canonical check flags **zero** in all phases. This distinction matters because the saved raw response body contains Unicode text in some replies.

### Outcome table (before verification)

| Think | Arm | Correct | Wrong | Abstain | Failure | Checker rejected | Released directions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Off | no diagnostic | 0 | 0 | 17 | 0 | 0 | 0 |
| Off | correct plain | 16 | 1 | 0 | 0 | 0 | 17 |
| Off | wrong plain | 0 | 17 | 0 | 0 | 0 | 17 |
| Off | correct qualified | 9 | 1 | 7 | 0 | 0 | 10 |
| Off | wrong qualified | 2 | 13 | 2 | 0 | 1 | 15 |
| On | no diagnostic | 8 | 0 | 9 | 0 | 0 | 8 |
| On | correct plain | 17 | 0 | 0 | 0 | 0 | 17 |
| On | wrong plain | 6 | 11 | 0 | 0 | 0 | 17 |
| On | correct qualified | 15 | 0 | 2 | 0 | 2 | 15 |
| On | wrong qualified | 9 | 4 | 3 | 1 | 0 | 13 |

The no-cue condition has 0/17 directional outputs with thinking off and 8/17 with thinking on. Wrong plain cue yields 17/17 wrong answers with thinking off and 11/17 wrong with thinking on. Those large within-cohort contrasts are evidence of susceptibility to the **constructed direction-only cue under this prompt**. They do not estimate the accuracy of real ANM scores or show that the model recognizes when a diagnostic is wrong. The limitations statement changes abstention and correct-answer counts as well as wrong-answer counts; the archived report includes paired exploratory source-group bootstrap contrasts. The 170 calls share 17 real pairs, not 170 independent cases.

## Reproducibility and limits

The archive contains all three frozen plans/evaluators/requests, 194 raw wrappers and records, model snapshots, full case analysis, protocol config, selected source files, a bundle verification JSON, and a hash inventory. The remaining required source is available at committed `7d4a408`; all 67 plan source hashes matched that revision and the current v3 worktree. The original pilot ZIP and thinking-ablation archive referenced by the plan also match their recorded SHA-256 values in the checkout. Thus an **offline replay and reanalysis** is materially reproducible from the committed source plus this archive and its pinned input artifacts. This review independently checked identities, hashes and counts; it did not execute the repository's full replay program or regenerate bootstrap intervals. Reproducing the model's exact responses would additionally require the same model binary, Ollama runtime and inference environment, and may not be byte deterministic.

The archive is not committed, pushed, or independently replicated as far as the inspected locations show. A file manifest detects changes within the archive but does not establish a trusted creation time or independent server identity. Before the v3 result appears in a submission or shared paper, the team should make a stable, accessible copy of this exact archive/hash and cite it with its exploratory scope. That is a preservation recommendation, not a change performed here.

## Final submission and other archive checks

The committed `report/CausalBridge-final.md`, its rendered PDF, and `presentation/CausalBridge-final.pptx` discuss the original Track A/Track B/ANM experiments and do **not** state that v3 was unrun or report a v3 outcome. Their claims that the *submitted Track A and Track B runs* used thinking off remain scoped to those runs; v3 is a later distinct study using both settings. The 38-pair panel is correctly labeled exploratory with opened ANM labels, and its 11 model abstentions plus one binding failure are kept distinct. The three E4 checker suppressions described in the submission belong to the **38-pair integrated Track B study** and should not be confused with v3's three rejected upstream abstentions. No existing submission result needs numerical correction because of v3. If the submission is amended to include v3, add a separate protocol/results section and archive citation; do not retroactively blend v3 with E4.

Other final-evidence integrity checks performed without recomputation:

- Track A compressed raw trace SHA-256 is `f7637886005c2c3f56d7b60c8f3e6d4c856262434cdbec7474b38f6f60545813`, matching its committed report.
- Original 17-pair pilot ZIP SHA-256 is `b73b24c45268ac1bc61ae250a2a81aa97ecb6190b923aeafd92d033c340b3f8a`; its 412 ZIP members passed CRC validation.
- ANM experiment archive SHA-256 is `98808df804e302da385b796dc7c576b8d3a3dec24e8c69e600123751119ff3ba`; all 7,125 regular archive members matched the committed manifest's byte lengths and SHA-256 values.
- Integrated 38-pair resumed-live archive SHA-256 is `30c190e8f0e826277a53246507054a35ec9606885d30e17dc88ae896d84dc1c1`. The separate committed provenance audit says 304 scheduled responses, 51 saved-live replays, 253 new generations and three transport retries. Its archive was opened and listed, but this reconciliation did not independently replay its full 304-response journal.

## Corrections required to the branch lineage audit

1. Replace the executive verdict's implication that v3 is only an unrun protocol. Keep the Git ancestry conclusion, but add the completed **untracked** v3 run with its archive path, hash, 4/20/170 gate and full counts. State that the work is absent from Git, not absent from the local project.
2. Replace the v3 experiment-provenance row and the “no archived live v3 replies or full analysis” claim with the exact plan, raw response, analysis, manifest and verification paths above. Distinguish 194 total live gate/full calls from the 170 scientific cells.
3. Update the scientific consistency findings: v3 is exploratory on opened pilot cases and cannot be compared directly with historical E4 because its prompt, single-decision/boolean schema, budget, thinking conditions and constructed directional cue differ. Preserve one execution failure and three *overlapping abstention* checker rejections as distinct categories.
4. Update the branch/worktree inventory narrative: its v3 `dirty 10` entries are ten untracked tarballs; the completed v3 package is one of them. Main's 15 untracked status paths also coexist with ignored historical runs. Branch-tip and PR inventory remain correct; branch ancestry does not change.
5. State the remaining preservation gap: the completed result is locally hash-verifiable and offline-replayable but is not in the checked-in tree or a confirmed shared immutable store. Do not archive/delete the v3 worktree or its tarballs on the premise that it holds only prepared software.

## Commands used for this reconciliation

Read-only commands included `git status --short --untracked-files=all`, `git status --short --ignored`, `git worktree list --porcelain`, `find runs`, `rg`, `tarfile.open`, `zipfile.testzip`, `git show 7d4a408:<path>`, `sha256` of archive members and committed blobs, `pdftotext`, and `markitdown` on the PPTX. No live endpoint was contacted and no analysis output directory was created. Independent checks used the saved `requests.json`, per-trial `records/*.json`, `raw/*.json`, `case-results.json`, and `metrics.json`; all operations were read-only.
