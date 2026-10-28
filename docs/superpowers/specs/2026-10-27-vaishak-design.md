# Vaishak's CausalBridge workstream

Implement Workstream C from the supplied roadmap, consistent with sections 3–4 of
the proposal and the original idea. The request explicitly delegates assumptions
and asks for implementation from start to end; proceed without a design approval
round. Source documents supply requirements, not authorization to execute their
meeting, messaging, or issue-creation suggestions.

## Boundaries

Own structured parsing, planning, operation contracts, evidence gates, conclusion
consistency, response templates, and an importable orchestration API. Supply a tiny
development reference tool adapter and scripted demo, not the team's benchmark,
witness generator, A–E experiment runner, scoring, or claimed research results.
The original proposal takes priority on scientific assumptions; the roadmap assigns
Vaishak Workstream C. No training, discovery, individual counterfactuals, hidden
confounding, or conditional effects in v1.

## Assumptions chosen for this implementation

- Python 3.12, Pydantic 2, NetworkX; uv lockfile and CI.
- Correct fully observed binary DAG, independent noise, positivity. Explicit
  assumption flags are required for numerical causal conclusions.
- Finite contracts: reachability, no-path zero total effect, effect contrast,
  intervention probability, backdoor validity and backdoor adjustment.
- Effect is E[Y | do(X=to_value)] - E[Y | do(X=from_value)]; decreasing treatment
  reverses the contrast. Probability requests have a separate intervention value.
- Values use absolute tolerance 0.001, signs use a distinct 1e-9 zero tolerance;
  these are configurable and recorded, not tuned on held-out data.
- Numerical inference initially requires all visible CPTs, conservatively. Anish
  may later support sufficient partial factorizations through an explicit contract.
- An observational joint over X,Y,Z is sufficient for adjustment only when Z
  passes the backdoor criterion; Z may be empty for unconfounded substitution.
- Strict runtime allowlist excludes answerability, gold answers, witnesses, hidden
  CPTs and target values. Dataset ingestion projects only permitted fields.
- Tool responses bind to exact request and evidence digest. The trusted backend
  must compute correctly from supplied visible evidence; a digest is bookkeeping,
  not proof of numerical correctness or a defense against a malicious backend.
- Parse, plan, execute, interpret, verify; the LLM can propose unsupported answers
  but only verified answers are released. Invalid JSON is logged as execution error.
- Optional explicit public query specs bind roles independently of the candidate.
  The default LLM parser is not independent proof of natural-language semantics;
  parsing audits remain necessary.
- Ollama structured JSON is the default live model adapter for qwen2.5:3b, with
  HTTP endpoint, timeout, generation budget and seed configurable. No weights are
  downloaded automatically. Offline scripted outputs are labeled fixtures.

## Runtime API

RuntimeCase -> Query -> Proposal -> ToolRequest -> ToolResult -> Verdict.
ToolBackend.execute(request, case) and JSONModel.generate(messages, schema) are
replaceable protocols. The verifier never loads files or calls the benchmark oracle.
Verdict status is verified, unsupported, wrong_operation, or execution_error;
response action is answer or abstain, separate from status. Model abstention does
not prove insufficient evidence and carries a distinct reason code.

## Acceptance

The same X→Y direction query abstains without CPTs and verifies +0.4 with CPTs.
Reachability=true cannot justify positive effect; reachability=false permits zero.
Reject incorrect roles, reversed interventions, invalid adjustment, incomplete CPTs,
wrong numeric conclusions, stale tool results, malformed JSON and unsupported tasks.
Show hand-computed confounded adjustment, disconnected nodes and mediation.
Provide reusable JSON schemas, CLI, JSONL traces, integration guide, tests, CI,
and an honest distinction between fixture testing and live model validation.
