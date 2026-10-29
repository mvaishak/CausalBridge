# Contributing

## Ownership

| Area | Owner | Location |
| --- | --- | --- |
| Benchmark and witness validation | Arunima | `src/causalbridge/benchmark/` |
| Graph and numerical engine | Anish | `src/causalbridge/tools/` |
| LLM orchestration and verifier | Vaishak | `src/causalbridge/llm/`, `verifier/`, `pipeline.py` |
| Baselines and experiment runner | Kris | `src/causalbridge/evaluation/` |
| Metrics, uncertainty and audits | Faizah | `src/causalbridge/evaluation/` |

## Changes

1. Branch from the latest `main`. Use `codex/` for agent-created branches or a
   short name such as `benchmark/pilot` for your own work.
2. Keep each pull request focused on one change. Add tests for new behavior.
3. Run `bash scripts/check.sh` before opening a pull request into `main`.
4. Ask the affected component's owner to review interface changes.

The shared types are in `src/causalbridge/schemas.py`. Read
[the integration guide](docs/integration.md) before connecting a component. If the
types change, regenerate the exported contracts:

```bash
uv run causalbridge schemas --output schemas
```

Use `ToolBackend` when connecting the graph engine and `CausalBridge.run` from the
experiment runner. Keep tests in `tests/`; existing import paths should keep working.

## Data and experiments

Follow [the data conventions](data/README.md). Keep oracle data outside runtime
cases. Join reference labels for scoring after execution.

Keep evidence pairs, paraphrases and isomorphic graph copies in the same split.
Tune prompts and rules on development data, then freeze the method before held-out
evaluation. Record model settings and retain raw traces under `runs/`.
