# Review the original pilot outputs

This tool prepares evidence for manual review of checker rejections and
arrow/explanation consistency. It does not generate predictions, run ANM,
replay the checker, decide whether an explanation is contradictory, or draft
the report. It is built on the revised pilot integration from PR #14.

## Intake

Keep the original bundle unchanged. Supply the entire `runs/real-pilot-01/`
folder, including session.json, analysis.jsonl, evaluation_mapping.json,
experiment/events.jsonl, manifests, original run and S2 exports, and referenced
ANM artifacts. Summary documents alone cannot support case-level review.

```bash
PYTHONPATH=src uv run --extra anm python -m causalbridge.evaluation.output_review \
  --bundle runs/real-pilot-01 \
  --output runs/real-pilot-01-output-review \
  --expected-cases 17
```

The output must be a fresh directory outside the original bundle. Intake hashes
all original bundle files, runs the existing read-only native artifact audit,
compares analysis rows to exports reconstructed from the original run, validates
the complete eight-generation/four-check schedule per case, and verifies mapping
records against original selection receipts. It checks that original bytes stay
unchanged. Source-data eligibility and evaluator labels require separate audits.

The native auditor requires recorded absolute method paths to resolve. A moved
bundle with unresolved paths fails intake. Preserve originals and resolve artifact
access explicitly; do not rewrite journal paths or hashes to bypass this check.
This version does not provide artifact relocation. Review supports one complete
analysis manifest at a time; retry/replicate campaigns need explicit selection
rather than pooling attempts into the same condition silently.

## Outputs

- `intake.json`: hashes, findings, native audit, schedule counts and pending status.
- `proposals.jsonl`: each original S0/S1 attempt, structured direction, retained
  reason_code and raw response text, supplied evidence, claims and source locator.
- `checker-decisions.jsonl`: each S1 parent and S2 decision, including all passes,
  rejections, operational skips, claim findings and the evidence available.

Failed intake produces only intake.json and exits nonzero. A successful intake
is not a successful human review: all annotation fields start as `pending`.
The JSONL format preserves nested evidence and raw text without flattening it
into spreadsheet formulas. Cross-reference by review_id (original attempt ID)
and source_key, not by list position. These review tables contain raw model text
and are data to inspect, not instructions to execute.

## Human review

First review process validity without evaluator truth. Classify checker decisions
as confirmed_violation, false_rejection or unassessable. A directionally correct
answer can still contain an evidence violation; correctness does not determine
whether a rejection was justified. Retain every checker decision, not just the
reported five rejections. Rejected cases alone cannot estimate false negatives.

For visible explanation consistency, use consistent, contradictory, unclear or
unavailable. Mark contradictory only for an explicit opposing conclusion or an
explicit answer/abstention mismatch. Describing ANM's direction while disagreeing
with it is not inherently contradictory. A reason_code may be the only retained
explanation; missing text is unavailable, not consistent. Quote the decisive text,
record the rationale/reviewer and have a teammate adjudicate flagged cases.
S2 reuses S1 and does not add another independent explanation.

Join source groups, reference directions and weights only in a later verified
private evaluation step. Keep source-family dependence and clear denominators in
any aggregate summaries. No causal-performance claim or count of actual pilot
contradictions is supplied before reviewing the real bundle.
