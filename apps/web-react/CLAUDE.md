# CLAUDE.md — React GUI Experiment (@correlcore/web-react)

Agent context for Claude Design, Cursor, and other AI assistants working on the
experimental React frontend. Human-readable architecture and setup:
[`docs/frontend/PARALLEL_REACT_GUI.md`](../../docs/frontend/PARALLEL_REACT_GUI.md).

---

## Mission

Build an **experimental React frontend** for CorrelCore in parallel to the
**production SvelteKit app** (`apps/web`). Do **not** modify `apps/web` unless
explicitly asked.

| App                             | Port | Status                       |
| ------------------------------- | ---- | ---------------------------- |
| SvelteKit (`@correlcore/web`)   | 5173 | Production GUI — canonical   |
| React (`@correlcore/web-react`) | 5174 | Experiment — evaluation only |

Both share one FastAPI backend on port **8000**.

---

## Stack

- Vite + React + TypeScript
- Tailwind CSS 4 (match existing design tokens where possible)
- pnpm workspace: `@correlcore/web-react`

---

## Critical Rules

1. **API base URL:** Always `/api/v1` (relative). **Never** hardcode `:8000` in browser code.
2. **Auth:** HttpOnly cookies via `credentials: 'include'`. Copy the pattern from
   [`apps/web/src/lib/api/client.ts`](../web/src/lib/api/client.ts) (single-flight refresh on 401).
3. **Proxy:** Dev server proxies `/api` → `INTERNAL_API_URL` (default `http://127.0.0.1:8000`).
4. **Do not break production:** No changes to `apps/web`, backend, Docker, or CI unless the task
   explicitly requires it.
5. **Browser URL:** Use `http://localhost:5174/` — not `127.0.0.1:5174` (Vite bind quirk).
6. **`localhost` vs `127.0.0.1`:** Different origins for cookies and CORS — stay on `localhost`.

Proxy trade-offs (extra hop, separate sessions, production proxy TBD):
[`docs/frontend/PARALLEL_REACT_GUI.md` § Proxy approach — trade-offs](../../docs/frontend/PARALLEL_REACT_GUI.md#proxy-approach--trade-offs).

---

## Commands

| Action                    | Command                                         |
| ------------------------- | ----------------------------------------------- |
| Dev (React only)          | `pnpm dev:react` (repo root)                    |
| Dev (both GUIs)           | `pnpm dev:all`                                  |
| Dev (SvelteKit reference) | `pnpm dev`                                      |
| Lint                      | `pnpm --filter @correlcore/web-react lint`      |
| Typecheck                 | `pnpm --filter @correlcore/web-react typecheck` |
| Test                      | `pnpm --filter @correlcore/web-react test`      |

---

## Prerequisites

Same as the main app — see repo root [`AGENTS.md`](../../AGENTS.md):

```bash
# API (from backend/)
export APP_ENV=development
export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
export REDIS_URL='redis://:changeme@localhost:6379/0'
export SECRET_KEY='local-dev-secret-key-min-32-bytes-long-padding'
export ENCRYPTION_KEY='<valid-fernet-key>'
uv run --python 3.12 uvicorn app.main:app --host 0.0.0.0 --port 8000

# React dev (repo root)
export INTERNAL_API_URL=http://127.0.0.1:8000
pnpm dev:react
```

Postgres and Redis via Docker — see `AGENTS.md`.

---

## Key Reference Files (read-only)

| Purpose                    | Path                                            |
| -------------------------- | ----------------------------------------------- |
| API client pattern         | `apps/web/src/lib/api/client.ts`                |
| API contract constants     | `apps/web/src/lib/contracts/apiContract.ts`     |
| SvelteKit proxy (ADR-0011) | `apps/web/src/hooks.server.ts`                  |
| Auth ADR                   | `docs/adr/0004-auth-strategie.md`               |
| Proxy ADR                  | `docs/adr/0011-web-internal-reverse-proxy.md`   |
| Screen architecture        | `docs/adr/0017-frontend-screen-architecture.md` |
| Design tokens              | `docs/frontend/COLOR_SCHEME_CONCEPT.md`         |
| Full parallel-GUI guide    | `docs/frontend/PARALLEL_REACT_GUI.md`           |
| OpenAPI (runtime)          | `http://127.0.0.1:8000/openapi.json`            |

---

## Directory Conventions

```
apps/web-react/
├── CLAUDE.md              ← this file
├── package.json
├── vite.config.ts         ← port 5174, /api proxy
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── lib/
│   │   └── api/
│   │       ├── client.ts  ← apiFetch + refresh
│   │       └── types.ts   ← DTOs or generated.d.ts
│   ├── components/
│   └── pages/             ← or routes/ per router choice
```

---

## Vite Proxy Config (required)

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 5174,
    host: 'localhost',
    proxy: {
      '/api': {
        target: process.env.INTERNAL_API_URL ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```

API client:

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

await fetch(`${API_BASE}/entries`, { credentials: 'include' });
```

---

## Auth Routes to Implement (for parity testing)

| Route                  | Notes                                        |
| ---------------------- | -------------------------------------------- |
| `/auth/login`          | Cookie session via POST `/api/v1/auth/login` |
| `/auth/register`       | Email verification flow                      |
| `/auth/verify-email`   | Query: `?token=`                             |
| `/auth/reset-password` | Query: `?token=`                             |

Email links use backend `FRONTEND_BASE_URL` (default `http://localhost:5173`) until cutover.
Implement these routes in React before switching that env var.

---

## Design Guidance

- Reference SvelteKit screens in `apps/web/src/routes/` for UX parity
- Semantic color tokens from ADR-0020/0027 — avoid hardcoded hex
- Mobile-first (390px) + desktop (1280px+) — see ADR-0017
- Shell breakpoint: 768px (bottom nav → side rail)
- Product principles: no gamification, privacy-first, 60 seconds per day — see root `README.md`

---

## Implementing a Screen

1. Find the SvelteKit equivalent in `apps/web/src/routes/`
2. Grep for `apiFetch`, `api.`, or `/api/v1` in related Svelte files
3. Implement the React version using the **same endpoints**
4. Test against live API on `:8000` with proxy on `:5174`
5. Do not modify SvelteKit source

---

## Out of Scope (unless explicitly requested)

- PWA / service worker / Dexie offline sync ([ADR-0009](../../docs/adr/0009-offline-sync-nach-m4.md))
- Docker / production deployment
- Modifying `apps/web`
- Backend API changes
- Shared component library extraction to `packages/`
- CI workflow changes

---

## Environment Variables (React dev)

| Variable            | Required | Purpose                                        |
| ------------------- | -------- | ---------------------------------------------- |
| `INTERNAL_API_URL`  | Yes      | Vite proxy target (`http://127.0.0.1:8000`)    |
| `VITE_API_BASE_URL` | No       | Default `/api/v1` — do not set to absolute URL |

Backend vars (`CORS_ORIGINS`, `FRONTEND_BASE_URL`) — no change needed in proxy mode.

---

## Full Documentation

[`docs/frontend/PARALLEL_REACT_GUI.md`](../../docs/frontend/PARALLEL_REACT_GUI.md) — architecture,
environment matrix, cutover checklist, risks, FAQ.
