# Compose stacks — canonical matrix

Last updated: 2026-07-16

CorrelCore ships several Compose files for different operator paths. Prefer the
**canonical** files below; treat Dockhand/Dockge as thin wrappers of the same
service shape.

## Canonical

| Path                                                                                             | Use when                 | Notes                                                                   |
| ------------------------------------------------------------------------------------------------ | ------------------------ | ----------------------------------------------------------------------- |
| [`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml)                       | Public VPS + Traefik TLS | **Path A** in [`INSTALL.md`](INSTALL.md). Analytics `worker` always on. |
| [`infra/docker/docker-compose.quickstart.yml`](../../infra/docker/docker-compose.quickstart.yml) | Homelab / Tailscale eval | **Path B**. Profiles: `worker`, `digest`, `monitoring`.                 |

Bootstrap secrets: `scripts/bootstrap-selfhost-env.sh --quickstart` or `--production`.

## Secondary / published images

| Path                                                                                           | Use when                                             |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [`infra/docker/docker-compose.user-test.yml`](../../infra/docker/docker-compose.user-test.yml) | Run GHCR images for beta / user test                 |
| [`infra/dockhand/compose.yaml`](../../infra/dockhand/compose.yaml)                             | Dockhand UI; same services as quickstart-style stack |
| [`infra/dockge/compose.yaml`](../../infra/dockge/compose.yaml)                                 | Dockge UI                                            |

Env examples must stay aligned for: `SECRET_KEY`, `ENCRYPTION_KEY`,
`SLUG_HMAC_KEY`, `FRONTEND_BASE_URL` ↔ `WEB_HOST_PORT`, Redis/Postgres passwords.

## Profiles

| Profile            | Service                      | Purpose                                                       |
| ------------------ | ---------------------------- | ------------------------------------------------------------- |
| _(none / default)_ | api, web, postgres, redis, … | Core app                                                      |
| `worker`           | `worker`                     | Analytics + cleanup (`app.workers.analytics`)                 |
| `digest`           | `digest-worker`              | Weekly in-app digest (`app.workers.digest`, Sunday 17:00 UTC) |
| `monitoring`       | GlitchTip (where defined)    | Error tracking                                                |

Examples:

```bash
# Quickstart with insights worker + weekly digest
COMPOSE_PROFILES=worker,digest docker compose -f docker-compose.quickstart.yml up -d

# Production Traefik stack: analytics always on; enable digest opt-in
COMPOSE_PROFILES=digest docker compose up -d
```

Manual one-shot (any env with DB access):

```bash
cd backend && uv run --python 3.12 python -m app.workers.digest --once
```

## Drift policy

When adding an env var or service:

1. Update **canonical** `docker-compose.yml` + `docker-compose.quickstart.yml` first.
2. Mirror into user-test / dockhand / dockge in the same PR.
3. Update `.env*.example` and [`INSTALL.md`](INSTALL.md).
4. Prefer `${VAR:?…}` for secrets on production-oriented stacks.

Longer-term: generate secondary stacks from the canonical quickstart file
(tracked as open infra decision).
