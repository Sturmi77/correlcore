# Upgrade guide — v1.5.0 compose update

Last updated: 2026-08-25

Canonical long form (rollback, troubleshooting, Alembic notes):
[`docs/selfhost/UPGRADE_1_5_0.md`](https://github.com/Sturmi77/correlcore/blob/main/docs/selfhost/UPGRADE_1_5_0.md)
in the repository.

## v1.5.0 (current)

From **v1.4.0** (or any earlier 1.x pin) to **v1.5.0**.

| Who                  | Action                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------- |
| Production / homelab | Pin `IMAGE_TAG=v1.5.0`, drop `digest` from `COMPOSE_PROFILES`, pull, `up -d --remove-orphans` |
| `.env`               | **No required new vars.** Optional: `WORKER_STATUS_API_KEY`, `APP_VERSION=1.5.0`              |
| Database             | `migrate` applies Alembic **042** (`last_seen_digest_at`)                                     |

Ops traps: leftover **`digest-worker`** (duplicate weekly digests) and mixing a
**1.5.0 worker image** with a **1.4.0 `command`** (or the reverse).

### 1. Pin the release

```env
IMAGE_TAG=v1.5.0
APP_VERSION=1.5.0
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

Any **`v1.x`** GHCR tag still pulls. Prefer **`v1.5.0`**.

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
