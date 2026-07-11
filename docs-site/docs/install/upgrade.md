# M10 Compose Upgrade Guide

Last updated: 2026-07-11

For existing production VPS operators upgrading to M10 Sprint 1+ compose.
Read this before `git pull` if you run
[`docker-compose.yml`](https://github.com/Sturmi77/correlcore/blob/main/infra/docker/docker-compose.yml).

**Related:** [Install overview](index.md)

---

## Summary

| Who                         | Action required                                      |
| --------------------------- | ---------------------------------------------------- |
| Existing production VPS     | `git pull` → `docker compose pull` → `docker compose up -d` |
| Secrets / `.env`            | **Keep unchanged**; optionally remove MinIO vars     |
| New evaluators / homelab    | Use [quickstart path](index.md) |

M10 Sprint 1 is designed **non-breaking**: mood tracking, auth, insights
(worker), and HTTPS (Traefik) continue without new flags or profile knowledge.

---

## What changes (Sprint 1)

### Production `docker-compose.yml`

| Change type | Detail |
| ----------- | ------ |
| **Added**   | `migrate` service (Alembic before api/worker)        |
| **Added**   | YAML anchors, explicit `FRONTEND_BASE_URL` in API env |
| **Removed** | `minio`, `minio-init`, `minio_data` volume           |
| **Removed** | `api.depends_on.minio`, `MINIO_*` in API environment |
| **Unchanged** | worker, traefik, socket-proxy, mailpit, glitchtip profile |

Container count drops from **12 → 10** (two unused MinIO containers removed).

### New files (quickstart path — optional for existing VPS)

- `docker-compose.quickstart.yml`
- `.env.quickstart.example`
- `scripts/bootstrap-selfhost-env.sh --quickstart`

Existing VPS operators **do not need** the quickstart compose unless switching paths.

---

## Your `.env` — what to change

### Required: nothing new

Keep all existing secrets:

- `SECRET_KEY`, `ENCRYPTION_KEY` (**critical — do not rotate casually**)
- `POSTGRES_*`, `APP_DB_*`, `REDIS_PASSWORD`
- `DOMAIN`, `CORS_ORIGINS`, `SMTP_*`

### Recommended: verify before upgrade

```bash
grep -E '^(FRONTEND_BASE_URL|DOMAIN|SMTP_HOST|CORS_ORIGINS)=' .env
```

| Variable              | Production expectation        |
| --------------------- | ----------------------------- |
| `FRONTEND_BASE_URL`   | `https://your-domain.tld`     |
| `CORS_ORIGINS`        | `https://your-domain.tld`     |
| `SMTP_HOST`           | Real relay (not `mailpit`)    |

Verify/reset email links depend on `FRONTEND_BASE_URL`.

### Optional: remove (harmless if left)

`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT`, `MINIO_BUCKET_PHOTOS`, `MINIO_SECURE`

The API no longer reads these from compose after Sprint 1.

---

## Upgrade procedure

```bash
cd correlcore/infra/docker

# Do NOT overwrite .env from .env.example
grep -E '^(FRONTEND_BASE_URL|DOMAIN)=' .env

git pull
docker compose pull
docker compose up -d
```

### What happens on `up -d`

1. **`migrate`** runs once (`alembic upgrade head`) — idempotent
2. **MinIO containers** are stopped and removed (no product feature used them)
3. **api, web, worker, traefik** restart with updated config

### Verify

```bash
docker compose ps
curl -sf "https://${DOMAIN}/api/v1/health"
```

Expected running services: traefik, socket-proxy, api, web, worker,
postgres, redis, mailpit, migrate (exited 0).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| API stuck waiting | Old compose has `depends_on: minio` | Ensure Sprint 1 compose is fully pulled |
| Verify email wrong host | `FRONTEND_BASE_URL` unset | Set `https://${DOMAIN}` in `.env`, restart api |
| `migrate` exits 1 | DB credentials | Check passwords (no `@` or `/`) |
| Insights empty | Worker not running | `correlcore-worker` should be **running** |

MinIO returns with **M13** photo upload via `--profile storage` (planned).
