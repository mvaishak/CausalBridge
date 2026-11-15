# Current project status

Updated 2026-11-15. This is the authoritative progress entry point. Older phase
notes retain their original evidence and test counts; they are historical snapshots.

## GitHub and validation

- Upstream main: `1dd84b4`, including merged PR #6 (native integration),
  PR #7 (Track A ten-group pilot) and PR #8 (smoke/checker fixes and review follow-up).
- [PR #9](https://github.com/mvaishak/CausalBridge/pull/9) is **open, ready for review**;
  implementation commit `bcad4a318c8715c085be64140bca4bf42bb0e4dd` is pushed on
  `codex/track-b-integration-acceptance`. It has not been merged.
- Implementation validation: **818 tests passed**, Ruff lint/format, both Track A
  demos, synthetic ANM handshake and wheel/sdist builds. PR #9 GitHub CI passed
  on Python 3.12 and 3.13. Documentation-only follow-ups do not imply new test runs.
- Final review added rejection of contradictory primary usability, binding and
  outcome states. No duplicate PR #8 production changes remain in PR #9.
- Account collaborator write access works. The earlier fork-only limitation is historical.

## Completed capability versus remaining research

| Area | Evidence-backed status | Remaining |
| --- | --- | --- |
| Track A tools/witnesses | Merged graph and numerical tools; independent rational/engine confirmation; 50 questions across ten graph groups | Human case review, live benchmark run and reporting |
| ANM | Merged KRR/HSIC implementation and saved original requests; successful and failure-path synthetic tests | Development calibration, method freeze and real-pair evaluation |
| Matched E1–E4 evidence | Merged selection, summaries, names/units visibility and A/B bindings | Accept audited real loader records and sanitized metadata |
| S0/S1, cached S2 | Merged native runner, persistence/resume, checker and independent artifact auditor | Frozen real-data execution; interpretation of natural model errors |
| Live transport | Two saved live Qwen3 8B smokes on synthetic observations; prompt/failure/provenance and numeric fixes merged in PR #8 | Real-pair readiness and final experimental settings |
| External boundaries | PR #9 validates runtime/evaluator separation, IDs, weights, within-batch group splits and scheduled exports | Faizah's actual adapter/schema acceptance; dataset-wide audit |
| Evaluator joins | PR #9 verifies both orientations, retained source digests, mapping IDs and exact S1 parents | Accept authentic reference metadata from data owner |
| Scorer acceptance | PR #9 has hand-calculated metrics, paired contrasts and fixed group-resample examples | Faizah's weighted scorer, bootstrap implementation and consumer acceptance |
| Pilot/held-out/report | Not completed | Real-data pilot, development decisions, freeze, held-out results and final outputs |

An artifact audit checks integrity and recorded handshake invariants. It does not
certify dataset eligibility, original labels, ANM assumptions or causal correctness.

## Integration-readiness phases

These are the recent readiness phases, distinct from the original roadmap's
implementation/pilot/held-out phase numbering.

| Phase | Status | Evidence |
| --- | --- | --- |
| 1 Live execution/verification fixes | Merged in PR #8, including review fixes | `docs/kris-smoke-v2.md`, `docs/kris-checker03.md` |
| 2 Saved-run replay | Completed; originals preserved | [Replay comparison](../kris-phase2-replay.md) |
| 3 Boundary acceptance | Implemented/tested in open PR #9 | [Handoff checks](../kris-phase3-handoff.md) |
| 4 A/B mapping and evaluator joins | Implemented/tested in open PR #9 | [Direction truth table and joins](../kris-phase4-evaluator-joins.md) |
| 5 Scoring acceptance fixtures | Implemented/tested in open PR #9 | [Metric/resample oracles](../kris-phase5-scoring-fixtures.md) |
| 6 Offline end-to-end acceptance | Implemented/tested in open PR #9 | [Pipeline acceptance](../kris-phase6-offline-acceptance.md) |
| 7 Review/publication/docs | Review complete; PR open; knowledge-bank cleanup recorded here | 818-test implementation validation and green CI; merge remains pending |

Phase-specific test counts document successive snapshots (689, 719, 759, 800).
The final reviewed implementation count is **818**; do not add those counts together.

## Live-smoke evidence

Both runs use synthetic observations, actual ANM and live pinned Qwen3 8B—not
Tübingen data or a research pilot. The model digest is
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.

| Bundle | Original observation | Checker-0.3 replay |
| --- | --- | --- |
| `runs/qwen3-8b-live-smoke-01` | Eight live calls; E2/S0 and E3/S0 truncated; S1 checks: three rejected, one E4 release | Outcomes unchanged |
| `runs/qwen3-8b-live-smoke-02-v2` | Eight live calls; E1–E3 S1 abstain; E4 originally rejected for rounding | E1–E3 remain abstentions; E4 releases A_to_B |

First-smoke E4 supplied no claims, so its pass does not establish checked support.
The second configuration uses 16 display rows, context 4096 and output cap 512;
it differs from the original configuration and is not a prompt-only comparison.
Historical native traces were never rewritten. Fresh-copy Phase 2 verification
reproduced both replays, passed native audits, kept original file hashes unchanged,
and verified zero new model/ANM calls and no events on repeated replay.
Local evidence is under `runs/phase2-checker03-verification/`.

## Offline scorer-input acceptance

`runs/phase6-offline-acceptance-final/report.json` records eight synthetic cases,
32 packages, **64 scripted attempts**, 32 S2 records (20 checks, 12 parent-failure
skips), and 136 private joined rows matching the scoring projection exactly.
Independent audit passes; cached S2/resume add zero calls. The tiny method samples
intentionally yield insufficient_rows/input_validation; this demo does not measure
successful ANM performance. Real successful ANM computation is covered elsewhere.

The 136-row scorer fixture uses four source families and eligible weight 16.
It explicitly distinguishes correct answers suppressed, wrong answers removed,
failures and abstentions. Fixed paired family draws include repeated groups and
undefined accuracy when no answers remain. These are deterministic acceptance
oracles, not estimated confidence intervals or natural error prevalence.

## Next actions and ownership

1. Review/merge PR #9 after team acceptance; no merge is assumed here.
2. Faizah supplies audited snapshot/hashes, eligibility/exclusions, sanitized
   runtime records and separate reference/weight/group/split metadata. Agree the
   concrete adapter fields; current evaluator cause_column shape is provisional.
3. Faizah's scorer passes the metric and fixed-resample fixtures. Our integration
   connects actual handoffs and validates one real pilot pair through scoring.
4. In parallel, Anish prepares/calibrates ANM on designated development groups;
   Vaishak/Kris validate final live settings; Arunima/Anish finalize Track A review
   and live execution. Do not use held-out groups for tuning.
5. Run the real-data pilot; inspect failures and costs; freeze eligibility, model,
   prompts, checker/tolerance, sampling, method, retry and metric/CI policies.
6. Execute held-out evaluation without retuning, then H1/H2/H3 comparisons, group
   uncertainty, representative errors, reproducibility package, report and slides.

No new live-model calls were made during the readiness implementation/cleanup.
