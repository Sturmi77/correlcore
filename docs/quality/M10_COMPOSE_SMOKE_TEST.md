# M10 Compose Smoke Test Protocol

Last updated: 2026-07-11  
Sprint: M10-S1 (Compose & install parity)  
Operator guide: [`docs/selfhost/INSTALL.md`](../selfhost/INSTALL.md)

## Objective

Verify that Sprint 1 compose changes are syntactically valid, bootstrap correctly,
and start a minimal quickstart stack without MinIO or Traefik.

Exit criteria from [`M10_SPRINT_PLAN.md`](../M10_SPRINT_PLAN.md):

- `migrate` runs before api/worker
- MinIO removed from production compose (no functional regression)
- Quickstart path boots with bootstrap script
- Production compose validates with existing `.env` contract

## Scope

| In scope                             | Out of scope                              |
| ------------------------------------ | ----------------------------------------- |
| `docker compose config` (both files) | Full production VPS Traefik/Let's Encrypt |
| Bootstrap `--quickstart` idempotency | GlitchTip UI setup                        |
| Quickstart health endpoints          | Multi-arch image publish (Sprint 2)       |
| Migrate service ordering             | Photo upload / MinIO (M13)                |

## Environment

| Field         | Value                                                 |
| ------------- | ----------------------------------------------------- |
| Date          | 2026-07-11                                            |
| Host          | Cursor Cloud agent VM                                 |
| Compose files | `docker-compose.yml`, `docker-compose.quickstart.yml` |
| Operator      | Automated Sprint 1 verification                       |

## Procedure

### Step 1 — Static compose validation

From `infra/docker/` with required secrets in `.env` (or bootstrap first):

```bash
cd infra/docker
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.quickstart.yml config --quiet
```

**Expected:** Both commands exit 0 with no YAML or interpolation errors.

**Result (2026-07-11):** PASS — both configs validated after bootstrap.

### Step 2 — Bootstrap quickstart secrets

From repository root:

```bash
./scripts/bootstrap-selfhost-env.sh --quickstart --force
```

**Expected:**

- Writes `infra/docker/.env` with non-placeholder secrets
- Prints `ENCRYPTION_KEY` once for offline storage
- Sets `CORS_ORIGINS` and `FRONTEND_BASE_URL` from `TAILSCALE_IP` + `WEB_HOST_PORT`

**Result (2026-07-11):** PASS

### Step 3 — Quickstart stack start

```bash
cd infra/docker
docker compose -f docker-compose.quickstart.yml up -d
docker compose -f docker-compose.quickstart.yml ps
```

**Expected running:** `migrate` (exited 0), `api`, `web`, `postgres`, `redis`, `mailpit`.

**Not present:** `minio`, `traefik`, `socket-proxy`.

### Step 4 — Health checks

```bash
curl -sf "http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health"
curl -sf "http://127.0.0.1:8025/api/v1/info" | head -c 200
```

**Expected:** API health JSON; Mailpit info response.

### Step 5 — Migrate ordering

```bash
docker compose -f docker-compose.quickstart.yml logs migrate
docker inspect correlcore-quickstart-migrate --format '{{.State.ExitCode}}'
```

**Expected:** Exit code `0`; Alembic reports `upgrade head` success.

### Step 6 — Production compose diff review (no live deploy required)

Confirm production file changes against pre-M10 baseline:

| Check                                 | Expected |
| ------------------------------------- | -------- |
| `migrate` service present             | Yes      |
| `x-api-image` / `x-api-env` anchors   | Yes      |
| `FRONTEND_BASE_URL` in shared API env | Yes      |
| `minio`, `minio-init` services        | Absent   |
| `api.depends_on.minio`                | Absent   |
| `worker` without profile              | Yes      |
| Container count (base, no monitoring) | ~10      |

## Operator checklist (post-upgrade VPS)

For existing production deployments after `git pull`:

```bash
cd infra/docker
grep -E '^(FRONTEND_BASE_URL|DOMAIN)=' .env
docker compose pull
docker compose up -d
docker compose ps
curl -sf "https://${DOMAIN}/api/v1/health"
```

See [`selfhost/M10_COMPOSE_UPGRADE.md`](../selfhost/M10_COMPOSE_UPGRADE.md) for full upgrade notes.

## Sign-off

| Step                        | Status  | Notes                         |
| --------------------------- | ------- | ----------------------------- |
| Compose config (production) | PASS    | 2026-07-11                    |
| Compose config (quickstart) | PASS    | 2026-07-11                    |
| Bootstrap script            | PASS    | `--quickstart --force`        |
| Quickstart stack live       | Pending | Run Step 3–5 when images pull |
| Production VPS live         | N/A     | Operator-run on upgrade       |
