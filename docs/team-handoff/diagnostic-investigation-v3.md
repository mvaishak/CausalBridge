# Diagnostic investigation v3 runner handoff

Read `docs/experiments/diagnostic-investigation-v3.md`. Base commit is `4f600b4c507bda66c0923a1a1a6546347a0b28f3`; record the exact v3 commit after amendment. Keep v1/v2 results and archives intact. Use new names for every plan and run. Do not merge or rewrite the final report.

```sh
uv sync --frozen --dev --extra anm
uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/diagnostic_investigation.py smoke --protocol v3 --output runs/cue-v3-smoke-01
uv run python scripts/diagnostic_investigation.py prepare --protocol v3 --phase diagnostic --output runs/cue-v3-diagnostic-plan-01
uv run python scripts/diagnostic_investigation.py prepare --protocol v3 --phase preflight --output runs/cue-v3-preflight-plan-01
uv run python scripts/diagnostic_investigation.py prepare --protocol v3 --phase full --output runs/cue-v3-full-plan-01
```

Before live work, call `/api/tags`, `/api/version`, and `/api/ps` at `http://127.0.0.1:11435`; verify `qwen3:8b` digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` and GPU residency. Independently validate each frozen plan and request order.

```sh
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-v3-diagnostic-plan-01 --output runs/cue-v3-diagnostic-live-01 --base-url http://127.0.0.1:11435
```

Require `diagnostic_passed: true`, exactly 4/4 complete, zero failures, zero checker rejections, and raw replay. If this gate fails, stop. Otherwise:

```sh
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-v3-preflight-plan-01 --output runs/cue-v3-preflight-live-01 --base-url http://127.0.0.1:11435
```

Require `preflight_passed: true`, 20/20 complete, zero failures, zero checker rejections, request order verification and raw replay. If this gate fails, stop. Otherwise:

```sh
uv run python scripts/diagnostic_investigation.py run --plan runs/cue-v3-full-plan-01 --output runs/cue-v3-full-live-01 --base-url http://127.0.0.1:11435 --preflight-run runs/cue-v3-preflight-live-01
uv run python scripts/diagnostic_investigation.py analyze --plan runs/cue-v3-full-plan-01 --run runs/cue-v3-full-live-01 --output runs/cue-v3-analysis-01
```

The runner saves raw replies before parsing. Preserve all schema, checker, transport, and completion failures. Do not edit or retry saved responses. Use `--resume` only after interruption with identical source, plan, and endpoint. The offline analyzer must replay the raw replies. Report exact denominators and effects, scientific limitations, model snapshots, all artifacts, and SHA-256 manifest/archive checksums. Never call probe or scripted outputs scientific observations.
