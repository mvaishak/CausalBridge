# Pilot integration acceptance

Checked 2026-11-15. Main is `7085d2f` (merged PR #9). The pilot API under review
is open PR #10, `a8ba5badeb74d8a143cc46ee3239bf4e7a58c6e4`.

## Verdict

**Fixture-backed code integration passes after one small compatibility fix.**
**Saved real-pilot result reconciliation remains blocked by absent artifacts.**
No live model requests, threshold changes, production method changes, or edits to
historical pilot predictions were made. PR #10 was not merged into the main
checkout. Its code was combined with main in an isolated detached worktree;
a documentation-only merge conflict was resolved there for test execution.

## Confirmed checks

- Actual loader accepts a hashed source-format fixture, preserves original column
  order and correctly reads second-column-to-first reference orientation.
- Its private record fields adapt explicitly to our evaluator boundary; no fields
  are silently discarded from runtime records. Weight 0.5 and the original source
  digest round-trip. Private description/reference sentinels stay out of actual
  E1–E4 model messages. This is a loader-format test, not a real snapshot audit.
- Actual pilot scorer reproduces every hand-calculated metric target across all
  17 package/condition cells from the native 136-row execution/export/join path.
- All three fixed paired family draws reproduce expected weighted totals and
  metrics, including repeated families and undefined zero-answer accuracy. This
  tests scorer arithmetic under resampling, not an implemented bootstrap interval.
- Missing/duplicate rows, wrong mapping/source identities and invalid reference
  directions are rejected by the actual scorer.
- The native acceptance run independently audits successfully: 64 scripted
  attempts, 32 S2 records and zero additional S2/resume calls. Parent binding,
  both A/B orientations and complete failure accounting pass their existing tests.

## Concrete compatibility issue and fix

The pilot exporter correctly sets ANM_ONLY generation_status=not_applicable,
because ANM is not an LLM generation. The PR #9 AnalysisHandoff allowed only
complete/truncated/incomplete/unavailable and therefore rejected valid pilot
exports. Its enum now accepts not_applicable **only for ANM_ONLY**. Twelve
parameterized acceptance regressions verify method acceptance and model rejection.
No pilot exporter or scientific settings were changed.

The explicit evaluator adapter converts first_to_second/second_to_first to
cause_column=0/1. It also verifies existing source digests through retained
RuntimePairs and mapping exports; it does not treat reference text as an A/B arrow.

## Validation evidence

- Initial combined checks reproduced the not_applicable schema incompatibility.
- After the fix, 208 targeted existing loader/scorer/boundary/join/pipeline checks pass.
- Ten additional actual-consumer tests pass.
- Complete combined-tree scripts/check.sh: **870 tests pass**, Ruff lint/format,
  both demos, successful synthetic ANM handshake and wheel/sdist builds.
- These are local combined-tree results, not a claim that main alone has 870
  tests or that the saved live pilot has been audited by this review.

Persistent local synthetic evidence is in runs/pilot-handoff-acceptance/, notably
report.json, audit.json, actual-scorer-input.json and actual-scorer-results.json.
The acceptance test skips explicitly when the unmerged pilot APIs are absent.
The compatibility fix and tests are published separately on
codex/pilot-handoff-acceptance. The actual-consumer module explicitly skips
on main until the pilot APIs arrive; the combined-tree checks above exercised it.

## Remaining artifact gate

Neither available checkout contains runs/real-pilot-01 or its prepared original
runtime/evaluator records. The full pilot artifact audit cannot be substituted
by the guide's reported totals or by this synthetic fixture run.

To finish, make available the original pilot bundle (journal, manifests, exports,
method request/result files and saved summaries/scores), together with the exact
prepared runtime/evaluator/mapping records and frozen preparation manifest. Method
artifact paths referenced by the journal must resolve read-only, or their original
bytes must be accessible through an explicitly audited relocation strategy.

Then independently verify the saved journal/S1–S2 links and mapping joins,
recompute every package/condition score and reconcile all scheduled cases with
the reported 17 pairs, seven groups, 136 generations and 68 cached S2 outcomes.
Do not regenerate predictions, silently rewrite paths/hashes, retune thresholds,
or treat the reported 89.0%/40.0% as independently confirmed until that gate passes.
