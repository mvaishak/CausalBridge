# PR #12 after the main integration

Follow-up: the user authorized closure as superseded. PR #12 was closed at
2026-11-19T20:37:30Z, mergedAt=null; no merge or branch deletion was performed.
The following paragraphs describe the initial review before that closure.

Checked 19 November 2026 against fetched main 7c7198d29f4f2e224963a2e24be778db1d81e4d7.
PR #10, #14 and #15 report merged. PR #12 remains open at
66126c2113d32a26f5b9f36e21f6ed46a40dc4d0 and targets codex/pilot-readiness,
not current main. Its GitHub comparison against main is diverged: four commits
ahead and nineteen behind. Old head CI is green, but does not validate a new
integration against current main.

Recommendation: treat #12 as superseded by the reviewed mapping/diagnosis work
now in main, rather than merge it as a new fix. Do not infer a missing fix from
its open status. No remote PR was merged, closed, edited or commented on here.

Evidence:

- Main verifies the mapping digest against case ID, exact column permutation and
  seed, then independently checks seeded orientation and evaluator source digest.
- The original #12 corruption regressions are retained in main's scorer tests.
  Focused scorer, lineage and new resource-accounting suites pass (56 tests).
- Main additionally validates a single manifest and exact cached S1 attempt,
  run, package and release lineage for S2/SIMPLE_GATE. The old #12 branch does
  not represent these later corrections.
- #12's scope grew beyond its title to include the older data-audit/diagnosis
  integration. Current main has the corrected versions. A two-tree diff is not
  a predicted merge result; this review does not claim Git would automatically
  delete every newer file. The issue is redundant/old scope, not a demonstrated
  missing mapping capability.

If maintainers want to retain the unique historical mapping-review document,
port that documentation separately after reconciling its old status statements.
Do not retarget or merge the old branch solely to close an open-PR counter.

This is a local review record; current remote state can change after this check.
