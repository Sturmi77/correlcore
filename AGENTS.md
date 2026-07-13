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

### Parallel React GUI (experimental)

See [`docs/frontend/PARALLEL_REACT_GUI.md`](docs/frontend/PARALLEL_REACT_GUI.md).

| GUI                    | Command                           | Port        |
| ---------------------- | --------------------------------- | ----------- |
| SvelteKit (production) | `pnpm dev`                        | 5173        |
| React (experiment)     | `pnpm dev:react` (after scaffold) | 5174        |
| Both                   | `pnpm dev:all` (after scaffold)   | 5173 + 5174 |

Agent context for React work: [`apps/web-react/CLAUDE.md`](apps/web-react/CLAUDE.md). Set `INTERNAL_API_URL=http://127.0.0.1:8000` for both frontends. No backend changes required in proxy mode.

### Lint / test / build

| Layer                  | Commands                                                                         |
| ---------------------- | -------------------------------------------------------------------------------- |
| Web + root             | `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`                         |
| Backend                | `cd backend && uv run --python 3.12 ruff check .`, `uv run --python 3.12 pytest` |
| E2E smoke (mocked API) | `pnpm --filter @correlcore/web test:e2e:smoke`                                   |

Pre-commit (`.husky/pre-commit`) runs Prettier on staged `*.ts`, `*.svelte`, etc. via `pnpm exec prettier`.

### Full stack alternative

`infra/docker/docker-compose.user-test.yml` runs published GHCR images (Postgres, Redis, API, web, Mailpit). Requires a filled `.env` from `.env.user-test.example`. Not required for day-to-day code changes if you run API/web locally as above.
