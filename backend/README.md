# CorrelCore Backend

FastAPI backend for CorrelCore.

The package metadata in `pyproject.toml` uses this file as its project README so
editable installs and CI dependency syncs can build the package consistently.

## Local quality checks

The canonical backend quality gate is executable and pins Python 3.12 to match
CI and `pyproject.toml`:

```bash
./scripts/check.sh
```

It runs the same checks that must stay green for an M1/Milestone review:

1. `uv sync --python 3.12 --extra dev --extra analytics --frozen`
2. `uv run --python 3.12 ruff check .`
3. `uv run --python 3.12 ruff format --check .`
4. `uv run --python 3.12 mypy app`
5. `uv run --python 3.12 pytest`

Run the script from `backend/` or from the repository root as
`backend/scripts/check.sh`. If dependency downloads are unavailable in the local
environment, treat the result as an environment warning and rely on CI for the
final gate verdict.
