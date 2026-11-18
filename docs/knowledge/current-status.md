# Current project status

Updated 15 November 2026. Start here; older phase counts and publication notes are
historical snapshots. See the [project audit](../reviews/project-audit-2026-11-15.md)
for the assessment, confirmed finding and evidence limits.

## GitHub snapshot

| Work | State | Revision / validation |
| --- | --- | --- |
| Main, including PRs #6–#9 | Merged | `7085d2f`; PR #9 implementation passed 818 tests and CI |
| [PR #10: pilot/data/scorer](https://github.com/mvaishak/CausalBridge/pull/10) | Open | `a8ba5ba`; not merged into main |
| [PR #11: ANM-only compatibility/acceptance](https://github.com/mvaishak/CausalBridge/pull/11) | Open, ready for review | Implementation `80c4431`; 830 tests pass, one pilot-API module skipped on main; Python 3.12/3.13 CI passed |
| Combined main + PR #10 + compatibility fix | Tested in isolated checkout | 870 tests, lint/format, demos, ANM handshake and builds pass; not a merged GitHub revision |

The skipped actual-consumer module was exercised in the combined checkout.
Historical 639-test ANM validation and other milestone counts refer to different
source trees; they are not directly comparable as progress percentages.

## Immediate audit finding

**PR #10 scorer mapping integrity remains open.** Reversing D0201's external
column order while retaining its mapping ID, source digest and every analysis
row changes synthetic E4/S1 accuracy from 62.5% to 37.5% without rejection.
The actual scorer checks matching ID strings but not the order/seed bound by the
ID or the independently retained selection receipt. Our strict evaluator join
checks that binding, but the pilot scorer entry point does not use it.

This is not evidence that the reported real pilot was scored incorrectly.
It is a confirmed acceptance gap: add strict mapping validation and a corruption
regression before closing that handoff. PR #11's ANM status fix is separate.
No production fix for this newly found issue was made in the project audit.

## Where the project stands

| Area | Completed evidence | Remaining |
| --- | --- | --- |
| Track A | Merged graph/numerical tools, exact witnesses, independent rational/engine checks, 50 questions across ten groups | Human case review and live final benchmark |
| Track B E1–E4 | Matched samples, summaries/context controls, seeded A/B mapping and private/runtime separation | Accept actual source metadata and final preprocessing choices |
| Runner/cache/audit | Durable attempts, failed-response metadata, recovery, zero-call S2/resume and artifact checks | Saved real-pilot artifact reconciliation and frozen final execution |
| Evidence checker | Typed claim/binding checks, finite numeric tolerance and strict nonnumeric identities | Quantify real rejection validity/cost; no general prose or causal-truth guarantee |
| Loader/scorer | Actual APIs exist on PR #10; loader fixture and weighted metric targets pass | Mapping-integrity fix, real artifact audit, owner acceptance and group-bootstrap implementation |
| Our compatibility work | PR #11 accepts not_applicable only for ANM_ONLY; tests and report published | Team review/merge with PR #10 |
| ANM numerical fidelity | Uploaded independent report/code review support 192 comparisons and 96 swap checks | Original validation source/raw run not reproduced from this checkout |
| ANM statistical reliability | Frozen n=128 progression gate **failed** | Separately specified development work or explicit revised research premise |
| Pilot/held-out | Real pilot reported; synthetic and live infrastructure evidence exists | Independently rescore saved pilot, development decisions, freeze and untouched evaluation |

Overall: strong software foundation, preliminary checker evidence, weak current
support for improved causal direction. A transparent negative result is useful;
claims of reliable ANM assistance or causal-truth verification are unsupported.

## Recent readiness work

1. Live execution/prompt/failure/numeric fixes merged in PR #8.
2. Saved synthetic live-smoke predictions replayed under checker 0.3 without new
   calls or rewriting originals; second-smoke E4 rounding rejection becomes release.
3. Runtime/evaluator and scheduled-export boundary checks merged in PR #9.
4. Four-case A/B reference truth table and strict private joins merged in PR #9.
5. Hand-calculated scoring and fixed paired group-resample fixtures merged in PR #9.
6. Native synthetic pipeline reproduces all 136 fixture rows; merged in PR #9.
7. Initial real-loader/scorer compatibility checks published in PR #11. Broader
   audit reopens scorer mapping acceptance; raw pilot audit remains pending.

These readiness phases are distinct from original roadmap pilot/held-out phases.
See [handoff checks](../kris-phase3-handoff.md), [joins](../kris-phase4-evaluator-joins.md),
[scorer fixtures](../kris-phase5-scoring-fixtures.md),
[offline demo](../kris-phase6-offline-acceptance.md), and
[actual API acceptance](../reviews/pilot-integration-acceptance.md).

## Experiment evidence and provenance

- Two saved Qwen3 8B live smokes on synthetic observations: eight calls each;
  cached S2/resume add zero. Historical first-smoke truncation is preserved.
  Replay evidence is described in [Phase 2](../kris-phase2-replay.md).
- Synthetic scorer-input demo: eight cases, four families, 64 scripted attempts,
  32 S2 records (20 checks/12 parent-failure skips), 136 rows and passing audit.
  Three-row method inputs intentionally exercise insufficient_rows; other tests
  cover successful ANM fitting. No live calls occur in acceptance tests.
- Real pilot, reported by user and PR #10 guide: 17 pairs/seven groups, 136 live
  generations, 68 cached S2 checks, zero execution/ANM errors, passing audit and
  zero-call resume. E4 S1/S2/ANM arrows match, with 14 answers (six correct/eight
  wrong) and three abstentions; weighted coverage about 89%, accuracy 40%.
  Five non-E4 rejections and prose/arrow contradictions are reported. The raw
  real-pilot/prepared bundles are absent from both available checkouts, so these
  outcomes have **not** been independently reconciled here.
- Uploaded ANM validation/decision/code-review reports were read directly. They
  distinguish 32 compatible recovery cases from 36 construction-direction-scored
  cases and 48 operational datasets; 12 controls are not direction-identifiable.
  Reported numerical maximum discrepancy is about 9.68e-16. Locked recovery 65.6%,
  stability 68.8% and minimum-family recovery 25% miss the frozen gates. The
  original 48-dataset run and validation source are not available locally for
  fresh execution; report review is not a rerun. No specific repair is established.

No audit pass or hash chain certifies causal truth, authentic source labels or
statistical ANM assumptions. Split/orientation repeats are not independent cases.

## Next actions and responsibility

1. Pilot scorer owner closes mapping validation and regression-tests changed
   order with unchanged ID. Kris verifies the repaired integration.
2. Make original real-pilot journal/manifests/exports/method files and prepared
   runtime/evaluator/mapping records available; independently audit and rescore.
3. Review and merge PRs #10/#11 in a checked combination; neither merge is assumed.
4. Anish/data owners specify, version and validate ANM/preprocessing development
   changes. Preserve original results and freeze source-separated evaluation groups.
5. Agree final prompts/model/checker/sampling/retries, process-error definitions,
   weighted metrics and interval policy; validate the revised handoff and freeze.
6. Run held-out evaluation and Track A live benchmark, then comparisons, figures,
   error cases, reproducibility artifacts, report and presentation.

Kris's implementation is substantially finished. Remaining ownership is integration
acceptance, final configuration and audited execution—not independently repairing
ANM statistics or taking over the data owner's audit. No new live runs or threshold
changes were made for this review.
