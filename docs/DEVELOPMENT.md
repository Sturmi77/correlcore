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

## Development on network shares (NAS/SMB)

pnpm's default isolated `node_modules` layout uses symlinks. Windows clients,
Synology SMB mounts, UNC paths such as `\\SynologyDS923\...`, and mapped
drives like `Y:` often reject those symlinks, which produces errors like
`UNKNOWN: unknown error, symlink ...`.

This repository ships a root [`.npmrc`](../.npmrc) with NAS-friendly defaults:

- `node-linker=hoisted` — flat `node_modules`, fewer links
- `package-import-method=copy` — copy packages from the store instead of linking

Additionally, keep the **pnpm store on local disk**, not on the NAS. Either:

```powershell
pnpm config set store-dir C:\Users\<you>\.pnpm-store --global
```

or add this to your user-level `%USERPROFILE%\.npmrc` (not committed — paths
are machine-specific):

```ini
store-dir=C:\Users\<you>\.pnpm-store
```

Then from the repo root on the network share:

```powershell
pnpm.cmd install --frozen-lockfile
cd apps\web
pnpm.cmd dev
```

If symlinks still fail after the settings above, use a local clone for daily
development (for example `C:\dev\correlcore`) and keep the NAS copy for Git
sync or deployment files only.

Optional Windows/Synology tuning if problems remain:

- Enable **Developer mode** in Windows settings (symlink creation).
- On Synology DSM, review SMB advanced settings for symbolic link support.

## Local quality gate

The PowerShell gate is intended for Windows contributors and CI debugging from
the Codex desktop workspace:

```powershell
.\scripts\local-quality.ps1
```

It runs:

1. `pnpm.CMD install --frozen-lockfile`
2. `pnpm.CMD check:contrast` (ADR-0027 WCAG token pairs)
3. `pnpm.CMD --filter @correlcore/web lint`
4. `pnpm.CMD --filter @correlcore/web typecheck`
5. `pnpm.CMD --filter @correlcore/web test`
6. `uv sync --python 3.12 --extra dev --extra analytics --frozen`
7. `uv run --python 3.12 ruff check .`
8. `uv run --python 3.12 ruff format --check .`
9. `uv run --python 3.12 mypy app`
10. `uv run --python 3.12 pytest`
11. `gitleaks detect --source . --no-git --redact`
12. `gitleaks detect --source . --redact`

Use the skip switches only while debugging a specific layer:

```powershell
.\scripts\local-quality.ps1 -SkipBackend
.\scripts\local-quality.ps1 -SkipFrontend
.\scripts\local-quality.ps1 -SkipSecrets
```

On Unix-like systems, `backend/scripts/check.sh` remains the canonical backend
gate. Run `pnpm check:contrast` from the repo root before opening a web PR,
then use `pnpm` directly for lint/typecheck/test.

## UI work without a backend (mock API + dev-mode fixtures)

For pure frontend work there is a backend-free path: a minimal mock API plus the
dev-mode fixtures in [`apps/web/src/lib/dev/phaseFixtures.ts`](../apps/web/src/lib/dev/phaseFixtures.ts).
The fixtures only render for an authenticated session, so `GET /api/v1/auth/me`
has to answer — that is what the mock server is for.

| Script                                                              | Port | Purpose                                                       |
| ------------------------------------------------------------------- | ---- | ------------------------------------------------------------- |
| [`scripts/dev-mock-api.cmd`](../scripts/dev-mock-api.cmd)           | 8001 | Mock API (auth, preferences, profile; rest 404 + log line)    |
| [`scripts/dev-web.cmd`](../scripts/dev-web.cmd)                     | 5173 | SvelteKit dev server, browser build                           |
| [`scripts/dev-web-capacitor.cmd`](../scripts/dev-web-capacitor.cmd) | 5174 | Same app with `VITE_CAPACITOR=1` (bearer auth, absolute base) |

Start the mock API first, then a web server. Both web wrappers default
`INTERNAL_API_URL` to the mock; set it yourself to use the real API:

```powershell
$env:INTERNAL_API_URL = 'http://127.0.0.1:8000'
```

The wrappers exist because Node is managed via fnm here and is not on the global
PATH; [`scripts/_node-path.cmd`](../scripts/_node-path.cmd) resolves the highest
installed fnm version (override with `NODE_DIR`). `.claude/launch.json` starts
the same three scripts for browser-driven sessions.

Enable dev mode in the running app: Settings → tap the version string 7× (ADR-0019),
then toggle "Mock-Daten fuer Visualisierungen" and pick a phase preset.

### Client developer mode in production (#589)

The **client** developer mode (7× tap, Force Visualizations, phase mocks) is
available in **production web builds** — it is not gated by `import.meta.env.DEV`
or a backend flag. Settings persists `dev_mode_enabled` and `dev_force_viz` in
`localStorage` on the device.

| Layer | Unlock | Works in CorrelCore Cloud? |
| ----- | ------ | -------------------------- |
| Client dev mode | 7× tap on Settings version string | Yes — mock charts/insights locally |
| Backend `/dev` view | `DEV_VIEW_ENABLED=true` on API (`APP_ENV` ≠ production) | No (by design); selfhost only |

After unlocking, the DEVELOPER section shows Force Visualizations and insight
phase presets. Tag-cluster and heatmap QA can use `dev_force_viz` without waiting
for live analytics maturity.

Caveats:

- `devPhase` lives in memory only. A full page reload resets the preset to
  `collecting` — navigate in-app to keep it.
- The mock API has no persistence and no authorization. It is for rendering
  work, never for testing API behaviour.
- `VITE_CAPACITOR=1` only flips the build flag. `deepLinks.ts` and
  `pushNotifications.ts` additionally check `Capacitor.isNativePlatform()`, which
  stays false in a browser, so push, widget deep links and the secure-session
  path remain no-ops. Those still need a real APK build.
- Stopping a wrapper can leave the Node child running (cmd does not forward the
  kill). If a port stays busy, stop the `node` process holding it.

## Parallel React GUI experiment

An experimental React frontend (`apps/web-react/`) can run alongside the
production SvelteKit app on a separate dev port. Both share the same API.

Full guide: [`docs/frontend/PARALLEL_REACT_GUI.md`](frontend/PARALLEL_REACT_GUI.md)  
Agent context (Claude / Cursor): [`apps/web-react/CLAUDE.md`](../apps/web-react/CLAUDE.md)

```bash
# API must be running on :8000 (see AGENTS.md)
export INTERNAL_API_URL=http://127.0.0.1:8000

pnpm dev          # SvelteKit → http://localhost:5173
# pnpm dev:react / pnpm dev:all — planned after apps/web-react is scaffolded
# (see PARALLEL_REACT_GUI.md); scripts are not in package.json yet.
```

Until the React package exists, use SvelteKit only. After scaffold, the React
app will proxy `/api/*` to `INTERNAL_API_URL` — same cookie-auth pattern as
SvelteKit ([ADR-0011](adr/0011-web-internal-reverse-proxy.md)). Production
deploy and CI stay unchanged until an explicit cutover decision.

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

Current migration head is documented in `backend/migrations/versions/` (run
`alembic heads` after sync).

## Analytics worker (local)

Regenerate insights without waiting for the nightly 03:00 UTC cron:

```bash
cd backend
uv run --python 3.12 python -m app.workers.analytics --once
```

Or use **Settings → Analysis → Refresh insights** in the web UI (`POST /api/v1/insights/regenerate`).
See [ADR-0037](adr/0037-insight-triggers-tag-cluster-maturity.md).

## M7 full-stack QA seed

After Postgres is running and migrations are applied, seed a verified QA user
with 100 days of analytics-ready entries (bypasses the 7-day API backdate window):

```powershell
cd backend
uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset
```

Login: `m7-qa@localhost.dev` / `CorrectHorse123!` — use `/insights` without developer
mock visualizations. Verify API responses:

```powershell
uv run --python 3.12 python scripts/verify_m7_qa_api.py
```

See [`docs/quality/M7_QUALITY_GATE.md`](quality/M7_QUALITY_GATE.md).

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

## Developer database dump / restore

For local backup/restore during development (not production ops):

```bash
export APP_ENV=development
./scripts/dev-db-dump.sh                # writes /tmp/correlcore-backups/*.dump (+ meta)
./scripts/dev-db-restore.sh /tmp/correlcore-backups/correlcore-dev-….dump --yes
```

Keep the same `ENCRYPTION_KEY` as the dump environment. With
`DEV_VIEW_ENABLED=true` and `APP_ENV=development`, `/dev` can also create and
restore dumps via `GET/POST /api/v1/dev/db/backups` and `POST /api/v1/dev/db/restore`.
`ops_ready` stays `false` until a separate production ops design exists.

Worker run history for GUI validation lives under `GET /api/v1/dev/workers`
(and `/workers/latest`) when `DEV_VIEW_ENABLED=true`.

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
