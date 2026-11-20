# CausalBridge

CausalBridge checks whether an LLM's causal answer is supported by the supplied
graph and evidence. A directed path from X to Y doesn't tell us whether increasing
X increases Y. The system checks the selected operation, its evidence requirements,
and the proposed conclusion before answering or abstaining.

Track A has graph tools, a validated 50-question/ten-group synthetic pilot, a
selectable numerical engine and independently checked witnesses. Track B has
ANM, matched evidence packages, a durable runner, predictor/checker and baseline
exports. The exploratory 17-pair Tübingen pilot has been run. Its case-level
diagnosis and the remaining research steps are in [readme_new.md](readme_new.md).

For reproduction commands, use the [pilot guide](docs/pilot_run.md).
Held-out evaluation, bootstrap intervals and the final report are deferred.

Start with the [19 November team handoff](docs/team-handoff/2026-11-19/README.md)
for audited pilot results, measured resources and the proposed midterm rerun.

## Setup

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync --frozen --dev
uv run causalbridge demo --output runs/demo.jsonl
uv run causalbridge demo --backend engine --output runs/engine-demo.jsonl
```

The demo uses 8 scripted cases. It runs offline and doesn't measure model performance.
Use `--overwrite` to replace an existing output file.
`demo` and `run` accept `--backend engine`; the default remains `reference`.

## ANM diagnostic and original request

```bash
uv sync --frozen --dev --extra anm
uv run --extra anm python examples/anm_integration.py --output runs/anm-handshake
```

Use a new output directory per attempt. This example computes ANM on synthetic
rows and connects saved artifacts to the existing predictor/checker with scripted
S1 output. It does not load Tuebingen labels or run a live LLM.

For caller-supplied numeric rows:

```bash
uv run --extra anm causalbridge anm-run \
  --input pair.json --config anm-config.json --output runs/anm-pair-001
```

Input JSON contains only `case_id`, `ab_mapping_id` and ordered numeric `rows`.
The default threshold is unconfigured; it returns scores without a direction.
`request.json` is saved independently before execution and is the original
`ANMRequestBinding` that the verifier needs. See [producer/API handoff](docs/anm_producer.md)
and [authoritative integration contract](docs/track_b_integration_contract.md).

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

These are Track A smoke settings. The bounded Track B pilot uses
`configs/pilot-model.json`; its guide requires an explicit model digest and a
fresh output directory. Earlier live synthetic smoke work is documented in
[Kris's smoke record](docs/kris-smoke-v2.md).

## Structure

```text
src/causalbridge/
  benchmark/       # Arunima: models, evidence pairs and witnesses
  tools/           # Structural graph helpers and Anish's numerical engine
  discovery/       # Direction schemas, ANM request storage, statistics and diagnostic
  llm/             # Vaishak: parsing and tool planning
  verifier/        # Vaishak: evidence and conclusion checks
  evaluation/      # Kris and Faizah: baselines, runner and scoring
  schemas.py       # Shared runtime types
  pipeline.py      # Connects the model, tools and verifier
data/              # Pilot, development and test splits
schemas/           # Exported JSON schemas
tests/             # Tests across components
```

`evaluation/` contains the native runner, independent audits, baseline exports
and exploratory pilot scoring. Confidence intervals remain future work.
`tools/reference.py` is preserved; `tools/engine.py` selects tested computations
from `tools/inference.py`. Track B's optional ANM extra uses NumPy and never routes
direction predictions through Track A's effect verifier.
See [data conventions](data/README.md) before adding cases.

## Development

```bash
bash scripts/check.sh
```

This installs the ANM extra and runs lint, formatting, tests, both Track A demos,
the synthetic ANM handshake and package builds.
GitHub Actions runs the same checks on Python 3.12 and 3.13.

Use a branch and open a pull request into `main`. See [contributing](CONTRIBUTING.md)
for ownership and workflow, and [integration](docs/integration.md) for the shared
interfaces. Runtime prompts and tools must never receive gold labels or withheld CPTs.

## Project progress and Track B work

See the [project knowledge bank](docs/knowledge/README.md) for evidence-linked
progress, ownership, decisions and planned versus completed work. Pilot-ready
software and offline validation are distinct from live-model research findings.
