# Selfhost Install Guide

Last updated: 2026-07-11 (M10)

Deploy CorrelCore on your own infrastructure. Full operator reference also lives in the
[repository `docs/selfhost/INSTALL.md`](https://github.com/Sturmi77/correlcore/blob/main/docs/selfhost/INSTALL.md).

## Deployment paths

| Path               | Compose file                    | TLS                                     | Best for                   |
| ------------------ | ------------------------------- | --------------------------------------- | -------------------------- |
| **B — Quickstart** | `docker-compose.quickstart.yml` | Bind to Tailscale IP; Mailpit for email | First eval, homelab        |
| **A — Public VPS** | `docker-compose.yml`            | Traefik + Let's Encrypt                 | Internet-facing production |

**Start here:** Path B for a 10-minute local eval. Path A when you have a public domain and SMTP relay.

Existing operators on **v1.4.0** (or any earlier 1.x pin): see [Upgrade guide](upgrade.md)
(compose update to **v1.7.0**). Pre-M10 MinIO stacks are covered in the same page.

---

## Path B — Quickstart / Homelab (recommended first)

### Prerequisites

- Docker ≥ 24 and Compose v2
- Optional: Tailscale IP for remote access

### 1. Bootstrap secrets

From the repository root:

```bash
git clone https://github.com/Sturmi77/correlcore.git
cd correlcore
./scripts/bootstrap-selfhost-env.sh --quickstart
```

Optional overrides:

```bash
export TAILSCALE_IP=100.x.y.z
export WEB_HOST_PORT=3010
./scripts/bootstrap-selfhost-env.sh --quickstart
```

This writes `infra/docker/.env` with generated secrets. **Store `ENCRYPTION_KEY` offline** (printed once).

### 2. Start the stack

```bash
cd infra/docker
docker compose -f docker-compose.quickstart.yml up -d
```

Optional profiles:

```bash
# Error tracking (GlitchTip on port 8080)
docker compose -f docker-compose.quickstart.yml --profile monitoring up -d
```

The analytics **worker** starts with the default stack (no `COMPOSE_PROFILES=worker`
needed). Users opt in to the in-app digest under Settings → Analysis.

### 3. Verify

```bash
docker compose -f docker-compose.quickstart.yml ps
curl -sf "http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health"
```

Open the app at `http://${TAILSCALE_IP}:${WEB_HOST_PORT}` (default `http://127.0.0.1:3010`).

Verify-email links appear in **Mailpit**: `http://${TAILSCALE_IP}:8025`.

---

## Path A — Public VPS (Traefik + DNS)

### Prerequisites

- Linux host with Docker ≥ 24 and Compose v2
- Public ports **80** and **443**
- A domain you control
- SMTP relay for email verification

### 1. DNS records

| Record                          | Type     | Purpose                               |
| ------------------------------- | -------- | ------------------------------------- |
| `correlcore.example.com`        | A / AAAA | Web + API (`/api` via Traefik)        |
| `errors.correlcore.example.com` | A / AAAA | GlitchTip (profile `monitoring` only) |

### 2. Configure secrets

```bash
cd correlcore/infra/docker
cp .env.example .env
# Or: ../../scripts/bootstrap-selfhost-env.sh --production
```

Generate and set at minimum:

| Variable                                | Notes                                            |
| --------------------------------------- | ------------------------------------------------ |
| `DOMAIN`                                | Apex host, e.g. `correlcore.example.com`         |
| `SECRET_KEY`                            | ≥ 32 bytes, URL-safe                             |
| `ENCRYPTION_KEY`                        | Fernet key — **store outside the server backup** |
| `POSTGRES_PASSWORD` / `APP_DB_PASSWORD` | Separate passwords, no `@` or `/`                |
| `REDIS_PASSWORD`                        | ≥ 20 chars recommended                           |
| `CORS_ORIGINS` / `FRONTEND_BASE_URL`    | `https://${DOMAIN}`                              |
| `SMTP_HOST`                             | Real relay in production                         |

!!! warning "ENCRYPTION_KEY"
Encrypted mood notes cannot be decrypted without this key — even from a valid
database backup. Store it in a password manager, not only on the VPS.

### 3. Traefik static config

Edit `infra/docker/traefik/traefik.yml` — set ACME email to match `LETSENCRYPT_EMAIL`.

### 4. Start the stack

```bash
docker compose up -d
```

The **analytics worker** starts automatically (insights + GDPR cleanup). No `--profile worker` needed on Path A.

Optional monitoring:

```bash
docker compose --profile monitoring up -d
```

### 5. Verify

```bash
curl -sf "https://${DOMAIN}/api/v1/health"
docker compose ps
```

Expected: `correlcore-api`, `correlcore-web`, `correlcore-worker`, `correlcore-postgres`,
`correlcore-redis`, `correlcore-traefik` healthy. `correlcore-migrate` exits 0.

---

## Updates

Pin images for reproducible deploys — see [Container images](container-images.md):

```env
IMAGE_REGISTRY=ghcr.io/sturmi77
IMAGE_TAG=v1.7.0   # any v1.x pin works
```

```bash
docker compose pull
docker compose up -d
```

The `migrate` service runs `alembic upgrade head` before API start.

---

## Backup essentials

| Asset       | Method                                       |
| ----------- | -------------------------------------------- |
| PostgreSQL  | `pg_dump` daily                              |
| **Secrets** | `ENCRYPTION_KEY`, `SECRET_KEY` — **offline** |

```bash
docker exec correlcore-postgres pg_dump -U correlcore -Fc correlcore \
  > correlcore-$(date +%F).dump
```

Full backup/restore procedure:
[`docs/selfhost/INSTALL.md` § Backup](https://github.com/Sturmi77/correlcore/blob/main/docs/selfhost/INSTALL.md#backup-strategy).

---

## Worker freshness monitoring

The nightly worker (cleanup + insights + weekly digest) can fail silently:
the container keeps running, but the actual nightly job stops completing.
`GET /api/v1/worker/status` reports the age of the last **successful** run
per job kind so an external uptime tool can alert on that, not just on
whether the process is alive (#756).

```bash
# Set a static key so external monitors can call the endpoint without a
# browser session (leave unset to require an admin login instead):
echo 'WORKER_STATUS_API_KEY='$(openssl rand -hex 24) >> .env

curl -sf -H "X-Worker-Status-Key: ${WORKER_STATUS_API_KEY}" \
  "https://${DOMAIN}/api/v1/worker/status"
```

Example response:

```json
{
  "status": "ok",
  "generated_at": "2026-08-22T06:00:00Z",
  "jobs": [
    {
      "job_kind": "daily_bundle",
      "job_status": "fresh",
      "age_hours": 3.0,
      "stale_after_hours": 30,
      "stale": false
    },
    {
      "job_kind": "insights",
      "job_status": "fresh",
      "age_hours": 3.0,
      "stale_after_hours": 30,
      "stale": false
    },
    {
      "job_kind": "digest",
      "job_status": "fresh",
      "age_hours": 27.0,
      "stale_after_hours": 210,
      "stale": false
    }
  ]
}
```

Wire it into whatever uptime tool you already run:

- **Uptime-Kuma**: HTTP(s) monitor, add the `X-Worker-Status-Key` header,
  enable "Keyword" or "JSON Query" mode checking `status == "ok"`.
- **healthchecks.io**: use its HTTP check type against the same URL, or ping
  it from a small script/cron that curls `/worker/status` and only pings
  "success" when `status == "ok"`.
- **GlitchTip cron monitor** (if you already run the `monitoring` profile,
  see above): configure a Cron Monitor with the expected daily schedule and
  ping it from the same wrapper script.

`WORKER_STALE_AFTER_HOURS` (default `30`) controls how many hours past the
last successful `daily_bundle`/`insights` run before they're reported stale;
the weekly digest uses 7× that value automatically. Tune it up if your host
sleeps/suspends overnight.

See also [`M11_WORKER_CRON_MIGRATION.md`](https://github.com/Sturmi77/correlcore/blob/main/docs/selfhost/M11_WORKER_CRON_MIGRATION.md)
for the move from a long-running worker process to externally-triggered
cron runs (#757), which this endpoint is designed to monitor.

---

## Troubleshooting

| Symptom                     | Fix                                          |
| --------------------------- | -------------------------------------------- |
| Certificate pending         | Fix DNS / port 80; wait for propagation      |
| `migrate` exits 1           | Check `POSTGRES_PASSWORD`, `APP_DB_PASSWORD` |
| Notes garbled after restore | Wrong `ENCRYPTION_KEY`                       |
| Verify email wrong host     | Set `FRONTEND_BASE_URL=https://${DOMAIN}`    |
