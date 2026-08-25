# Upgrade to 1.5.0 — existing selfhost / hosted operators

Last updated: 2026-08-25

Step-by-step compose update from **v1.4.0** (or any earlier 1.x pin) to
**v1.5.0**. Read this before `docker compose pull`.

**Related:** [`INSTALL.md`](INSTALL.md) · [`COMPOSE_STACKS.md`](COMPOSE_STACKS.md) ·
[`M11_WORKER_CRON_MIGRATION.md`](M11_WORKER_CRON_MIGRATION.md) (cron detail) ·
docs-site [Upgrade](https://sturmi77.github.io/correlcore/install/upgrade/)

---

## Summary

| Who                     | Action                                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------------- |
| Production VPS (Path A) | Pin `IMAGE_TAG=v1.5.0`, drop `digest` from profiles, pull, `up -d --remove-orphans`           |
| Quickstart / homelab    | Same, with `-f docker-compose.quickstart.yml`                                                 |
| GHCR user-test stack    | Same, with `-f docker-compose.user-test.yml`                                                  |
| Secrets / `.env`        | **No required new vars.** Optional: `WORKER_STATUS_API_KEY`. Pin `IMAGE_TAG` / `APP_VERSION`. |
| Database                | `migrate` runs Alembic to **042** (`last_seen_digest_at`). Additive, zero-downtime.           |

The upgrade is designed **non-breaking** for users: auth, entries, insights, and
HTTPS stay up. The two ops traps are a leftover **`digest-worker`** (duplicate
weekly snapshots) and an **old worker `command`** (sleep-loop image vs
supercronic compose, or the reverse).

---

## What changed since 1.4.0 (ops-relevant)

| Area             | 1.4.0                                                         | 1.5.0                                                                                                                                      |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Weekly digest    | Optional compose profile `digest` + `digest-worker` container | Generated **Sundays inside the analytics `worker`**. No `digest` profile. User opt-in: Settings → Analyse (`digest_enabled`, default off). |
| Worker process   | Long-lived `python -m app.workers.analytics` sleep loop       | `supercronic` + `python -m app.workers.analytics --once` at 03:00 UTC                                                                      |
| Worker freshness | Container up ≠ job succeeding                                 | `GET /api/v1/worker/status`                                                                                                                |
| Alembic head     | 041 (if you were on 1.4.0)                                    | **042** — `user_preferences.last_seen_digest_at` (digest modal)                                                                            |
| Landing          | Marketing page + instance mode                                | Two-path IA (try vs self-host); APK not above the fold                                                                                     |
| Required `.env`  | unchanged                                                     | unchanged                                                                                                                                  |

Jumping from **&lt; 1.4.0** also applies 039–041 (leisure default tags, `users.is_admin`
backfill of existing accounts to admin, `admin_audit_log`). If you are already on
1.4.0, only **042** is new.

---

## Before you start

1. **Backup Postgres** (and note `ENCRYPTION_KEY` is still required to read data).
2. Record current pins:

   ```bash
   cd correlcore/infra/docker   # or your compose directory
   grep -E '^(IMAGE_TAG|APP_VERSION|COMPOSE_PROFILES)=' .env || true
   docker compose ps
   ```

3. Confirm you can roll back: previous `IMAGE_TAG` (e.g. `v1.4.0`) still exists
   on GHCR.

---

## Step-by-step

### 1. Update compose files (git operators)

If this directory is a git checkout:

```bash
cd correlcore
git fetch origin
git checkout main
git pull --ff-only origin main
```

If you only pin images and keep a local compose copy, copy the 1.5.0
`infra/docker/docker-compose*.yml` (or `git pull` just those files). The
**worker `command:`** must be:

```yaml
command: ['supercronic', '-passthrough-logs', '/app/crontab/worker.crontab']
```

Do **not** mix a 1.5.0 image with a 1.4.0 compose `command: ['python', '-m', 'app.workers.analytics']`
(or the reverse): supercronic is baked into the 1.5.0 API/worker image.

### 2. Pin the release in `.env`

```bash
# infra/docker/.env — do not overwrite the whole file from .env.example
```

Set (or change):

```env
IMAGE_TAG=v1.5.0
APP_VERSION=1.5.0
```

`APP_VERSION` is optional but keeps `/api/v1/health`, `/api/v1/instance`, and
error-tracking labels aligned with the image.

### 3. Remove the old digest profile (required if you ever enabled it)

```bash
grep COMPOSE_PROFILES .env
```

- If the value contains `digest`, delete that token. Example:
  `COMPOSE_PROFILES=worker,digest` → `COMPOSE_PROFILES=worker`
- Quickstart still needs `COMPOSE_PROFILES=worker` (or `--profile worker`) for
  insights + weekly digest. Production `docker-compose.yml` already runs
  `worker` without a profile.

Then stop and remove a leftover container **once**:

```bash
docker compose rm -sf digest-worker
```

Harmless if the service does not exist. If you skip this and only `up -d`
without `--remove-orphans`, an old `digest-worker` on a stale image can keep
writing **duplicate** weekly digest rows.

### 4. Pull and recreate

**Path A — production** (`docker-compose.yml`):

```bash
cd correlcore/infra/docker
docker compose pull
docker compose up -d --remove-orphans
```

**Path B — quickstart:**

```bash
cd correlcore/infra/docker
docker compose -f docker-compose.quickstart.yml pull
docker compose -f docker-compose.quickstart.yml up -d --remove-orphans
```

**Published-image user-test:**

```bash
docker compose -f docker-compose.user-test.yml pull
docker compose -f docker-compose.user-test.yml up -d --remove-orphans
```

### 5. What `up -d` does

1. **`migrate`** runs `alembic upgrade head` (exits 0). On 1.4.0 this applies
   revision **042** only.
2. **`api` / `web`** restart on `v1.5.0` images.
3. **`worker`** restarts as supercronic. Brief gap (seconds). The nightly job
   still ticks at 03:00 UTC; it does not fire twice because of the restart.
4. Orphans (`digest-worker`) are removed when `--remove-orphans` is set.

### 6. Verify

```bash
docker compose ps
# migrate: Exited (0)
# api, web, postgres, redis: Up (healthy where defined)
# worker: Up  (Path A always; Path B only with profile worker)

docker compose logs migrate --tail=30
# expect: "Running upgrade … -> 042" or already at head

curl -sf "https://${DOMAIN}/api/v1/health"
# {"status":"ok", ... "version":"1.5.0"}  (version follows APP_VERSION)

# Landing (logged out): two paths, check-in hero, no APK in the header
```

Optional worker freshness (after at least one successful job, or a manual run):

```bash
docker compose exec worker python -m app.workers.analytics --once

curl -sf -H "X-Worker-Status-Key: ${WORKER_STATUS_API_KEY}" \
  "https://${DOMAIN}/api/v1/worker/status"
```

Leave `WORKER_STATUS_API_KEY` empty to require an admin session instead.

### 7. Product checks (5 minutes)

- Log in; Home and Insights still load.
- Settings → Analyse: digest toggle is **off** by default; turning it on does
  **not** require a compose profile.
- If you are the first accounts on the instance and came from &lt; 1.4.0:
  those users were backfilled as **admin** (migration 040). Confirm `/admin`
  access is intended.

---

## Optional `.env` (not required to boot)

```bash
# Freshness probe for Uptime-Kuma / healthchecks.io
WORKER_STATUS_API_KEY=$(openssl rand -hex 24)
WORKER_STALE_AFTER_HOURS=30
```

On production `docker-compose.yml` these are wired from `.env`. On quickstart /
user-test, defaults are baked in (`WORKER_STATUS_API_KEY` empty → admin-only);
edit the compose file if you need the static key there.

---

## Troubleshooting

| Symptom                                                            | Cause                               | Fix                                                                                                        |
| ------------------------------------------------------------------ | ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Duplicate weekly digests                                           | Leftover `digest-worker`            | `docker compose rm -sf digest-worker` then `up -d --remove-orphans`; drop `digest` from `COMPOSE_PROFILES` |
| `worker` crash-loops: `supercronic: executable file not found`     | 1.5.0 compose + pre-1.5 image       | `IMAGE_TAG=v1.5.0` and `docker compose pull`                                                               |
| Worker image has supercronic but compose still runs the sleep loop | 1.5.0 image + old compose `command` | Update compose files from 1.5.0; recreate worker                                                           |
| `migrate` exits 1                                                  | DB URL / permissions                | Check `DATABASE_URL` / `POSTGRES_*`; `docker compose logs migrate`                                         |
| `/worker/status` 401                                               | No key and no admin cookie          | Set `WORKER_STATUS_API_KEY` or call while logged in as admin                                               |
| `/worker/status` `never_run` right after upgrade                   | Expected                            | Wait for 03:00 UTC or `exec worker python -m app.workers.analytics --once`                                 |
| Landing still shows old jargon / APK in header                     | Web container not on 1.5.0          | Confirm `IMAGE_TAG`, `docker compose pull web && up -d web`                                                |
| Insights empty on homelab                                          | Worker profile off                  | `COMPOSE_PROFILES=worker` (quickstart)                                                                     |

---

## Rollback

```bash
# .env
IMAGE_TAG=v1.4.0
APP_VERSION=1.4.0

docker compose pull
docker compose up -d
```

- **042** is additive (`last_seen_digest_at` nullable). Leaving it in place on
  a 1.4.0 API is safe; the old API ignores the column.
- Do **not** downgrade compose to restore `digest-worker` unless you also
  revert the analytics-worker digest job (otherwise two generators run).
- Worker command must match the image: 1.4.0 = sleep-loop Python; 1.5.0 =
  supercronic.

---

## After the GitHub `v1.5.0` tag (maintainers)

Images and the GitHub Release (changelog body, signed APK) are published by
CI when `v1.5.0` is pushed — not by merging this documentation alone.

```bash
git checkout main
git pull --ff-only origin main
git tag -a v1.5.0 -m "CorrelCore v1.5.0"
git push origin v1.5.0
```

Then confirm
[`release-images.yml`](../../.github/workflows/release-images.yml) tagged
`:v1.5.0` / `:v1.5` and operators can `docker compose pull`.
