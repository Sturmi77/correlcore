# CorrelCore — Selfhost Install Guide

Last updated: 2026-07-11 (M9 Sprint 3)

Canonical operator guide for deploying CorrelCore on your own infrastructure.
Consolidates [`infra/dockhand/README.md`](../../infra/dockhand/README.md),
[`docs/RUNBOOK_DEPLOYMENT.md`](../RUNBOOK_DEPLOYMENT.md), and
[`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml).

**Related:** [`BETA_CHECKLIST.md`](BETA_CHECKLIST.md) · [`../frontend/USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md) ·
[`../adr/0005-verschluesselung-at-rest.md`](../adr/0005-verschluesselung-at-rest.md)

---

## Deployment paths

| Path                      | Compose file                                                                                                                                                         | TLS / exposure                                  | Best for                                |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------- |
| **A — Public VPS**        | [`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml)                                                                                           | Traefik + Let's Encrypt on 80/443               | Internet-facing beta / production       |
| **B — Homelab / Tailnet** | [`infra/dockhand/compose.yaml`](../../infra/dockhand/compose.yaml) or [`infra/docker/docker-compose.user-test.yml`](../../infra/docker/docker-compose.user-test.yml) | No Traefik; bind to `TAILSCALE_IP` or `0.0.0.0` | Dockhand, Dockge, Synology, private LAN |

Path A is the M9 acceptance target (Compose + Traefik + DNS). Path B is documented in
[`infra/dockhand/README.md`](../../infra/dockhand/README.md) — use it when you do not need a public domain.

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

# Database / Redis / MinIO passwords
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Edit `.env` and set at minimum:

| Variable              | Notes                                            |
| --------------------- | ------------------------------------------------ |
| `DOMAIN`              | Apex host, e.g. `correlcore.example.com`         |
| `LETSENCRYPT_EMAIL`   | ACME registration email                          |
| `SECRET_KEY`          | ≥ 32 bytes, URL-safe                             |
| `ENCRYPTION_KEY`      | Fernet key — **store outside the server backup** |
| `POSTGRES_PASSWORD`   | ≥ 20 chars, no `@` or `/`                        |
| `APP_DB_PASSWORD`     | Separate from `POSTGRES_PASSWORD`                |
| `REDIS_PASSWORD`      | ≥ 20 chars recommended                           |
| `MINIO_ROOT_PASSWORD` | MinIO root credential                            |
| `CORS_ORIGINS`        | `https://${DOMAIN}` in production                |
| `FRONTEND_BASE_URL`   | `https://${DOMAIN}`                              |
| `APP_ENV`             | `production` or `staging`                        |

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

# Analytics worker + unverified-account cleanup
docker compose --profile worker up -d
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

Expected: `correlcore-api`, `correlcore-web`, `correlcore-postgres`, `correlcore-redis`,
`correlcore-minio`, `correlcore-traefik` healthy or running.

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

## Path B — Homelab / Tailnet (summary)

For private testing without public DNS:

1. Use [`infra/dockhand/compose.yaml`](../../infra/dockhand/compose.yaml) (Dockhand Git stack or manual adopt).
2. Copy secrets from [`infra/dockhand/.env.example`](../../infra/dockhand/.env.example).
3. Set `TAILSCALE_IP` — on Synology with Tailscale userspace mode use `0.0.0.0` (see
   [`RUNBOOK_DEPLOYMENT.md`](../RUNBOOK_DEPLOYMENT.md) §2).
4. Web reachable at `http://<tailscale-ip>:3010`; API proxied via web (`INTERNAL_API_URL`).

Full variable reference: [`infra/dockhand/README.md`](../../infra/dockhand/README.md).

---

## Backup strategy

CorrelCore stores Art. 9 health data. Backups must be **encrypted in transit and at rest**
and **`ENCRYPTION_KEY` must never live only inside the same backup bundle**.

### What to back up

| Asset                        | Method                                                        | Retention suggestion   |
| ---------------------------- | ------------------------------------------------------------- | ---------------------- |
| PostgreSQL (`correlcore` DB) | `pg_dump` (logical)                                           | Daily, 30 days         |
| GlitchTip DB (if monitoring) | `pg_dump` database `glitchtip`                                | Weekly                 |
| MinIO object data            | restic path backup of volume                                  | Daily                  |
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
IMAGE_TAG=v0.3.0   # or sha-<short> from GHCR
```

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
