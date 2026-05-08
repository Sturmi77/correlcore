#!/usr/bin/env bash
# Canonical backend quality gate. Keep this command in sync with
# .github/workflows/ci-api.yml and docs/quality/M1_QUALITY_GATE.md.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv sync --python 3.12 --extra dev --frozen
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format --check .
uv run --python 3.12 mypy app
uv run --python 3.12 pytest
