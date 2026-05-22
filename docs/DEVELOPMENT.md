# Development

This guide keeps the local development and quality-gate environment aligned
with GitHub Actions.

## Prerequisites

- Git for Windows or Git on Linux/macOS
- Node.js 22, matching `.nvmrc`
- pnpm 11.0.8, matching `package.json`
- Python 3.12
- uv for Python dependency management
- Docker Desktop or another Docker Compose v2 runtime
- gitleaks for local secret scanning

Recommended Windows setup:

```powershell
winget install OpenJS.NodeJS.LTS
corepack enable
corepack prepare pnpm@11.0.8 --activate
winget install Python.Python.3.12
winget install astral-sh.uv
winget install gitleaks.gitleaks
```

If Git refuses to operate from this checkout because of ownership metadata, add
the clone as an explicit safe directory:

```powershell
git config --global --add safe.directory C:/path/to/correlcore
```

## Local quality gate

The PowerShell gate is intended for Windows contributors and CI debugging from
the Codex desktop workspace:

```powershell
.\scripts\local-quality.ps1
```

It runs:

1. `pnpm.CMD install --frozen-lockfile`
2. `pnpm.CMD --filter @correlcore/web lint`
3. `pnpm.CMD --filter @correlcore/web typecheck`
4. `pnpm.CMD --filter @correlcore/web test`
5. `uv sync --python 3.12 --extra dev --extra analytics --frozen`
6. `uv run --python 3.12 ruff check .`
7. `uv run --python 3.12 ruff format --check .`
8. `uv run --python 3.12 mypy app`
9. `uv run --python 3.12 pytest`
10. `gitleaks detect --source . --no-git --redact`
11. `gitleaks detect --source . --redact`

Use the skip switches only while debugging a specific layer:

```powershell
.\scripts\local-quality.ps1 -SkipBackend
.\scripts\local-quality.ps1 -SkipFrontend
.\scripts\local-quality.ps1 -SkipSecrets
```

On Unix-like systems, `backend/scripts/check.sh` remains the canonical backend
gate and `pnpm` can be used directly instead of `pnpm.CMD`.

## Backend test database

The API unit tests mostly mock external services, but migration smoke tests need
PostgreSQL. The CI job uses PostgreSQL 16.4. For local migration checks, start
the Docker stack or a throwaway Postgres 16 container, then run from `backend/`:

```powershell
uv sync --python 3.12 --extra dev --extra analytics --frozen
$env:APP_ENV = "test"
$env:DATABASE_URL = "postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore"
$env:REDIS_URL = "redis://:changeme@localhost:6379/0"
$env:SECRET_KEY = "local-dev-" + [guid]::NewGuid().ToString("N")
$env:ENCRYPTION_KEY = uv run --python 3.12 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
uv run --python 3.12 alembic -c migrations/alembic.ini upgrade head
```

The values above are generated for local test runs. Do not reuse local test
values in deployed environments.

## Database roles and RLS

Fresh Docker stacks create two database roles:

- `POSTGRES_USER`: migration/owner role used by Alembic.
- `APP_DB_USER`: restricted runtime role used by API and worker containers.

Migration `012_enforce_rls_and_app_role_grants.py` grants runtime table
privileges to `correlcore_app` when that role exists and enables
`FORCE ROW LEVEL SECURITY` on user-owned data tables. The application binds
`app.current_user_id` transaction-locally after authentication and before
loading encrypted per-user data. Worker jobs bind the same setting per user
before reading or writing RLS-protected analytics data.

For existing deployments, create `APP_DB_USER` and `APP_DB_PASSWORD` before
switching API/worker containers to the restricted role, then run Alembic
`upgrade head`. Keep the default `APP_DB_USER=correlcore_app` unless you also
adapt the migration grants for a custom role name.

## Rate limiting

SlowAPI uses Redis by default via `REDIS_URL`; deployments can override the
storage with `RATE_LIMIT_STORAGE_URL`. Production reverse-proxy stacks set
`RATE_LIMIT_TRUST_PROXY_HEADERS=true` so buckets are based on the forwarded
client IP. Directly exposed API ports should leave it `false` to avoid trusting
spoofable request headers.

## Secret scanning

Run both scans before opening a PR:

```powershell
gitleaks detect --source . --no-git --redact
gitleaks detect --source . --redact
```

The first command checks the current working tree. The second checks Git
history. GitHub Actions runs the history scan in `CI - Security` on every push
and pull request.
