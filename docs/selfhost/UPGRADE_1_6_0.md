# Upgrade to 1.6.0 — existing selfhost / hosted operators

Last updated: 2026-09-01

Step-by-step compose update from **v1.5.0** (or any earlier 1.x pin) to
**v1.6.0**. Read this before `docker compose pull` — **two changes can stop a
running deployment**.

**Related:** [`INSTALL.md`](INSTALL.md) · [`COMPOSE_STACKS.md`](COMPOSE_STACKS.md) ·
docs-site [Upgrade](https://sturmi77.github.io/correlcore/install/upgrade/)

---

## Summary

| Who                  | Action                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Production / homelab | Check the two blockers below, pin `IMAGE_TAG=v1.6.0`, pull, `up -d --remove-orphans`     |
| `.env`               | **No required new vars.** Remove a pinned `APP_VERSION` (see below)                      |
| Database             | `migrate` applies Alembic **043** (expanded default tag / symptom catalogue, idempotent) |
| Custom API clients   | State-changing requests must send `Content-Type: application/json` or they get **415**   |

This is a security and assurance release: CSRF Content-Type gate, report-only
CSP, a bounded access-token TTL, and CodeQL / Trivy / ZAP scanning in CI.

---

## Before you start — two blockers

### 1. Access-token TTL is capped at 15 minutes (staging / production)

If your `.env` sets `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` **above 15**, the API
**will refuse to start** after the upgrade (config validation error, not a
silent clamp).

```bash
# check
grep JWT_ACCESS_TOKEN_EXPIRE_MINUTES infra/docker/.env
```

Fix: set it to `15` or lower (or remove the line — the default is 15).

Why: ADR-0006 accepts "no logout denylist" as a residual risk _only_ while
access tokens are short-lived. An operator raising the TTL silently invalidated
that assumption, so the bound is now enforced (#791).

### 2. Non-JSON state-changing requests now return 415

The Content-Type CSRF gate rejects `POST` / `PUT` / `PATCH` / `DELETE` requests
that carry a body without `Content-Type: application/json` (#779, #789).

The web and Android clients already comply. Only **your own** scripts,
integrations or `curl` calls are affected:

```bash
# fails with 415
curl -X POST https://$DOMAIN/api/v1/... -d 'a=b'
# correct
curl -X POST https://$DOMAIN/api/v1/... -H 'Content-Type: application/json' -d '{"a":"b"}'
```

**Route exceptions — do not "fix" these to JSON.** Two routes keep their own
media types (`backend/app/core/csrf.py`):

| Route                              | Allowed content types                                |
| ---------------------------------- | ---------------------------------------------------- |
| `POST /api/v1/media/photos`        | `multipart/form-data` (file upload)                  |
| `POST /api/v1/security/csp-report` | `application/csp-report`, `application/reports+json` |

Photo upload requires multipart — sending JSON there would break it.

---

## Also worth knowing

### `APP_VERSION` should no longer be pinned in `.env`

The app now derives its version from the installed package, so OpenAPI,
`/health`, `/instance` and the Sentry release all report the running image's
real version. A value in `.env` is loaded via `env_file` and **overrides** that
default — it will report a stale version forever.

```bash
# remove (or comment out) this line if present
grep APP_VERSION infra/docker/.env
```

`.env.example` no longer ships a concrete pin (only a
`<your-custom-build-version>` placeholder). Set it only for a deliberate custom
build, and never to an older version than the image you run.

### Generated secondary compose stacks

`infra/dockge/compose.yaml` and `infra/dockhand/compose.yaml` are now
**generated** from the quickstart stack by `scripts/gen_compose_stacks.py`
(#781). Do not edit them directly — local edits are overwritten on the next
regeneration and CI fails on drift. Change the canonical stack or the generator.

### New setting: `RATE_LIMIT_ENABLED`

Defaults to `true` and **must stay `true`** in any real deployment. It exists so
the isolated DAST harness in CI can exercise handler logic without SlowAPI's
per-endpoint caps.

---

## Step-by-step

### 1. Update compose files (git operators)

```bash
cd correlcore
git fetch --tags
git checkout v1.6.0
```

### 2. Check the blockers and pin the release

```bash
cd infra/docker
grep -E 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES|APP_VERSION' .env   # act per the sections above
```

```env
# infra/docker/.env — do not overwrite the whole file from .env.example
IMAGE_TAG=v1.6.0
```

### 3. Pull and recreate

```bash
docker compose pull
docker compose up -d --remove-orphans
```

Quickstart: add `-f docker-compose.quickstart.yml` to both commands.

### 4. Verify

```bash
docker compose ps
# migrate: Exited (0)
# api, web, postgres, redis: Up (healthy where defined)

docker compose logs migrate --tail=30
# expect: "Running upgrade 042 -> 043" or already at head

curl -sf "https://${DOMAIN}/api/v1/health"
# {"status":"ok", ... "version":"1.6.0"}
```

If the API does **not** come up, check its logs first — a rejected
`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` fails fast with an explicit message:

```bash
docker compose logs api --tail=40
```

### 5. Product checks (2 minutes)

- Log in, create an entry, save — a working write proves the CSRF gate accepts
  the app's own requests.
- Settings → Tags: the expanded default catalogue (walk, cycle, stretching,
  screen-time …) and the new default symptoms (migraine, nausea, dizziness)
  are present for new accounts; existing custom tags are untouched.

---

## Troubleshooting

| Symptom                                   | Cause / fix                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| API container restarts, config error      | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` > 15 — lower it to 15                     |
| Own integration suddenly gets `415`       | Send `Content-Type: application/json` on state-changing requests            |
| `/health` reports an old version          | `APP_VERSION` still pinned in `.env` — remove the line                      |
| Edits to `dockge`/`dockhand` compose lost | Those files are generated — change the source stack or the generator (#781) |
| CSP violations in the browser console     | The CSP ships **report-only**; nothing is blocked. Reports go to            |
|                                           | `POST /api/v1/security/csp-report`                                          |

---

## Rollback

```bash
# infra/docker/.env
IMAGE_TAG=v1.5.0
```

```bash
docker compose pull && docker compose up -d
```

Alembic **043** is additive and idempotent; a 1.5.0 image runs against it
unchanged, so a plain image rollback needs **no** downgrade.

If you nevertheless want to reverse the migration, run it **before** you change
the pin — the v1.5.0 `migrate` image predates revision `043` and cannot resolve
it:

```bash
# still pinned to v1.6.0 (or override explicitly)
IMAGE_TAG=v1.6.0 docker compose run --rm migrate alembic downgrade 042
# only then switch the pin back to v1.5.0
```
