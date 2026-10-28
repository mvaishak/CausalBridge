# Integrating Workstream C

## Shared runtime format

The generated files in `schemas/` are the machine-readable interface contract,
version `1.0`. The team should review this proposed format together before merging
it into the shared repository.

```json
{
  "schema_version": "1.0",
  "case_id": "G001_sign_complete",
  "graph_group_id": "G001",
  "graph_nodes": ["X", "Y"],
  "graph_edges": [["X", "Y"]],
  "question": "Does increasing X increase Y?",
  "evidence_level": "complete_cpts",
  "visible_cpts": [
    {"node": "X", "parents": [], "p_one": {"": 0.5}},
    {"node": "Y", "parents": ["X"], "p_one": {"0": 0.3, "1": 0.7}}
  ],
  "assumptions": {
    "correct_dag": true,
    "fully_observed": true,
    "independent_noise": true,
    "positivity": true
  }
}
```

Every variable is binary. `p_one` gives P(node=1 | parents), with bit strings in
the listed parent order. A root uses `""`. Include every parent assignment in each
table, with probabilities strictly between 0 and 1. The benchmark's tighter
[0.1,0.9] generation range belongs to the benchmark producer.

Partial collections of complete node tables are representable. The v1 numerical
contract conservatively requires a table for every graph node, except for a
graph-supported zero total effect. `evidence_level` is descriptive metadata;
contracts inspect the actual supplied evidence.

For observational adjustment, supply `visible_joint`:

```json
{
  "variables": ["Z", "X", "Y"],
  "probabilities": {
    "000": 0.36, "001": 0.04, "010": 0.06, "011": 0.04,
    "100": 0.05, "101": 0.05, "110": 0.08, "111": 0.32
  }
}
```

Keys follow `variables` order. Every cell must be positive; cells sum to 1 within
1e-9. Additional observed variables can be marginalized. For Z → X, Z → Y, X → Y,
adjusting for Z gives 0.6, while P(Y=1 | X=1) is 0.72.

Explicit `graph_nodes` preserve isolated variables. The benchmark projection can
derive nodes from edges as a convenience, but that loses isolated nodes; benchmark
producers should always send `graph_nodes`.

## Calling the pipeline

```python
from causalbridge.llm.client import OllamaModel
from causalbridge.pipeline import CausalBridge
from causalbridge.schemas import RuntimeCase
from causalbridge.tools.reference import ReferenceBackend

case = RuntimeCase.from_benchmark(benchmark_row)
bridge = CausalBridge(OllamaModel(), ReferenceBackend())
trace = bridge.run(case)
print(trace.verdict.model_dump())
```

`RuntimeCase(...)` rejects unexpected fields. `from_benchmark` deliberately selects
only visible fields and drops `answerable`, `gold_response`, `target_value`,
witness IDs and hidden parameters. Nested unexpected evidence fields still fail
validation. Producers remain responsible for marking visibility correctly.

When a separate public query specification is available, use
`bridge.run(case, query=Query(...))`. The trace records `query_source=public_query_spec`.
Default parsing uses `query_source=llm_parser`. Keep these experimental settings
separate. Query specs bind variables and roles; they contain no answer labels.

## Anish: replace the development backend

Implement the protocol in `tools/protocol.py`:

```python
from causalbridge.schemas import RuntimeCase, ToolRequest, ToolResult


class AnishBackend:
    def execute(self, request: ToolRequest, case: RuntimeCase) -> ToolResult:
        # Call your deterministic engine using ONLY case's visible evidence.
        value = your_engine(request.operation, request.query, case)
        return ToolResult(request=request, value=value)
```

Pass `AnishBackend()` to `CausalBridge`. Return the exact request in the result.
Return a Python `bool` for structural operations, a finite Python `float` for
numeric operations, and `ToolResult(request=request, error="...")` for failures.
Convert NumPy scalars before returning them. There's no implicit retry or fallback.

| Operation | Query arguments | Output | Evidence requirement |
| --- | --- | --- | --- |
| `has_directed_path` | cause, outcome | bool | supplied DAG |
| `is_valid_adjustment_set` | cause, outcome, adjustment_set | bool | supplied DAG |
| `compute_effect` | cause, outcome, from_value, to_value | float in [-1,1] | assumptions and complete visible CPTs; no-path zero is an exception |
| `compute_intervention` | cause, outcome, intervention_value | float in [0,1] | assumptions and complete visible CPTs |
| `backdoor_adjustment` | cause, outcome, intervention_value, adjustment_set | float in [0,1] | assumptions, valid set and visible joint over X,Y,Z |

The effect convention is P(Y=1 | do(X=to_value)) minus
P(Y=1 | do(X=from_value)). An intervention query always asks about outcome value 1.
Conditioning, multi-valued treatments, multiple simultaneous interventions and
individual counterfactuals are outside this schema.

`requested_operation` expresses the question's required quantity.
`proposed_tool` records the model's selected tool. They remain separate so the
verifier can detect the roadmap's compute-effect versus reachability mismatch.
Backdoor adjustment is an accepted alternative to direct intervention computation.

The reference adapter implements exact enumeration and the backdoor criterion so
you can exercise all contracts locally. Replace it for the shared engine. Call
`check_preconditions(request, case)` in a standalone adapter as well as at the
pipeline boundary. The verifier repeats its own checks.

## Kris: consume traces in the experiment runner

Use `CausalBridge.run` for condition D. Use the same cases, model settings and
decoding budgets for comparable conditions. Implement A–C and E in the team's
runner; this CLI only exercises Workstream C.

`RunTrace` records the visible input, parsed query, initial and final proposals,
tool request/result, whether the tool executed, every model prompt and raw reply,
prompt/schema versions, model configuration, tolerances, token counts, latency,
failure stage, verdict and run ID. Preserve it as JSONL:

```python
with open("runs/condition_d.jsonl", "a", encoding="utf-8") as output:
    output.write(trace.model_dump_json() + "\n")
```

Join labels for scoring later using `trace.runtime_case.case_id` and
`graph_group_id`. Never add gold fields to model prompts or runtime tools.
The `invalid_input` CLI record has an input line number and verdict instead of a
full `RunTrace`, because there was no valid runtime case to record.

## Faizah: interpret decisions

| Status | Meaning |
| --- | --- |
| `verified` | The bound operation, evidence and proposed answer satisfy the contract |
| `unsupported` | Missing evidence, inconsistent conclusion, or model abstention |
| `wrong_operation` | The selected/requested operation cannot establish the requested quantity |
| `execution_error` | Parsing, binding, model, tool or result-format failure |

`response_action` is independently `answer` or `abstain`. Only verified decisions
release an answer. Inspect `reason_code` and `missing_evidence` for attribution.
`model_abstention` doesn't establish evidence insufficiency; it may be a false
abstention after labels are joined. `unsupported` is a verifier decision, distinct
from the benchmark's unsupported-answer metric.

The system releases the checked tool value for numerical answers, preserving its
precision. Model-proposed values must be within the configured 0.001 tolerance.
Sign uses its own 1e-9 threshold. Format to 3 decimals in presentation/scoring code
after deciding the sign. Boolean values cannot pass as numerical answers.

## Swapping the model

Implement `JSONModel.generate(messages, schema) -> Generation` in `llm/client.py`.
Return raw structured text and actual token accounting when available. Unknown
usage stays `null`; fixture runs use `model_mode=scripted_fixture`.

The parser accepts exactly 1 JSON object. It rejects code fences, duplicate keys,
nonfinite values, extra fields and oversized responses. It never repairs a model's
wrong operation or invalid query silently. Raw replies remain in the trace.
