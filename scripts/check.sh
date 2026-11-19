#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --dev --extra anm
uv run --extra anm ruff check .
uv run --extra anm ruff format --check .
uv run --extra anm python -m pytest --cov=causalbridge --cov-report=term-missing
uv run --extra anm causalbridge demo --output runs/check-demo.jsonl --overwrite
uv run --extra anm causalbridge demo --backend engine --output runs/check-engine-demo.jsonl --overwrite
anm_check_directory=$(mktemp -d "${TMPDIR:-/tmp}/causalbridge-anm-check.XXXXXX")
uv run --extra anm python examples/anm_integration.py --output "$anm_check_directory/handshake"
uv build
