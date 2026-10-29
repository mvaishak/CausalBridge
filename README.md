# CausalBridge

CausalBridge checks whether an LLM's causal answer is supported by the supplied
graph and evidence. A directed path from X to Y doesn't tell us whether increasing
X increases Y. The system checks the selected operation, its evidence requirements,
and the proposed conclusion before answering or abstaining.

Parsing, orchestration and verification are implemented with a reference tool
backend. Benchmark generation, the full engine, baselines and evaluation are pending.

## Setup

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync --frozen --dev
uv run causalbridge demo --output runs/demo.jsonl
```

The demo uses 8 scripted cases. It runs offline and doesn't measure model performance.
Use `--overwrite` to replace an existing output file.

## Run with a model

Install [Ollama](https://docs.ollama.com/quickstart), then pull the model and start
the server:

```bash
ollama pull qwen2.5:3b
ollama serve
```

If Ollama is already running, use the existing server. In another terminal:

```bash
uv run causalbridge run \
  --input examples/runtime_cases.jsonl \
  --config configs/model.json \
  --output runs/qwen-smoke.jsonl
```

Model settings are in `configs/model.json`. Live Qwen inference still needs validation.

## Structure

```text
src/causalbridge/
  benchmark/       # Arunima: models, evidence pairs and witnesses
  tools/           # Anish: graph and numerical operations
  llm/             # Vaishak: parsing and tool planning
  verifier/        # Vaishak: evidence and conclusion checks
  evaluation/      # Kris and Faizah: baselines, runner and scoring
  schemas.py       # Shared runtime types
  pipeline.py      # Connects the model, tools and verifier
data/              # Pilot, development and test splits
schemas/           # Exported JSON schemas
tests/             # Tests across components
```

`benchmark/` and `evaluation/` are starting points for the remaining workstreams.
`tools/reference.py` is the development backend until the full engine is integrated.
See [data conventions](data/README.md) before adding cases.

## Development

```bash
bash scripts/check.sh
```

This runs lint, formatting checks, tests, the offline demo and the package build.
GitHub Actions runs the same checks on Python 3.12 and 3.13.

Use a branch and open a pull request into `main`. See [contributing](CONTRIBUTING.md)
for ownership and workflow, and [integration](docs/integration.md) for the shared
interfaces. Runtime prompts and tools must never receive gold labels or withheld CPTs.
