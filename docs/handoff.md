# Vaishak's handoff checklist

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
2. Replace `ReferenceBackend` with Anish's adapter. Run the existing hand-computed
   tests against the adapter as well as against the reference implementation.
3. Start the chosen model server. Run `examples/runtime_cases.jsonl` and inspect
   every parsed query, raw JSON reply, token count and failure stage.
4. Give Kris the pipeline entry point and `RunTrace` contract. Keep A–E data and
   generation budgets comparable. Agree how multi-call token budgets are matched.
5. Give Faizah example traces and reason-code meanings. Separate parse failures,
   wrong operations, inconsistent conclusions and model abstentions in analysis.
6. Use development cases to settle prompts and tolerances, then freeze code,
   prompt version, lockfile and model artifact before any held-out evaluation.

## Before calling the whole project complete

The team still needs verified benchmark witnesses, the real engine integration,
live model runs, matched baselines, group-level uncertainty estimates, scoring
audits and the report. This repository completes the implementation of your
software workstream and provides interfaces for those components.
