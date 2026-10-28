# CausalBridge: Vaishak's workstream

This repository implements **Workstream C: LLM orchestration and verification**.
It follows the implementation roadmap, the DSC 261 proposal, and the original idea.

You can run your part independently. The package includes structured parsing,
tool planning, evidence requirements, verification contracts, checked responses,
and JSONL traces. A small reference backend lets you test integration while Anish
builds the team's graph and numerical engine.

## Run it

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
From this folder:

```bash
uv sync --frozen --dev
uv run causalbridge demo --output runs/demo.jsonl
uv run pytest -q
```

The demo uses 8 hand-authored cases and scripted model responses. It runs the real
parser, planner, tools and verifier. You don't need model weights or an API key.
These fixtures test software behavior; they don't measure an LLM's performance.

Expected demo behavior:

| Case | Decision |
| --- | --- |
| X → Y with complete CPTs | Answer `positive`, computed effect +0.4 |
| Same question and graph, CPTs withheld | Abstain: missing evidence |
| Positive-effect claim from reachability | Reject: wrong operation |
| No directed path, no CPTs | Answer `zero` |
| Decrease X with the original CPTs | Answer `negative` |
| Confounded graph, valid adjustment and joint distribution | Answer 0.6 |
| Same intervention question, only P(X,Y) visible | Abstain: missing evidence |
| Proposed 0.9, computed intervention probability 0.7 | Reject: inconsistent answer |

Existing trace files are protected. Add `--overwrite` when you want to replace one.

## Connect the model

The default is `qwen2.5:3b` through a local Ollama server. Install Ollama using its
[official instructions](https://docs.ollama.com/quickstart), then run:

```bash
ollama pull qwen2.5:3b
ollama serve
```

If the Ollama app already runs its server, you can use that server. In another terminal:

```bash
uv run causalbridge run \
  --input examples/runtime_cases.jsonl \
  --config configs/model.json \
  --output runs/qwen-smoke.jsonl
```

`configs/model.json` sets the endpoint, model, seed, temperature, context budget,
generation budget and timeout. The adapter sends JSON schemas using Ollama's
[structured-output API](https://docs.ollama.com/api/chat). The candidate comes from
the roadmap; [Qwen's model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
describes the original model. Check its license before distributing weights.

**Live Qwen inference still needs validation.** No Ollama server or model weights
were available during setup. HTTP adapter tests cover request settings, token
accounting, malformed replies and truncation. Hardware fit, actual JSON reliability,
latency and model accuracy need a live smoke run on your chosen machine.

Exit codes: `0` means every input was processed without an execution failure,
including valid abstentions; `1` means at least 1 execution failure was recorded;
`2` means a file/configuration/CLI error. A model outage produces a trace with an
`execution_error` verdict.

## What you own

```text
src/causalbridge/
  schemas.py                 visible evidence, queries, proposals, tool IO, verdicts
  llm/parser.py              strict JSON parser and versioned prompts
  llm/client.py              replaceable model protocol and Ollama adapter
  llm/tool_planner.py        bind query and proposed operation
  verifier/contracts.py     operation, evidence and conclusion checks
  pipeline.py               parse → plan → execute → interpret → verify
  tools/protocol.py         interface for Anish's engine
  tools/graph.py            graph checks needed by verification
  tools/reference.py        small development backend, capped at 12 nodes
  demo.py                   explicitly labeled integration fixtures
  cli.py                    smoke runs, JSONL traces and schema export
```

Arunima's benchmark and witness generation, Kris's A–E runner, and Faizah's scoring
and confidence intervals remain separate team components. There's no fabricated
pilot benchmark, held-out data, or reported research result in this repository.

Read [the integration guide](docs/integration.md) for the APIs and exact data format.
[The scope and assumptions](docs/scope-and-assumptions.md) explain the scientific
limits. [The handoff checklist](docs/handoff.md) maps the code to your deliverables.

## Check changes

```bash
bash scripts/check.sh
```

This installs locked dependencies, checks formatting and lint, runs tests, executes
the offline demo, and builds the package. GitHub Actions runs the same checks on
Python 3.12 and 3.13. Re-export shared schemas after changing types:

```bash
uv run causalbridge schemas --output schemas
```

Keep labels, witness models and withheld CPTs in separate oracle files. Runtime
cases contain only public evidence. Full benchmark rows require explicit projection
with `RuntimeCase.from_benchmark(row)` or CLI `--benchmark-rows`.
