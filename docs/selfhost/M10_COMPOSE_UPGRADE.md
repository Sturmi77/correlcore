# M10 Compose Upgrade Guide — Existing Selfhost Operators

Last updated: 2026-07-11

Applies when **Sprint 1** of M10 lands (compose parity + MinIO removal). Read
this before `git pull` if you run the production stack at
[`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml).

**Related:** [`INSTALL.md`](INSTALL.md) · [`M10_SPRINT_PLAN.md`](../M10_SPRINT_PLAN.md)

---

## Summary

| Who                      | Action required                                             |
| ------------------------ | ----------------------------------------------------------- |
| Existing production VPS  | `git pull` → `docker compose pull` → `docker compose up -d` |
| Secrets / `.env`         | **Keep unchanged**; optionally remove MinIO vars            |
| New evaluators / homelab | Use quickstart compose (after Sprint 1 ships)               |

M10 Sprint 1 is designed **non-breaking**: mood tracking, auth, insights
(worker), and HTTPS (Traefik) continue without new flags or profile knowledge.

---

## What changes in the repository (Sprint 1)

### Production `docker-compose.yml`

| Change type   | Detail                                                    |
| ------------- | --------------------------------------------------------- |
| **Added**     | `migrate` service (Alembic before api/worker)             |
| **Added**     | YAML anchors, explicit `FRONTEND_BASE_URL` in API env     |
| **Removed**   | `minio`, `minio-init`, `minio_data` volume                |
| **Removed**   | `api.depends_on.minio`, `MINIO_*` in API environment      |
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

| Variable            | Production expectation     |
| ------------------- | -------------------------- |
| `FRONTEND_BASE_URL` | `https://your-domain.tld`  |
| `CORS_ORIGINS`      | `https://your-domain.tld`  |
| `SMTP_HOST`         | Real relay (not `mailpit`) |

Verify/reset email links depend on `FRONTEND_BASE_URL`.

### Optional: remove (harmless if left)

```bash
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
MINIO_ENDPOINT
MINIO_BUCKET_PHOTOS
MINIO_SECURE
```

The API no longer reads these from compose after Sprint 1. Defaults in
`config.py` remain for a future M13 `storage` profile.

### Not needed for production VPS

- `COMPOSE_PROFILES` — worker and traefik still start with bare `docker compose up -d`
- Quickstart-only vars (`TAILSCALE_IP`, `WEB_HOST_PORT`)

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
# Log in; optional: trigger verify/reset email and check link host
```

Expected running services (approx.): traefik, socket-proxy, api, web, worker,
postgres, redis, mailpit, migrate (exited 0).

---

## Optional cleanup

| Action                                  | When                                   |
| --------------------------------------- | -------------------------------------- |
| `docker volume rm <project>_minio_data` | MinIO data not needed until M13 photos |
| Remove MinIO from restic/backup scripts | Update per INSTALL §Backup             |
| Delete MinIO block from `.env`          | Cosmetic                               |

**Do not delete:** postgres, redis, or traefik certificate volumes.

---

## Two deployment paths after M10

| Path               | Compose file                    | Audience                             |
| ------------------ | ------------------------------- | ------------------------------------ |
| **Quickstart**     | `docker-compose.quickstart.yml` | Homelab, Tailscale, first 10 minutes |
| **Production VPS** | `docker-compose.yml`            | Internet-facing with Traefik + TLS   |

Existing VPS installations stay on **production compose**. See
[`M10_SPRINT_PLAN.md`](../M10_SPRINT_PLAN.md) § COMPOSE_PROFILES for profile
rules on the quickstart path.

---

## Troubleshooting

| Symptom                          | Likely cause                                                | Fix                                                             |
| -------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| API stuck waiting / not starting | Old compose still has `depends_on: minio` but MinIO removed | Ensure Sprint 1 compose is fully pulled                         |
| Verify email links wrong host    | `FRONTEND_BASE_URL` unset or HTTP in prod                   | Set `https://${DOMAIN}` in `.env`, restart api                  |
| `migrate` exits 1                | DB credentials                                              | Check `POSTGRES_PASSWORD`, `APP_DB_PASSWORD` (no `@` or `/`)    |
| Insights empty                   | Worker not running                                          | `docker compose ps` — `correlcore-worker` should be **running** |

---

## Future: M10.1 unified profiles

Post-v1.0, a single compose file may use Docker profiles (`worker`, `tls`,
`monitoring`, `storage`). That will ship with an ADR and CHANGELOG migration
note. **Not required for M10 Sprint 1 upgrades.**

MinIO returns with **M13** photo upload via `--profile storage` (planned).
