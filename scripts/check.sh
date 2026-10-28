#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=causalbridge --cov-report=term-missing
uv run causalbridge demo --output runs/check-demo.jsonl --overwrite
uv build
