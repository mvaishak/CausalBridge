# Verification record

Verified on October 27, 2026, with Python 3.12.11 on macOS arm64.

| Check | Result |
| --- | --- |
| `uv sync --frozen --dev` | Locked environment installs successfully |
| `uv lock --check` | Lockfile matches package metadata |
| `uv run ruff check .` | Pass |
| `uv run ruff format --check .` | Pass |
| `uv run pytest --cov=causalbridge --cov-report=term-missing` | 67 tests pass; 88% overall coverage |
| Offline fixture demo | 8 traces: 4 verified, 3 unsupported, 1 wrong operation |
| `uv build` | Source archive and wheel built successfully |
| Isolated wheel installation and `python -m causalbridge demo` | All 8 fixture scenarios run successfully |
| Exported JSON schemas | All 8 parse successfully |
| Source archive contents | Original proposal and idea PDFs excluded |

An independent read-only review identified 2 input-handling defects. Regression
tests reproduced both before fixes: invalid benchmark root types stopped ingestion,
and validation exceptions copied rejected nested values into error traces. Both
are fixed. A pipeline regression test also verifies that operation mismatch is
classified before missing numerical evidence.

The HTTP model adapter is tested with controlled HTTP responses. Live Qwen inference
hasn't run because the machine had no Ollama executable, running server or model
weights at setup time. The fixture demo and coverage counts don't measure model
quality or the project's research hypothesis.
