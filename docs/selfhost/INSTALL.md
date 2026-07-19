# CorrelCore — Selfhost Install Guide

Last updated: 2026-07-11 (M10 Sprint 1)

Canonical operator guide for deploying CorrelCore on your own infrastructure.
Consolidates [`infra/dockhand/README.md`](../../infra/dockhand/README.md),
[`docs/RUNBOOK_DEPLOYMENT.md`](../RUNBOOK_DEPLOYMENT.md), and
[`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml).

**Related:** [`BETA_CHECKLIST.md`](BETA_CHECKLIST.md) · [`../frontend/USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md) ·
[`CONTAINER_IMAGES.md`](CONTAINER_IMAGES.md) ·
[`M10_COMPOSE_UPGRADE.md`](M10_COMPOSE_UPGRADE.md) ·
[`../adr/0005-verschluesselung-at-rest.md`](../adr/0005-verschluesselung-at-rest.md)

---

## Deployment paths

| Path                         | Compose file                                                                                                                                            | TLS / exposure                            | Best for                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------- |
| **B — Quickstart / Homelab** | [`infra/docker/docker-compose.quickstart.yml`](../../infra/docker/docker-compose.quickstart.yml)                                                        | Bind to `TAILSCALE_IP`; Mailpit for email | First eval, Tailscale, Dockhand |
| **A — Public VPS**           | [`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml)                                                                              | Traefik + Let's Encrypt on 80/443         | Internet-facing production      |
| **Legacy homelab**           | [`infra/dockhand/compose.yaml`](../../infra/dockhand/compose.yaml) or [`docker-compose.user-test.yml`](../../infra/docker/docker-compose.user-test.yml) | Same as quickstart                        | Existing Dockhand adopters      |

**Start here:** Path B for a 10-minute local eval. Path A when you have a public domain and SMTP relay.

Existing VPS operators upgrading from pre-M10 compose: [`M10_COMPOSE_UPGRADE.md`](M10_COMPOSE_UPGRADE.md).

---

## Path B — Quickstart / Homelab (recommended first)

### Prerequisites

- Docker ≥ 24 and Compose v2
- Optional: Tailscale IP for remote access from your tailnet

### 1. Bootstrap secrets

From the repository root:

```bash
./scripts/bootstrap-selfhost-env.sh --quickstart
```

Optional overrides before bootstrap:

```bash
export TAILSCALE_IP=100.x.y.z   # or 0.0.0.0 on some Synology setups
export WEB_HOST_PORT=3010
./scripts/bootstrap-selfhost-env.sh --quickstart
```

This writes `infra/docker/.env` with generated secrets. **Store `ENCRYPTION_KEY` offline** (printed once).

Manual alternative: copy [`.env.quickstart.example`](../../infra/docker/.env.quickstart.example) to `.env` and fill secrets.

### 2. Start the stack

```bash
cd correlcore/infra/docker
docker compose -f docker-compose.quickstart.yml up -d
```

Optional profiles (see [`COMPOSE_STACKS.md`](COMPOSE_STACKS.md)):

```bash
# Insights generation + unverified-account cleanup (recommended for durable homelab)
echo 'COMPOSE_PROFILES=worker' >> .env
docker compose -f docker-compose.quickstart.yml up -d

# Weekly in-app digest (Sunday 17:00 UTC) — users must opt in under Settings → Analysis
echo 'COMPOSE_PROFILES=worker,digest' >> .env
docker compose -f docker-compose.quickstart.yml up -d

# Error tracking (GlitchTip on port 8080)
docker compose -f docker-compose.quickstart.yml --profile monitoring up -d
```

### 3. Verify

```bash
docker compose -f docker-compose.quickstart.yml ps
curl -sf "http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health"
```

Open the app at `http://${TAILSCALE_IP}:${WEB_HOST_PORT}` (default `http://127.0.0.1:3010`).

Verify-email links appear in **Mailpit**: `http://${TAILSCALE_IP}:8025`.

### 4. Upgrade to production VPS

When ready for a public domain, follow Path A below. Your Postgres volume is separate per compose project — plan a migration or fresh start.

---

## Path A — Public VPS (Traefik + DNS)

### Prerequisites

- Linux host with Docker ≥ 24 and Compose v2
- Public IPv4 (and optionally IPv6) on ports **80** and **443**
- A domain you control (example: `correlcore.example.com`)
- SMTP relay for email verification (or Mailpit for non-production tests)

### 1. DNS records

Create DNS records pointing to your server **before** starting Traefik (HTTP-01 challenge).

| Record                          | Type     | Value         | Purpose                               |
| ------------------------------- | -------- | ------------- | ------------------------------------- |
| `correlcore.example.com`        | A / AAAA | `<server-ip>` | Web + API (`/api` via Traefik)        |
| `errors.correlcore.example.com` | A / AAAA | `<server-ip>` | GlitchTip (profile `monitoring` only) |

Replace `correlcore.example.com` with your real `DOMAIN` value.

Verify propagation:

```bash
dig +short correlcore.example.com A
dig +short errors.correlcore.example.com A
```

### 2. Clone and configure secrets

```bash
git clone https://github.com/Sturmi77/correlcore.git
cd correlcore/infra/docker
cp .env.example .env
```

Generate secrets (minimum set — see [`.env.example`](../../infra/docker/.env.example) for all variables):

```bash
# SECRET_KEY (JWT signing)
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

# ENCRYPTION_KEY (Fernet — CRITICAL, backup separately!)
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# Database / Redis passwords
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Or use `./scripts/bootstrap-selfhost-env.sh --production` to generate secrets into `.env`, then set domain and SMTP manually.

Edit `.env` and set at minimum:

| Variable            | Notes                                            |
| ------------------- | ------------------------------------------------ |
| `DOMAIN`            | Apex host, e.g. `correlcore.example.com`         |
| `LETSENCRYPT_EMAIL` | ACME registration email                          |
| `SECRET_KEY`        | ≥ 32 bytes, URL-safe                             |
| `ENCRYPTION_KEY`    | Fernet key — **store outside the server backup** |
| `POSTGRES_PASSWORD` | ≥ 20 chars, no `@` or `/`                        |
| `APP_DB_PASSWORD`   | Separate from `POSTGRES_PASSWORD`                |
| `REDIS_PASSWORD`    | ≥ 20 chars recommended                           |
| `CORS_ORIGINS`      | `https://${DOMAIN}` in production                |
| `FRONTEND_BASE_URL` | `https://${DOMAIN}`                              |
| `APP_ENV`           | `production` or `staging`                        |
| `SMTP_HOST`         | Real relay in production (not `mailpit`)         |

> **ENCRYPTION_KEY warning (ADR-0005):** Encrypted mood notes and custom symptom names
> cannot be decrypted without this key — even from a valid database backup. Store it in a
> password manager or offline secret store, not only on the VPS.

### 3. Traefik static config

The production stack mounts [`infra/docker/traefik/traefik.yml`](../../infra/docker/traefik/traefik.yml).
Before first deploy, set the ACME email to match `LETSENCRYPT_EMAIL`:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com # ← same as LETSENCRYPT_EMAIL in .env
```

Traefik obtains certificates via HTTP-01 on port 80. Security headers and HTTPS redirect
are defined as Docker labels on the Traefik service in `docker-compose.yml`.

**Socket proxy:** Traefik reads container labels through
[Tecnativa docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) — not a
direct `/var/run/docker.sock` mount (SEC-03).

### 4. Start the stack

```bash
cd correlcore/infra/docker
docker compose up -d
```

Optional profiles:

```bash
# Error tracking (GlitchTip at https://errors.${DOMAIN})
docker compose --profile monitoring up -d
```

The **analytics worker** starts automatically with the production stack (insights + GDPR account cleanup). No `--profile worker` needed on Path A.

Weekly **digest** is opt-in for users (`digest_enabled`) and for operators:

```bash
COMPOSE_PROFILES=digest docker compose up -d
```

After first start with `monitoring`:

```bash
docker exec -it correlcore-glitchtip ./manage.py migrate
docker exec -it correlcore-glitchtip ./manage.py createsuperuser
# Create project in GlitchTip UI → copy DSN → set GLITCHTIP_DSN in .env → redeploy api + web
```

### 5. Verify deployment

```bash
curl -sf "https://${DOMAIN}/api/v1/health"
curl -sfI "https://${DOMAIN}/" | head -5
```

Check container health:

```bash
docker compose ps
```

Expected: `correlcore-api`, `correlcore-web`, `correlcore-worker`, `correlcore-postgres`,
`correlcore-redis`, `correlcore-traefik` healthy or running. `correlcore-migrate` exits 0.

### 6. LUKS volume encryption (VPS / Hetzner)

ADR-0005 Stufe 1: encrypt the **block device** that holds Docker volumes and backup staging.

**When to use:** Any VPS where physical disk theft or provider snapshot access is in scope.
LUKS protects data at rest on a **powered-off** server; it does not replace app-level Fernet
encryption for backup files.

**Hetzner Cloud (example):**

1. Attach an encrypted volume or use full-disk LUKS on the root/data partition.
2. Mount encrypted storage at `/var/lib/docker` or a dedicated path, e.g. `/mnt/correlcore-data`.
3. Point Compose volume bind paths or Docker `data-root` to that mount.

```bash
# Example: LUKS on a dedicated data disk (destructive — adjust device names!)
sudo cryptsetup luksFormat /dev/sdb
sudo cryptsetup open /dev/sdb correlcore_crypt
sudo mkfs.ext4 /dev/mapper/correlcore_crypt
sudo mkdir -p /mnt/correlcore-data
echo 'correlcore_crypt /dev/sdb /etc/luks/correlcore.key luks' | sudo tee -a /etc/crypttab
```

Store the LUKS passphrase **separately** from `ENCRYPTION_KEY` and database passwords.
Document unlock procedure in your personal runbook (console / rescue mode).

**Limitation:** LUKS does not protect against backup theft of a logical `pg_dump` — use
restic repo encryption and Fernet field encryption (Stufe 2) together.

---

## Path B legacy — Dockhand / user-test

For existing Dockhand Git stacks, [`infra/dockhand/compose.yaml`](../../infra/dockhand/compose.yaml)
remains supported. New homelab installs should prefer
[`docker-compose.quickstart.yml`](../../infra/docker/docker-compose.quickstart.yml).

Full variable reference: [`infra/dockhand/README.md`](../../infra/dockhand/README.md).

---

## External reverse proxy (advanced)

If you already run nginx, Caddy, or Traefik on the host, you can bind CorrelCore web to
localhost only and terminate TLS on the host proxy:

1. Use quickstart compose or adapt production compose to expose web on `127.0.0.1:${WEB_HOST_PORT}` only.
2. Point your host reverse proxy at `http://127.0.0.1:${WEB_HOST_PORT}` for `/` and ensure
   `/api` is proxied to the same origin (SvelteKit proxies `/api/*` to the internal API — ADR-0011).
3. Set `FRONTEND_BASE_URL` and `CORS_ORIGINS` to your public HTTPS origin.
4. Set `COOKIE_SECURE=true` when serving over HTTPS.

This avoids running a second Traefik inside Docker. **Do not run Compose Traefik on ports
80/443 at the same time as a host Nginx** — one TLS edge only.

**Hosted reference (`correlcore.com`):** maintainer ops for Nginx-on-NAS, SMTP cutover, and
later VPS migration are tracked in
[`M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)
(not a second install guide). Sprint-1 edge:
[`runbooks/hosted-nginx-edge.md`](../runbooks/hosted-nginx-edge.md).
SMTP + one-shot cutover:
[`runbooks/hosted-cutover.md`](../runbooks/hosted-cutover.md).
Topology (IONOS marketing vs full NAS):
[`runbooks/hosted-topology-options.md`](../runbooks/hosted-topology-options.md).
Remaining work:
[`M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md).
A dedicated compose profile for external-proxy mode remains deferred (historical
“M10.1 deferred” compose item — not the M10.1 insight pipeline).

---

## Backup strategy

CorrelCore stores Art. 9 health data. Backups must be **encrypted in transit and at rest**
and **`ENCRYPTION_KEY` must never live only inside the same backup bundle**.

### What to back up

| Asset                        | Method                                                        | Retention suggestion   |
| ---------------------------- | ------------------------------------------------------------- | ---------------------- |
| PostgreSQL (`correlcore` DB) | `pg_dump` (logical)                                           | Daily, 30 days         |
| GlitchTip DB (if monitoring) | `pg_dump` database `glitchtip`                                | Weekly                 |
| Redis                        | Optional — session/rate-limit state; rebuild acceptable       | —                      |
| **Secrets**                  | `ENCRYPTION_KEY`, `SECRET_KEY`, restic password — **offline** | Permanent secure store |

### Daily PostgreSQL dump

```bash
BACKUP_DIR=/var/backups/correlcore
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%F-%H%M)

docker exec correlcore-postgres pg_dump -U correlcore -Fc correlcore \
  > "$BACKUP_DIR/correlcore-${STAMP}.dump"

# Optional: GlitchTip database
docker exec correlcore-postgres pg_dump -U correlcore -Fc glitchtip \
  > "$BACKUP_DIR/glitchtip-${STAMP}.dump" 2>/dev/null || true
```

`-Fc` (custom format) supports parallel restore with `pg_restore`.

### restic encrypted off-site copy

Install [restic](https://restic.readthedocs.io/) on the host or use the container image.
Initialize once (choose backend: local path, S3, SFTP, B2, etc.):

```bash
export RESTIC_REPOSITORY=sftp:user@backup-host:/correlcore-restic
export RESTIC_PASSWORD='<strong-repo-password-distinct-from-db-password>'

restic init   # first time only
restic backup /var/backups/correlcore \
  --tag correlcore-db \
  --host "$(hostname)"
restic forget --keep-daily 30 --prune
```

restic encrypts all repository data with AES-256-GCM (ADR-0005). The repo password is
independent of PostgreSQL credentials.

**Cron example** (`/etc/cron.d/correlcore-backup`):

```cron
15 2 * * * root /opt/correlcore/scripts/backup.sh >> /var/log/correlcore-backup.log 2>&1
```

See [`docs/quality/M9_BACKUP_RESTORE_TEST.md`](../quality/M9_BACKUP_RESTORE_TEST.md) for a
verified restore procedure.

### Secrets checklist (store outside VPS)

- [ ] `ENCRYPTION_KEY` (or `ENCRYPTION_KEYS` during rotation)
- [ ] `SECRET_KEY`
- [ ] `POSTGRES_PASSWORD` / `APP_DB_PASSWORD`
- [ ] `RESTIC_PASSWORD`
- [ ] LUKS passphrase (if applicable)

---

## Restore procedure (PostgreSQL)

**Prerequisites:** Valid `.dump` file, original `ENCRYPTION_KEY`, stack stopped or API scaled down.

```bash
# 1. Stop writers (prevents partial state during restore)
docker compose stop api worker web

# 2. Drop and recreate database (destructive!)
docker exec correlcore-postgres psql -U correlcore -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='correlcore' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS correlcore;" \
  -c "CREATE DATABASE correlcore OWNER correlcore;"

# 3. Restore
docker exec -i correlcore-postgres pg_restore -U correlcore -d correlcore --no-owner --role=correlcore \
  < /var/backups/correlcore/correlcore-YYYY-MM-DD.dump

# 4. Re-run migrations if restoring an older dump onto newer images
docker compose run --rm migrate

# 5. Start services
docker compose up -d api web worker
```

After restore, verify:

```bash
curl -sf "https://${DOMAIN}/api/v1/health"
# Log in as test user; confirm entries and encrypted notes decrypt correctly
```

If notes show decryption errors, the backup was restored with a **wrong `ENCRYPTION_KEY`**.

### Restore from restic

```bash
export RESTIC_REPOSITORY=...
export RESTIC_PASSWORD=...
restic restore latest --target /tmp/restic-restore --path /var/backups/correlcore
# Then run pg_restore as above from /tmp/restic-restore/...
```

---

## Updates

Pin images for reproducible deploys:

```env
IMAGE_REGISTRY=ghcr.io/sturmi77   # or docker.io/<username> for Docker Hub
IMAGE_TAG=v1.0.6                  # any v1.0.x pin works; or sha-<short> from GHCR / Docker Hub
```

See [`CONTAINER_IMAGES.md`](CONTAINER_IMAGES.md) for registry and tag details.

```bash
docker compose pull
docker compose up -d
```

The `migrate` service runs `alembic upgrade head` before API start. See
[`RUNBOOK_DEPLOYMENT.md`](../RUNBOOK_DEPLOYMENT.md) for Dockerfile and Synology pitfalls.

---

## User documentation

End-user workflows (registration, daily entry, export, privacy settings) are catalogued in
[`docs/frontend/USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md).

Beta operators: [`BETA_ONBOARDING.md`](BETA_ONBOARDING.md) · Testers: [`BETA_CHECKLIST.md`](BETA_CHECKLIST.md)

---

## Troubleshooting

| Symptom                                            | Likely cause                                    | Fix                                                |
| -------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------- |
| Traefik won't start                                | Missing `traefik/traefik.yml` or bad ACME email | Check mount path; sync email with `.env`           |
| Certificate pending                                | DNS not propagated or port 80 blocked           | Fix DNS / firewall; wait for propagation           |
| `bind: cannot assign requested address` (Synology) | Tailscale userspace mode                        | Set `TAILSCALE_IP=0.0.0.0` — see runbook §2        |
| Login works but notes empty/garbled                | Wrong `ENCRYPTION_KEY` after restore            | Restore correct key from offline backup            |
| `migrate` exits 1                                  | DB credentials or stale volume                  | Check `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, logs |

Further reading: [`docs/runbooks/incident-response.md`](../runbooks/incident-response.md),
[`docs/RUNBOOK_KEY_ROTATION.md`](../RUNBOOK_KEY_ROTATION.md).
