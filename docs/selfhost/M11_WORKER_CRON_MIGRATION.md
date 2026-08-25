# M11 Worker Cron Migration Guide — Existing Selfhost Operators

Last updated: 2026-08-25

**1.4.0 → 1.5.0 operators:** follow
[`UPGRADE_1_5_0.md`](UPGRADE_1_5_0.md) (compose pin, digest-worker removal,
Alembic 042). This page is the cron-only detail for the worker `command`
change (`supercronic`).

Applies when the **Phase 3 worker robustness** changes ([#756](https://github.com/Sturmi77/correlcore/issues/756),
[#757](https://github.com/Sturmi77/correlcore/issues/757)) land. Read this
before `git pull` if you run the `worker` service on any of the three compose
stacks in [`infra/docker/`](../../infra/docker/).

**Related:** [`INSTALL.md`](INSTALL.md) · [`COMPOSE_STACKS.md`](COMPOSE_STACKS.md) ·
[`UPGRADE_1_5_0.md`](UPGRADE_1_5_0.md) ·
[ADR-0007 Healthchecks & Logging](../adr/0007-healthchecks-and-logging.md)

---

## Summary

| Who                        | Action required                                                                                                                                                                                                                                                                                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing production VPS    | `git pull` → `docker compose pull` → `docker compose up -d`                                                                                                                                                                                                                                                                                                      |
| Quickstart / homelab       | Same three commands, `-f docker-compose.quickstart.yml`                                                                                                                                                                                                                                                                                                          |
| Secrets / `.env`           | **No required new vars.** Optional monitoring vars for #756 apply out of the box on `docker-compose.yml`; on the quickstart/user-test stacks the safe defaults (`WORKER_STATUS_API_KEY` empty → admin-session-only, `WORKER_STALE_AFTER_HOURS=30`) are baked in and not overridable via `.env` — edit the compose file directly if you need to change them there |
| External uptime monitoring | Recommended: wire `GET /api/v1/worker/status` in (see below)                                                                                                                                                                                                                                                                                                     |

This migration is designed **non-breaking**: the worker still runs the exact
same Python job logic (`app/workers/analytics.py` is unchanged) on the same
daily schedule. Only _how_ that job is triggered inside the container changes.

---

## What changes in the repository

| Change type   | Detail                                                                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Added**     | `supercronic` binary baked into the `worker`-role image (`backend/Dockerfile`)                                                               |
| **Added**     | `backend/crontab/worker.crontab` — single daily entry, `0 3 * * * python -m app.workers.analytics --once`                                    |
| **Added**     | `GET /api/v1/worker/status` endpoint (#756) — freshness per job kind, see below                                                              |
| **Changed**   | `worker.command` — from `['python', '-m', 'app.workers.analytics']` to `['supercronic', '-passthrough-logs', '/app/crontab/worker.crontab']` |
| **Unchanged** | `worker.restart: unless-stopped`, job logic itself, nightly 03:00 UTC schedule, weekly Sunday digest piggyback                               |

### Why this change

Previously the `worker` container ran a single long-lived Python process
(`run_worker()`) that slept until 03:00 UTC, ran the daily jobs, and slept
again — forever. If that in-process loop crashed or hung _inside_ a job run,
the whole container could go down (or worse: hang without crashing, so
`restart: unless-stopped` never kicked in) and the next nightly run would
silently never happen. There was no way to distinguish "worker container is
up" from "worker container's nightly job is actually still succeeding."

With `supercronic`, the container now runs a small, always-up scheduler
process that spawns a fresh `python -m app.workers.analytics --once`
subprocess once a day. If that subprocess crashes, `supercronic` logs it and
simply waits for tomorrow's tick — the scheduler itself is never affected.
Combined with the new `GET /api/v1/worker/status` endpoint from #756 (which
reports the age of the _last successful_ run per job, independent of whether
the process is currently alive), an external monitor can now detect "the
worker hasn't actually completed a job in 30+ hours" — the failure mode #757
was written to close.

The `worker` service's compose block itself only changes in one line — its
`command:` — deliberately, to keep the upgrade diff minimal for selfhost
operators. No new container, no new required `.env` entry, no new
`healthcheck:` block was added on top of that.

---

## Your `.env` — what to change

### Required: nothing new for #757 itself

The cron migration introduces no new required environment variables. Existing
secrets (`SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_*`, `REDIS_PASSWORD`, etc.)
are untouched.

### Optional: worker freshness monitoring (#756)

```bash
# In infra/docker/.env
echo 'WORKER_STATUS_API_KEY='$(openssl rand -hex 24) >> .env
echo 'WORKER_STALE_AFTER_HOURS=30' >> .env
```

Leave `WORKER_STATUS_API_KEY` unset to require an admin session instead of a
static key — the endpoint is never fully unauthenticated either way. See
[`docs-site/docs/install/index.md`](../../docs-site/docs/install/index.md)
§ "Worker freshness monitoring" for the full curl example and Uptime-Kuma /
healthchecks.io wiring instructions.

---

## Upgrade procedure

```bash
cd correlcore/infra/docker

git pull
docker compose pull
docker compose up -d
```

(Quickstart / homelab path: add `-f docker-compose.quickstart.yml` to every
`docker compose` call, and remember `worker` only starts with
`COMPOSE_PROFILES=worker` or `--profile worker` as before — that part is
unchanged.)

### What happens on `up -d`

1. The `worker` image is rebuilt/pulled with the `supercronic` binary and
   `crontab/` baked in.
2. The `worker` container restarts with the new `command:`. There is a brief
   window (well under a minute) where the old long-running process stops and
   `supercronic` starts — this does not skip or duplicate the nightly job
   since jobs only ever run at the fixed `0 3 * * *` tick.
3. `api`, `web`, `postgres`, `redis`, etc. are unaffected.

### Verify

```bash
docker compose ps
# correlcore-worker should show "Up" (no dedicated healthcheck was added for
# this change — the freshness signal to watch is /worker/status, see below)

docker compose logs worker --tail=20
# Expect supercronic startup log lines; no cron output yet until the next
# 03:00 UTC tick (or trigger manually, see below)

# Primary freshness signal — requires the api container, not worker:
curl -sf -H "X-Worker-Status-Key: ${WORKER_STATUS_API_KEY}" \
  "https://${DOMAIN}/api/v1/worker/status"
```

To manually trigger a run without waiting for 03:00 UTC (useful right after
upgrading, to confirm the new invocation path works end-to-end):

```bash
docker compose exec worker python -m app.workers.analytics --once
```

---

## Monitoring: what changed

| Signal                     | Before (#745 baseline)                                   | After (#756 + #757)                                                                                  |
| -------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Container process liveness | None (no `healthcheck:` on worker)                       | None (unchanged — no `healthcheck:` block was added; not needed since freshness is tracked via #756) |
| Job success/freshness      | None — silent failure possible                           | `GET /api/v1/worker/status` (#756) — **only** signal, age of last success per job kind               |
| Crash recovery             | Whole container restart needed                           | `supercronic` survives a crashed `--once` subprocess; container stays up                             |
| Loud crash reporting       | GlitchTip (if `--profile monitoring` enabled), unchanged | Unchanged, still applies                                                                             |

**Action for existing external monitors:** if you already poll the worker
container's Docker status (`docker compose ps`) or logs for liveness, that
keeps working exactly as before — this migration does not change it. What's
new is `GET /api/v1/worker/status` on the `api` container/domain, which is
the only signal that actually reflects whether the nightly job is still
succeeding. See the install docs for exact Uptime-Kuma / healthchecks.io
setup.

---

## Troubleshooting

| Symptom                                                                          | Likely cause                                                  | Fix                                                                                                                                                                                |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `worker` container crash-loops after upgrade                                     | `supercronic` binary missing/checksum failed at build time    | `docker compose build worker --no-cache`, check build logs for the checksum step                                                                                                   |
| No nightly job output in logs                                                    | Waiting for next `0 3 * * *` UTC tick                         | Trigger manually: `docker compose exec worker python -m app.workers.analytics --once`                                                                                              |
| `/worker/status` returns 401                                                     | Neither `WORKER_STATUS_API_KEY` nor an admin session provided | On `docker-compose.yml`, set the env var in `.env`; on quickstart/user-test, call it from an authenticated admin browser session instead (or edit the compose file to add the var) |
| `/worker/status` shows `job_status: never_run` for every job right after upgrade | Expected — no successful run recorded yet on this DB          | Wait for the next tick or trigger manually; recheck                                                                                                                                |
| Weekly digest not appearing                                                      | Unrelated to this migration — check user's Settings opt-in    | See `docs/DEVELOPMENT.md` digest section                                                                                                                                           |

---

## Rollback

If you need to revert to the previous long-running worker process, check out
the pre-#757 `worker.command` in your compose file
(`['python', '-m', 'app.workers.analytics']`, no `--once`) and rebuild. No
database migration is involved in this change, so rollback is compose-only.
