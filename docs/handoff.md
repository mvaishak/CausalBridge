# Team handoff checklist

## Engineering/accounting pass — 2026-11-20

Based on final-delivery commit d773118, isolated from report/presentation work.
Completeness checks now reject missing/duplicate trial identities and metadata;
resumed provenance checks durable generation/request equality. Outcome accounting
keeps upstream abstentions, binding failures and checker suppressions separate.
E4/S1 on the opened 38-pair panel has 11 model abstentions plus one binding
failure, not 12 genuine model abstentions; existing coverage/yield are unchanged.
`python scripts/reproduce_saved_results.py --output /fresh/path` uses tracked
archives only and regenerates saved analyses without inference or ANM refits.
Report, slides, original traces, method settings and scientific scores are unchanged.
Verification: isolated full suite 1,013 passed, two snapshot-dependent skips;
18 new regression checks pass. Archived analyses reproduce identically, with zero
HTTP/generation/ANM-execution/numerical-solve calls under guarded replay. Access
was restored and the verified patch applied to codex/final-accounting-checks.
No new held-out evaluation is claimed; report and presentation remain unchanged.

## Real validation outcomes opened — 2026-11-18

The user explicitly authorized one fixed descriptive test on all 38 assigned real
validation pairs. Up-to-512-row ANM at the existing gamma/alpha/threshold and fixed
three splits made 114 attempts without execution errors. Primary results are
13 correct, 13 wrong and 12 abstentions: 50.0% unweighted / 48.1% weighted answered
accuracy. No parameter or split was chosen from those results. Original roster
roles are preserved, but these pairs are no longer untouched. Future changes
informed by their outcomes require fresh held-out assessment. See
[anm_validation_results.md](anm_validation_results.md).

## Latest ANM evidence — 2026-11-18

A fixed 88-dataset synthetic panel now demonstrates success under tested compatible
conditions: the primary 512-row confirmation endpoint has 26 correct, zero wrong,
six abstentions, passing the predeclared demonstration gate. All families and
controls remain reported. This does not establish real-data reliability: a larger
sample on the four real development pairs gives one correct primary answer but
zero answered accuracy on the other splits. No real validation case is used.
See [anm_synthetic_panel.md](anm_synthetic_panel.md) for full results and limits.

## Current Anish development handoff — 2026-11-18

The four-chunk ANM study workflow is implemented locally, with PR #14 `a29dc4b`
as a dependency on `codex/anish-anm-baseline-reproduction`. Existing
replay changes are preserved. Faizah's real-data handoff is available and verified;
it is no longer a prerequisite blocking development.

The development study ran on pairs 12/17/93/99: six fixed variants, three splits,
72 numerical attempts and 24 baseline controls. Primary answered accuracy is zero
for every variant. No candidate was selected and all 38 validation cases remain
unused by ANM. Code supports explicit criteria, candidate freeze and one validation
run per freeze; that path is tested on synthetic fixtures only. See
[anm_development.md](anm_development.md) for commands, limitations and next work.

A targeted permutation-adequacy follow-up is also complete. It still has zero
correct development answers across all three split seeds, despite abstaining
more. It is not a production replacement. The user has authorized committing
this work; no real candidate is frozen and no real validation case was fitted.

The missing original 48-dataset synthetic validation bundle is needed only to
reproduce that earlier report exactly. No model server/live-pilot artifacts are
required for ANM-only development. Do not retune using the 17 frozen pilot pairs.

## Anish: numerical engine and ANM request producer

Implemented locally from merged main `48d6cda` on `codex/anish-anm-provenance`
in the fresh `CausalBridge-Anish` clone. Anish has authorized committing and
pushing this feature branch; PR creation and merge remain separate steps.

- Track A `CausalEngineBackend` and reusable numerical functions preserve the
  reference backend and graph/witness code. Select with `--backend engine`.
- Independent rational tests confirm all merged small-pilot numeric labels and
  the same-P(X,Y), +0.30/-0.30 witness. Historical oracle tags are left intact.
- `save_anm_request` writes actual sample/config/split bindings and standalone
  `request.json` before any numerical execution. It never derives a request from
  returned provenance. `execute_anm_request` produces existing ANMResult objects.
- `load_anm_artifacts` resolves/checks reproducibility records and originals;
  the existing verifier consumes its saved request as context.method_request.
- `examples/anm_integration.py` demonstrates computed synthetic ANM, a scripted S1
  prediction and deterministic S2, with separately saved receipts and no new S2 calls.

See [producer/API guide](anm_producer.md), [verification](verification.md), and the
authoritative [Track B contract](track_b_integration_contract.md).

Outstanding: real eligible samples and source-group development evaluation,
matched E1-E4 packages, actual S0/S1 runner/cache, a frozen tau, and live model runs.
No numerical score here is a causal probability or proof. Do not reconstruct a
missing request from a result. Create a fresh directory for a retry.

## Vaishak: original orchestration handoff

## What you can demonstrate now

Run `uv run causalbridge demo --output runs/demo.jsonl`. Open the JSONL to inspect
the parsed query, selected tool, tool result and verdict for each fixture.

The paired toy cases keep the question and graph fixed. Complete CPTs support
+0.4; the graph-only case abstains. A deliberately wrong tool choice receives
`wrong_operation`. No-path zero and valid backdoor adjustment show that the verifier
can also accept useful answers.

## Roadmap deliverables

| Deliverable | Implementation |
| --- | --- |
| Structured query parser | `src/causalbridge/llm/parser.py`, `schemas.Query` |
| Tool planner | `src/causalbridge/llm/tool_planner.py` |
| Verification contracts | `src/causalbridge/verifier/contracts.py` |
| LLM orchestration | `src/causalbridge/pipeline.py`, `llm/client.py` |
| General operation requirements | `check_preconditions`, capability checks and conclusion checks |
| Accept computed effect; reject path-to-sign claim | `tests/test_contracts.py`, fixture demo |
| Work independently of Anish | `ToolBackend` protocol, reference adapter and hand-computed fixtures |
| Integration with Kris | Importable `CausalBridge.run`, versioned schemas and JSONL traces |

## Team integration steps

1. Review `schemas/` with Anish and Arunima. Confirm parent ordering, visibility,
   binary treatment convention, adjustment-set representation and assumption flags.
2. Anish's adapter is now selectable, with shared fixture parity and independent
   numerical controls. Retain the reference default until the team changes it.
3. Start the chosen model server. Run `examples/runtime_cases.jsonl` and inspect
   every parsed query, raw JSON reply, token count and failure stage.
4. Give Kris the pipeline entry point and `RunTrace` contract. Keep A–E data and
   generation budgets comparable. Agree how multi-call token budgets are matched.
5. Give Faizah example traces and reason-code meanings. Separate parse failures,
   wrong operations, inconsistent conclusions and model abstentions in analysis.
6. Use development cases to settle prompts and tolerances, then freeze code,
   prompt version, lockfile and model artifact before any held-out evaluation.

## Before calling the whole project complete

The numerical engine and independent pilot/witness checks are implemented. The
team still needs full benchmark validation, real-data/live-model runs, matched
baselines, group-level uncertainty estimates, scoring audits and the report.

## ANM baseline follow-up — 2026-11-17

Anish's local feature branch `codex/anish-anm-baseline-reproduction` adds saved
attempt verification and optional production replay. Commands and exact scope:
[anm_producer.md](anm_producer.md#saved-baseline-verification-and-production-replay--2026-11-17).
Seventeen retained scripted-pilot ANM attempts replay consistently; this does not
reproduce the independent study's 48-dataset scientific gate or improve the method.

Required handoff from the validation-bundle holder (coordinate with Faizah): the
exact frozen validation source/configuration, seed manifest, original datasets,
truth/scorability records, saved attempts, and reproduction commands described by
the three external validation reports. These files are not present on any fetched
remote branch. Agree development/untouched validation cases and pass criteria
before tuning. No full production scorer or live-model run is needed to begin
that numerical work. Preserve historical artifacts and use fresh output paths.
