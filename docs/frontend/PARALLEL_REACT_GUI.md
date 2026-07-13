# Parallel React GUI Experiment

**Status:** Documentation + scaffold planned — production GUI remains SvelteKit until cutover decision.

## Zusammenfassung (DE)

CorrelCore kann ein **zweites React-Frontend** parallel zum bestehenden **SvelteKit-GUI** betreiben. Beide teilen sich dieselbe FastAPI-API und Datenbank. Das SvelteKit-GUI läuft auf Port **5173**, das React-Experiment auf Port **5174**. Für Auth und Cookies wird in beiden Fällen ein **Same-Origin-API-Proxy** verwendet (relativer Pfad `/api/v1`), nicht direkte Calls an `:8000`. Backend-Änderungen sind für lokalen Parallelbetrieb **nicht nötig**. Agent-Kontext für Claude Design / Cursor: [`apps/web-react/CLAUDE.md`](../../apps/web-react/CLAUDE.md).

---

## Executive Summary (EN)

CorrelCore supports running an **experimental React frontend** in parallel to the **production SvelteKit GUI**. Both frontends share the same FastAPI backend and database. SvelteKit stays on port **5173**; React runs on port **5174**. Authentication uses **HttpOnly cookies** with a **same-origin reverse proxy** (`/api/v1`) — the same pattern as [ADR-0011](../adr/0011-web-internal-reverse-proxy.md). No backend changes are required for local parallel development. The production deploy pipeline is unchanged until an explicit cutover decision.

---

## Architecture Overview

```mermaid
flowchart LR
  subgraph browsers [Browser]
    B1["Tab: localhost:5173"]
    B2["Tab: localhost:5174"]
  end
  subgraph frontends [Frontends]
    SK["apps/web SvelteKit"]
    RE["apps/web-react React"]
  end
  subgraph backend [Shared Backend]
    API["FastAPI :8000"]
    PG["PostgreSQL"]
    RD["Redis"]
  end
  B1 --> SK
  B2 --> RE
  SK -->|"/api/* same-origin proxy"| API
  RE -->|"/api/* Vite dev proxy"| API
  API --> PG
  API --> RD
```

| Component      | Package                                     | Port (dev) | Role                            |
| -------------- | ------------------------------------------- | ---------- | ------------------------------- |
| Production GUI | `@correlcore/web` (`apps/web/`)             | 5173       | SvelteKit — canonical, deployed |
| Experiment GUI | `@correlcore/web-react` (`apps/web-react/`) | 5174       | React — evaluation only         |
| API            | FastAPI (`backend/`)                        | 8000       | Shared by both frontends        |

---

## Monorepo Layout

```
apps/
├── web/           @correlcore/web       — production GUI (SvelteKit)
└── web-react/     @correlcore/web-react — experimental GUI (React)
backend/           FastAPI, shared
packages/          (future: shared api-types, design tokens)
```

The pnpm workspace ([`pnpm-workspace.yaml`](../../pnpm-workspace.yaml)) already includes `apps/*`. Only `@correlcore/web` exists today; `@correlcore/web-react` is added when the scaffold lands.

---

## API Proxy Strategy

### Why relative `/api/v1`

The browser bundle must call the API via a **relative path** (`/api/v1`), not an absolute URL like `http://localhost:8000/api/v1`. Reasons:

1. **Build-time independence** — `VITE_*` vars are baked at build time; runtime topology changes should not require rebuilds ([ADR-0011](../adr/0011-web-internal-reverse-proxy.md)).
2. **Cookie auth** — HttpOnly cookies use `SameSite=strict` ([`backend/app/core/auth_cookies.py`](../../backend/app/core/auth_cookies.py)). They are set for the frontend origin. Cross-origin direct API calls break login.
3. **CORS simplification** — Same-origin requests do not need CORS allowlisting.

### SvelteKit (production)

[`apps/web/src/hooks.server.ts`](../../apps/web/src/hooks.server.ts) proxies every `/api/*` request to `INTERNAL_API_URL` (default `http://api:8000` in Docker, `http://127.0.0.1:8000` locally).

```typescript
// Browser sees:  http://localhost:5173/api/v1/...
// Proxy forwards: http://127.0.0.1:8000/api/v1/...
const API_BASE = '/api/v1';
```

### React (experiment, dev)

Vite dev server proxy in `apps/web-react/vite.config.ts`:

```typescript
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

### React (production, future cutover)

SvelteKit uses `adapter-node` + `hooks.server.ts`. For React production you need one of:

- Express/Fastify middleware proxying `/api/*` (ADR-0011 parity)
- nginx reverse proxy in the container
- Adapt the existing [`apps/web/Dockerfile`](../../apps/web/Dockerfile) pattern

During the **experiment phase**, local dev proxy is sufficient. Docker/CI changes happen only at cutover.

### Anti-pattern: direct API calls

Do **not** configure `VITE_API_BASE_URL=http://localhost:8000/api/v1` for browser-side requests. This causes:

- CORS preflight on every request
- Cookies set on `:8000`, not sent from `:5174` (`SameSite=strict`)
- Broken login/session refresh

### Proxy approach — trade-offs

The proxy pattern is the **recommended default** for CorrelCore (see [ADR-0011](../adr/0011-web-internal-reverse-proxy.md)), but it has real costs. Understand these before choosing an alternative.

#### Technical trade-offs

| Drawback                         | Description                                                                                                                                                                                                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Extra hop**                    | Every API request passes through the frontend server (SvelteKit `handle` hook or Vite dev proxy) before reaching FastAPI. Adds latency and a failure point — if the proxy is down, the SPA gets 502 even when the API is healthy.                                  |
| **Two proxy implementations**    | SvelteKit uses [`hooks.server.ts`](../../apps/web/src/hooks.server.ts) (production-ready). React uses Vite `server.proxy` (dev-only). React production requires a separate reverse proxy (Express/nginx) at cutover — extra work that direct API calls would skip. |
| **Dev ≠ production**             | Vite dev proxy and SvelteKit `handle` do not behave identically (headers, timeouts, error bodies, streaming). Bugs may appear in one environment only.                                                                                                             |
| **WebSockets / SSE / streaming** | The current SvelteKit proxy targets REST. WebSockets, Server-Sent Events, or large uploads need explicit proxy configuration and may behave differently in Vite vs production.                                                                                     |
| **Indirect debugging**           | Browser DevTools show requests to `:5173` / `:5174`, not `:8000`. Troubleshooting requires checking both frontend proxy logs and backend logs.                                                                                                                     |

#### Architecture trade-offs

| Drawback                               | Description                                                                                                                                                                                                                                                                             |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Separate origins in parallel dev**   | `:5173` and `:5174` are different **origins** for CORS/JS, but HttpOnly cookies are **host-scoped** (no `Domain`, path `/api`) — a login on one `localhost` port is visible to the other when paths match. Use `127.0.0.1` vs `localhost` consistently; those are separate cookie jars. |
| **Single `FRONTEND_BASE_URL`**         | Email verify/reset links point to one canonical URL (default `:5173`). The React GUI on `:5174` does not receive those links unless auth routes are implemented there and the env var is switched.                                                                                      |
| **No benefit for non-browser clients** | Mobile apps, external tools, or Capacitor with bearer tokens talk to the API directly anyway ([ADR-0006](../adr/0006-cookie-auth-mit-capacitor-migration.md)). The web proxy does not help those clients.                                                                               |
| **ADR-0011 assumes one entry point**   | Production design is one public web origin with internal API. Running two production frontends requires infra changes (second compose service, Traefik route) — parallel ports are for **dev/evaluation only**.                                                                         |

#### Operations trade-offs

| Drawback                                   | Description                                                                                                                                                                                                                             |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Heavier frontend container**             | Production web container carries proxy logic. An edge reverse proxy (Traefik/nginx) could do the same — risk of duplicate proxies or unclear ownership if both are configured.                                                          |
| **Client IP / rate limiting**              | Backend rate limiting may trust `X-Forwarded-For` when `RATE_LIMIT_TRUST_PROXY_HEADERS=true`. The SvelteKit proxy strips browser-supplied forwarding headers (correct for security) — edge proxies must set trusted headers explicitly. |
| **Two production frontends not supported** | Compose/Traefik templates define one `web` service. Parallel public GUIs need custom infra.                                                                                                                                             |

#### Alternative: direct API calls (and why CorrelCore avoids them)

Calling `http://localhost:8000/api/v1` directly from the browser avoids the proxy hop but introduces different problems:

| Problem                     | Without proxy                                                                                             |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| Cookies (`SameSite=strict`) | Login from `:5174` → API on `:8000` **breaks** — cookies are not sent cross-origin                        |
| CORS                        | Every frontend origin must be listed in `CORS_ORIGINS`                                                    |
| Build-time coupling         | Absolute API URL baked into the bundle ([ADR-0011 background](../adr/0011-web-internal-reverse-proxy.md)) |
| Exposed API port            | `:8000` must be reachable from the browser                                                                |
| Security                    | Larger attack surface in dev/homelab setups                                                               |

**Verdict for this experiment:** Proxy trade-offs (extra hop, separate sessions, React production proxy TBD) are **acceptable** for parallel SvelteKit + React evaluation. The cookie/CORS/build-time problems of direct API calls are worse for CorrelCore's auth model.

---

## Authentication and Cookies

| Aspect            | Behavior                                                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Mechanism         | HttpOnly cookies (`access_token`, `refresh_token`)                                                                          |
| SameSite          | `strict` — requires same-origin proxy                                                                                       |
| Cookie path       | `/api` (access), `/api/v1/auth/refresh` (refresh)                                                                           |
| Secure flag       | Off in `APP_ENV=development`, on in production                                                                              |
| Cookie scope      | Host + path (`/api`) — **not port-scoped**; `localhost:5173` and `localhost:5174` share cookies when the proxy path matches |
| Origins (CORS/JS) | `:5173` and `:5174` are different origins — separate `localStorage`, service workers, and JS context                        |

Reference implementation: [`apps/web/src/lib/api/client.ts`](../../apps/web/src/lib/api/client.ts)

- `credentials: 'include'` on all requests
- Single-flight refresh on 401 → `POST /auth/refresh`, then replay original request once

Related ADRs:

- [ADR-0004 — Auth strategy](../adr/0004-auth-strategie.md)
- [ADR-0006 — Cookie auth + Capacitor migration](../adr/0006-cookie-auth-mit-capacitor-migration.md)

---

## Environment Variables

| Variable            | SvelteKit                      | React             | Backend change?            |
| ------------------- | ------------------------------ | ----------------- | -------------------------- |
| `INTERNAL_API_URL`  | `hooks.server.ts` proxy target | Vite proxy target | No                         |
| `CORS_ORIGINS`      | Not used (proxy)               | Not used (proxy)  | No in proxy mode           |
| `FRONTEND_BASE_URL` | Email verify/reset links       | Email links       | Keep `:5173` until cutover |
| `VITE_API_BASE_URL` | `/api/v1` (fixed)              | `/api/v1` (fixed) | No                         |

### Direct API mode (not recommended)

If a frontend calls the API directly on port 8000:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174
```

Note: `localhost` and `127.0.0.1` are **different origins** for both CORS and cookies. Stay consistent.

Default backend CORS ([`backend/app/core/config.py`](../../backend/app/core/config.py)):

```python
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
```

Add `:5174` only if needed for direct API access.

---

## Local Development

### Prerequisites

Same as main app — see [`AGENTS.md`](../../AGENTS.md) and [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md):

- PostgreSQL 16 (pgvector), Redis 7, optional Mailpit
- Backend migrations applied
- Node 22, pnpm 11, Python 3.12, uv

### Step-by-step

```bash
# 1. Infrastructure (once)
docker run -d --name correlcore-postgres \
  -e POSTGRES_USER=correlcore -e POSTGRES_PASSWORD=correlcore \
  -e POSTGRES_DB=correlcore -p 5432:5432 pgvector/pgvector:pg16

docker run -d --name correlcore-redis -p 6379:6379 \
  redis:7-alpine redis-server --requirepass changeme

# 2. Backend
cd backend
export APP_ENV=development
export DATABASE_URL='postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore'
export REDIS_URL='redis://:changeme@localhost:6379/0'
export SECRET_KEY='local-dev-secret-key-min-32-bytes-long-padding'
export ENCRYPTION_KEY='<valid-fernet-key>'
export CORS_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'
export SMTP_HOST=localhost SMTP_PORT=1025
uv run --python 3.12 alembic -c migrations/alembic.ini upgrade head
uv run --python 3.12 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2** (repo root — API keeps running in terminal 1):

```bash
# 3. SvelteKit (production GUI — unchanged)
export INTERNAL_API_URL=http://127.0.0.1:8000
pnpm dev
# → http://localhost:5173

# 4. React experiment (after apps/web-react scaffold exists — scripts not in root package.json yet)
export INTERNAL_API_URL=http://127.0.0.1:8000
pnpm dev:react   # planned — see Package Scripts below
# → http://localhost:5174

# Or both frontends in one terminal (planned):
pnpm dev:all
```

**Vite bind quirk:** Dev server may listen on `localhost` only. Use `http://localhost:5174/`, not `127.0.0.1:5174`.

Playwright already runs a second SvelteKit instance on port 4173 ([`apps/web/playwright.config.ts`](../../apps/web/playwright.config.ts)) — the same `--port` pattern applies.

---

## Package Scripts

Root [`package.json`](../../package.json) — **planned** after `apps/web-react` scaffold (not yet present on `main`):

```json
{
  "dev": "pnpm --filter @correlcore/web dev",
  "dev:react": "pnpm --filter @correlcore/web-react dev",
  "dev:all": "pnpm --parallel --filter @correlcore/web --filter @correlcore/web-react dev"
}
```

Until then, use `pnpm --filter @correlcore/web dev` only; see [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md).

---

## API Contract and Types

| Resource                    | Location                                                                                       |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| OpenAPI (runtime)           | `http://127.0.0.1:8000/openapi.json`                                                           |
| Frontend contract constants | [`apps/web/src/lib/contracts/apiContract.ts`](../../apps/web/src/lib/contracts/apiContract.ts) |
| Contract strategy           | [`docs/API_CONTRACTS.md`](../API_CONTRACTS.md)                                                 |
| Backend contract test       | `backend/tests/test_api_contract.py`                                                           |

Recommended for React: hand-written `apiFetch` wrapper + optional `openapi-typescript` generation per [API Contract Strategy](../API_CONTRACTS.md). Do not introduce a generated runtime client until it preserves single-flight cookie refresh.

---

## What NOT to Change During the Experiment

- `apps/web/**` — no refactoring for React compatibility
- Backend routes or auth logic
- Docker / CI / Compose (until cutover)
- Production deploy pipeline

---

## Claude Design Workflow

When using Claude or Cursor to design and implement a new UI in React:

1. **Leave SvelteKit untouched** — continue `pnpm dev` on 5173 for reference and production work.
2. **Build in `apps/web-react/`** — port 5174, agent context in [`CLAUDE.md`](../../apps/web-react/CLAUDE.md).
3. **Use the same API endpoints** via relative `/api/v1`.
4. **No feature-parity requirement initially** — build only screens you want to compare (e.g. Home, Trends).
5. **Reuse design tokens** — copy Tailwind/CSS variables from SvelteKit or see [`COLOR_SCHEME_CONCEPT.md`](COLOR_SCHEME_CONCEPT.md).
6. **Use SvelteKit screens as UX benchmark** — grep `apps/web/src/routes/` for equivalent flows.

---

## Cutover Checklist (when React wins)

- [ ] Production reverse proxy (Express/nginx) for `/api/*`
- [ ] `apps/web-react/Dockerfile`
- [ ] CI: [`.github/workflows/ci-web.yml`](../../.github/workflows/ci-web.yml) → React build target
- [ ] `FRONTEND_BASE_URL`, `CORS_ORIGINS`, Traefik/Compose routes
- [ ] Auth routes: `/auth/login`, `/auth/register`, `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password`
- [ ] PWA/offline scope (Dexie sync — [ADR-0009](../adr/0009-offline-sync-nach-m4.md))
- [ ] Archive or remove `apps/web`

Until then: **dev/evaluation only** — no infra changes required.

```mermaid
flowchart TD
  A["Experiment: apps/web-react on :5174"] --> B{React superior?}
  B -->|No| C["SvelteKit remains apps/web"]
  B -->|Yes| D["Replace or rename apps/web"]
  D --> E["Docker / CI / FRONTEND_BASE_URL"]
```

---

## Risks and Limitations

| Risk                     | Impact                                         | Mitigation                                               |
| ------------------------ | ---------------------------------------------- | -------------------------------------------------------- |
| Email verify/reset links | Point to `FRONTEND_BASE_URL` (default `:5173`) | Implement same auth routes in React before switching URL |
| Code duplication         | API client, types, utils                       | Accept during experiment; extract to `packages/` later   |
| No PWA/offline in React  | No service worker, no Dexie sync               | Document as known gap                                    |
| Two production frontends | Not supported in Compose                       | Dev/eval only                                            |
| Independent sessions     | Separate logins per port                       | Expected — same DB data when both authenticated          |

---

## FAQ

**Can I be logged in to both GUIs at the same time?**  
On `localhost`, yes for **cookies** (host-scoped, shared across ports). Each port still has its own origin for JS storage and service workers. Use the same host (`localhost` or `127.0.0.1`) consistently.

**Do I need a second backend?**  
No. One API instance serves both frontends.

**Must I change CORS?**  
Not if both frontends use the proxy pattern (relative `/api/v1`).

**What about CI?**  
React app gets its own lint/test when scaffolded. Main CI unchanged until cutover.

**Why React alongside SvelteKit?**  
To evaluate an alternative UI (e.g. Claude Design output) without disrupting the production GUI. Switch only if the experiment proves superior.

---

## Related Documentation

- Agent context: [`apps/web-react/CLAUDE.md`](../../apps/web-react/CLAUDE.md)
- Cursor Cloud: [`AGENTS.md`](../../AGENTS.md)
- Development guide: [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md)
- Frontend status: [`docs/frontend/FRONTEND_STATUS.md`](FRONTEND_STATUS.md)
- Proxy ADR: [`docs/adr/0011-web-internal-reverse-proxy.md`](../adr/0011-web-internal-reverse-proxy.md)
