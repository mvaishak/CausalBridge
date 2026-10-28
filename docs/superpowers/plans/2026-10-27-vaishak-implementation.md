# Vaishak Workstream C Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** A runnable, independently testable LLM orchestrator and causal verifier.

**Architecture:** Typed visible evidence enters a strict boundary. A replaceable
model parses and plans; a replaceable backend runs tools; contracts check binding,
capability, evidence, and conclusion. Templates release only checked conclusions.

**Tech Stack:** Python 3.12, Pydantic 2, NetworkX, httpx, pytest, uv, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-27-vaishak-design.md`

## Global Constraints

- Runtime never sees hidden parameters, reference labels or witness models.
- Fully observed binary DAGs with independent noise and positivity.
- Absolute numeric tolerance 0.001; independent sign tolerance 1e-9.
- No benchmark generation, scoring, training, discovery or counterfactuals.
- Local branch in the supplied empty repository; no remote publication.

## Review Focus

- Extra metadata and nested hidden fields must not enter prompts or tools (Task 1).
- Reversed contrasts and bool/numeric confusion must not verify (Tasks 1–2).
- Stale tool results and changed final plans must fail binding (Tasks 2–3).
- Observational substitution with confounding/colliders must fail (Task 2).
- Model outages, malformed JSON, unsupported intent must produce logged abstentions (Task 3).

### Task 1: Shared visible-only schemas

Files: `src/causalbridge/schemas.py`, `tests/test_schemas.py`, package configuration.
Produces: RuntimeCase.from_benchmark(dict), Query, Proposal, ToolRequest,
ToolResult, Verdict; complete model validation and deterministic evidence digest.

- [x] Write tests for leakage projection, invalid DAGs/CPTs, roles and strict values.
- [x] Run `uv run pytest tests/test_schemas.py`; expect missing implementation.
- [x] Implement schemas and runtime projection; forbid extras and nonfinite values.
- [x] Run schema tests; expect all pass.

### Task 2: Planner, tools and verifier contracts

Files: `llm/tool_planner.py`, `tools/protocol.py`, `tools/reference.py`,
`verifier/contracts.py`, `tests/test_contracts.py`, `tests/test_reference.py`.
Consumes Task 1 types. Produces plan_request(query, proposal, case),
check_preconditions(request, case), verify(query, proposal, request, result, case),
ToolBackend.execute(request, case). ReferenceBackend is development-only.

- [x] Write hand-computed tests for +0.4, graph-only abstention, path/sign mismatch,
  no-path zero, confounding, valid adjustment, mediation, reversed contrast,
  execution failure, incorrect answers and stale result provenance.
- [x] Run focused tests and observe missing modules/functions.
- [x] Implement capabilities, general evidence contracts and reference adapter.
- [x] Run full suite; expect all pass.

### Task 3: LLM lifecycle, runnable CLI and reproducibility

Files: `llm/parser.py`, `llm/client.py`, `pipeline.py`, `cli.py`, `demo.py`,
`tests/test_pipeline.py`, `tests/test_client.py`, examples/configs/scripts/docs/CI.
Consumes Tasks 1–2 interfaces. Produces CausalBridge.run(case, query=None),
OllamaModel.generate(messages, schema), JSONL traces and exported JSON schemas.

- [x] Write lifecycle tests: tool-informed final answer, changed plan, malformed JSON,
  model/backend outage, leakage exclusion, trace completeness and CLI smoke runs.
- [x] Run tests and observe missing implementation.
- [x] Implement model adapter, bounded parser, orchestration, CLI and fixture demo.
- [x] Run full tests, lint, build, demo, editable install and schema export.
- [x] Write README, integration API, assumption record and model setup instructions.
- [x] Review whole implementation; fix material findings with regression tests.
- [x] Commit tested work on `codex/vaishak-verifier`.
