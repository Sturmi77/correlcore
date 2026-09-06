# Upgrade guide — v1.7.0

Last updated: 2026-09-06

## v1.7.0 (current)

From **v1.6.0** to **v1.7.0**. Test minor — no new required env vars and **no new
blocking API changes** relative to v1.6.0.

If you are on **v1.5.0 or earlier**, complete the [v1.6.0](#v160) prerequisite
checks first (JWT access-token TTL ≤ 15 minutes; JSON `Content-Type` on
state-changing API requests), then pin/pull v1.7.0. Skipping those steps can
still prevent the API from starting or return **415** to custom clients.

| Who                  | Action                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------- |
| Production / homelab | Pin `IMAGE_TAG=v1.7.0`, pull, `up -d --remove-orphans` (run [v1.6.0](#v160) blockers first if upgrading from earlier) |
| `.env`               | **No required new vars.** Homelab stacks now start the analytics worker by default (#818) |
| Database             | `migrate` applies Alembic through **044** (`insight_sections`) if not already             |

```env
IMAGE_TAG=v1.7.0
```

```bash
docker compose pull
docker compose up -d --remove-orphans
curl -sf "https://${DOMAIN}/api/v1/health"   # "version":"1.7.0"
```

Rollback: set `IMAGE_TAG=v1.6.0` and `up -d`.

---

## v1.6.0

From **v1.5.0** (or any earlier 1.x pin) to **v1.6.0**. Security and assurance
release — **two changes can stop a running deployment**, check them first.
Canonical long form (rollback, troubleshooting, Alembic notes):
[`docs/selfhost/UPGRADE_1_6_0.md`](https://github.com/Sturmi77/correlcore/blob/main/docs/selfhost/UPGRADE_1_6_0.md)
in the repository.

| Who                  | Action                                                                           |
| -------------------- | -------------------------------------------------------------------------------- |
| Production / homelab | Check the two blockers, pin `IMAGE_TAG=v1.6.0`, pull, `up -d --remove-orphans`   |
| `.env`               | **No required new vars.** Remove a pinned `APP_VERSION`                          |
| Database             | `migrate` applies Alembic **043** (expanded tag / symptom catalogue, idempotent) |
| Custom API clients   | State-changing requests need `Content-Type: application/json`, else **415**      |

### Blocker 1 — access-token TTL capped at 15 minutes

If `.env` sets `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` above 15, the API **refuses to
start** in staging/production. Set it to `15` or remove the line.

```bash
grep JWT_ACCESS_TOKEN_EXPIRE_MINUTES .env
```

### Blocker 2 — non-JSON state-changing requests return 415

The Content-Type CSRF gate rejects bodies without `Content-Type:
application/json`. The web and Android clients already comply; your own scripts
may not.

Two routes keep their own media types and must **not** be switched to JSON:
`POST /api/v1/media/photos` (`multipart/form-data`) and
`POST /api/v1/security/csp-report` (`application/csp-report`,
`application/reports+json`).

### Remove a pinned `APP_VERSION`

The version now comes from the installed package, so `/health`, `/instance`,
OpenAPI and Sentry report the running image. A value in `.env` overrides that
and goes stale.

```bash
grep APP_VERSION .env   # remove the line if present
```

### Pin, pull, verify

```env
IMAGE_TAG=v1.6.0
```

```bash
docker compose pull
docker compose up -d --remove-orphans
docker compose logs migrate --tail=30   # "Running upgrade 042 -> 043" or at head
curl -sf "https://${DOMAIN}/api/v1/health"   # "version":"1.6.0"
```

Also note: `infra/dockge/` and `infra/dockhand/` compose files are now
**generated** (`scripts/gen_compose_stacks.py`) — do not edit them directly.

Rollback: set `IMAGE_TAG=v1.5.0` and `up -d`. Alembic 043 is additive and
idempotent, so a 1.5.0 image runs against it unchanged.

---

## v1.5.0

From **v1.4.0** (or any earlier 1.x pin) to **v1.5.0**.

| Who                  | Action                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------- |
| Production / homelab | Pin `IMAGE_TAG=v1.5.0`, drop `digest` from `COMPOSE_PROFILES`, pull, `up -d --remove-orphans` |
| `.env`               | **No required new vars.** Optional: `WORKER_STATUS_API_KEY`                                   |
| Database             | `migrate` applies Alembic **042** (`last_seen_digest_at`)                                     |

Ops traps: leftover **`digest-worker`** (duplicate weekly digests) and mixing a
**1.5.0 worker image** with a **1.4.0 `command`** (or the reverse).

### 1. Pin the release

```env
IMAGE_TAG=v1.5.0
```

### 2. Drop the old digest profile

If `.env` has `COMPOSE_PROFILES=…,digest`, remove `digest`. Then:

```bash
docker compose rm -sf digest-worker
```

Weekly digest now runs inside the analytics `worker` on Sundays (user opt-in
under Settings → Analysis). Quickstart still needs `COMPOSE_PROFILES=worker`.

### 3. Pull and recreate

```bash
cd correlcore/infra/docker
docker compose pull
docker compose up -d --remove-orphans
```

Quickstart: add `-f docker-compose.quickstart.yml` to both commands.

### 4. Verify

```bash
docker compose ps
docker compose logs migrate --tail=30
curl -sf "https://${DOMAIN}/api/v1/health"
```

`migrate` should exit 0 (upgrade to 042 or already at head). Worker stays up
via `supercronic` (03:00 UTC `--once`); trigger a job with
`docker compose exec worker python -m app.workers.analytics --once` if you
do not want to wait.

Optional freshness probe: `GET /api/v1/worker/status` (static
`WORKER_STATUS_API_KEY` or an admin session).

Rollback: set `IMAGE_TAG=v1.4.0` and `up -d` again. Do not restore
`digest-worker` unless you also revert the in-worker digest job.

---

## Older 1.x image pins

Any **`v1.x`** GHCR tag still pulls. Prefer **`v1.7.0`**.

```bash
cd correlcore/infra/docker
grep IMAGE_TAG .env
docker compose pull
docker compose up -d
```

The `migrate` service runs `alembic upgrade head` before the API starts.
See [Container images](container-images.md).

---

## M10 compose upgrade (historical — MinIO removal)

For existing production VPS operators who upgraded to M10 Sprint 1+ compose.
Read this before `git pull` if you run
[`docker-compose.yml`](https://github.com/Sturmi77/correlcore/blob/main/infra/docker/docker-compose.yml).

### Summary

| Who                      | Action required                                             |
| ------------------------ | ----------------------------------------------------------- |
| Existing production VPS  | `git pull` → `docker compose pull` → `docker compose up -d` |
| Secrets / `.env`         | **Keep unchanged**; optionally remove MinIO vars            |
| New evaluators / homelab | Use [quickstart path](index.md)                             |

M10 Sprint 1 is designed **non-breaking**: mood tracking, auth, insights
(worker), and HTTPS (Traefik) continue without new flags or profile knowledge.

### What changes (Sprint 1)

#### Production `docker-compose.yml`

| Change type   | Detail                                                    |
| ------------- | --------------------------------------------------------- |
| **Added**     | `migrate` service (Alembic before api/worker)             |
| **Added**     | YAML anchors, explicit `FRONTEND_BASE_URL` in API env     |
| **Removed**   | `minio`, `minio-init`, `minio_data` volume                |
| **Removed**   | `api.depends_on.minio`, `MINIO_*` in API environment      |
| **Unchanged** | worker, traefik, socket-proxy, mailpit, glitchtip profile |

Container count drops from **12 → 10** (two unused MinIO containers removed).

### Your `.env` — what to change

#### Required: nothing new

Keep all existing secrets:

- `SECRET_KEY`, `ENCRYPTION_KEY` (**critical — do not rotate casually**)
- `POSTGRES_*`, `APP_DB_*`, `REDIS_PASSWORD`
- `DOMAIN`, `CORS_ORIGINS`, `SMTP_*`

#### Recommended: verify before upgrade

```bash
grep -E '^(FRONTEND_BASE_URL|DOMAIN|SMTP_HOST|CORS_ORIGINS)=' .env
```

| Variable            | Production expectation     |
| ------------------- | -------------------------- |
| `FRONTEND_BASE_URL` | `https://your-domain.tld`  |
| `CORS_ORIGINS`      | `https://your-domain.tld`  |
| `SMTP_HOST`         | Real relay (not `mailpit`) |

Verify/reset email links depend on `FRONTEND_BASE_URL`.

#### Optional: remove (harmless if left)

`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT`, `MINIO_BUCKET_PHOTOS`, `MINIO_SECURE`

The API no longer reads these from compose after Sprint 1.

### Upgrade procedure (M10)

```bash
cd correlcore/infra/docker

# Do NOT overwrite .env from .env.example
grep -E '^(FRONTEND_BASE_URL|DOMAIN)=' .env

git pull
docker compose pull
docker compose up -d
```

Expected running services: traefik, socket-proxy, api, web, worker,
postgres, redis, mailpit, migrate (exited 0).

MinIO returns with **M13** photo upload via `--profile storage` (planned).
