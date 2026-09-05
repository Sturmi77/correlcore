# AGENTS.md

## Cursor Cloud specific instructions

CorrelCore is a pnpm + uv monorepo (SvelteKit web + FastAPI). See `docs/DEVELOPMENT.md` and `README.md` for canonical commands.

### Services (local dev)

| Service                  | Purpose                   | How to start                                                                                                                                                         |
| ------------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL 16 (pgvector) | DB + migrations           | `docker run -d --name correlcore-postgres -e POSTGRES_USER=correlcore -e POSTGRES_PASSWORD=correlcore -e POSTGRES_DB=correlcore -p 5432:5432 pgvector/pgvector:pg16` |
| Redis 7                  | Rate limits / sessions    | `docker run -d --name correlcore-redis -p 6379:6379 redis:7-alpine redis-server --requirepass changeme`                                                              |
| Mailpit (optional)       | Email verification in dev | `docker run -d --name correlcore-mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit:latest`                                                                           |

After Postgres is healthy, from `backend/`:

```bash
export APP_ENV=development
export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
export REDIS_URL='redis://:changeme@localhost:6379/0'
export SECRET_KEY='local-dev-secret-key-min-32-bytes-long-padding'
export ENCRYPTION_KEY='<valid-fernet-key>'  # see backend pytest env in ci-api.yml
export CORS_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'
export SMTP_HOST=localhost SMTP_PORT=1025
uv run --python 3.12 alembic -c migrations/alembic.ini upgrade head
```

### Dev servers

- **API** (`backend/`): `uv run --python 3.12 uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Web** (repo root): set `INTERNAL_API_URL=http://127.0.0.1:8000` so `hooks.server.ts` proxies `/api/*` to the API, then `pnpm dev` (port **5173**).

**Vite bind quirk:** the dev server may listen on `localhost` only. Use `http://localhost:5173/` in the browser; `127.0.0.1:5173` can refuse connections even when the process is up.

### Analytics worker & on-demand insights (M10.1)

After API + Redis are up, run insight generation locally without waiting for 03:00 UTC:

```bash
cd backend
uv run --python 3.12 python -m app.workers.analytics --once
```

Weekly insight digest (foundation #147), same env:

```bash
cd backend
uv run --python 3.12 python -m app.workers.digest --once
```

Or trigger regeneration for the logged-in user via API: `POST /api/v1/insights/regenerate` (rate-limited 1×/hour). Latest digest snapshot: `GET /api/v1/insights/digest/latest`. Bulk import via `POST /entries/batch` schedules a debounced background regeneration.

Admin manual worker run: set `INSIGHT_TRIGGER_ADMIN_EMAILS` and call `POST /api/v1/insights/trigger`.

### Parallel React GUI (planned, not scaffolded)

See [`docs/frontend/PARALLEL_REACT_GUI.md`](docs/frontend/PARALLEL_REACT_GUI.md).
`apps/web-react/` currently holds agent notes only — there is **no** package and
**no** `pnpm dev:react` / `dev:all` scripts in the root `package.json` yet.
Do not invent a React scaffold unless a task explicitly requests it.
Production GUI remains SvelteKit (`pnpm dev` on port **5173**).

### Lint / test / build

Canonical strategy and CI pyramid: [`docs/quality/TESTING.md`](docs/quality/TESTING.md).

| Layer                  | Commands                                                                         |
| ---------------------- | -------------------------------------------------------------------------------- |
| Web + root             | `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`                         |
| Backend                | `cd backend && uv run --python 3.12 ruff check .`, `uv run --python 3.12 pytest` |
| E2E smoke (mocked API) | `pnpm --filter @correlcore/web test:e2e:smoke`                                   |

Pre-commit (`.husky/pre-commit`) runs Prettier on staged `*.ts`, `*.svelte`, etc. via `pnpm exec prettier`.

### Full stack alternative

`infra/docker/docker-compose.user-test.yml` runs published GHCR images (Postgres, Redis, API, web, Mailpit). Requires a filled `.env` from `.env.user-test.example`. Not required for day-to-day code changes if you run API/web locally as above.

### PRs must auto-close finished issues

When a PR **fully completes** an issue’s acceptance criteria, the PR description
(or a commit message that lands on `main`) **must** include a GitHub closing
keyword so the issue closes on merge:

- Preferred: `Closes #123` / `Fixes #123` (also accepted: `Close`, `Closed`,
  `Fix`, `Fixed`, `Resolve`, `Resolves`, `Resolved`)
- Put the keyword in the **PR body** (reliable) or in a commit that merges to
  the default branch — not only in review comments or vague phrases like
  “Completes #123” / “Relates to #123” (those do **not** auto-close).

**Close on merge when:**

- Implementation + automated tests in CI cover the issue, **and**
- No **external** follow-up is still required to call the work done
  (manual device QA, production redeploy/verify, owner-only ops, human
  sign-off trackers, open discussions).

**Do not use `Closes` / `Fixes` when:**

- The PR is partial (Phase 1 of N) — use `Relates to #123` or `Part of #123`
  and leave the parent issue open until the completing PR.
- External tests / sign-off remain open (e.g. device QA issues, “verify on
  prod after redeploy”). Ship with `Relates to #123`; close only after that
  gate passes (owner or a dedicated follow-up PR/comment).
- The PR is docs/spec-only for a feature that is not implemented yet.

Agents cannot call `closeIssue` (no triage permission). Relying on merge
auto-close is the required path; see
[`docs/quality/ISSUE_TRACKER_HYGIENE_2026-07-31.md`](docs/quality/ISSUE_TRACKER_HYGIENE_2026-07-31.md)
when keywords were missed.
