# Weekly Digest — Completion Plan

Status: **WP1 done** (opt-in + compose profile + stored GET)  
Last updated: 2026-07-16  
Related: Issue #147, `backend/app/services/insight_digest.py`, `backend/app/workers/digest.py`, `/insights/digest`, Settings `digest_enabled`

---

## Decisions (locked)

| ID   | Decision                 | Choice                                                                  |
| ---- | ------------------------ | ----------------------------------------------------------------------- |
| D-D1 | Delivery channel v1      | **In-app only** (no push/email yet)                                     |
| D-D2 | Compose wiring           | Profile **`digest`** → `digest-worker` (`python -m app.workers.digest`) |
| D-D3 | Default `digest_enabled` | **`false`** (opt-in); migration 028                                     |
| D-D4 | Discoverability          | Settings toggle + preview link to `/insights/digest`                    |
| D-D5 | Legacy `true` rows       | **Backfill to `false`**; migration 031 (#449)                           |

### D-D5 — why the legacy rows are reset

Migration 026 added `digest_enabled` as `NOT NULL DEFAULT true`, and the ORM
model carried `default=True` until #398. Every preference row created before
that upgrade therefore holds `true` without anyone having opted in. Migration
028 changed only the column default and left those rows alone, so the worker's
`digest_enabled IS TRUE` gate did **not** mean "user opted in" for them.

Migration 031 resets every `true` row once, unconditionally. No `created_at`
cutoff: nothing records when 028 was applied to a given database, so any date
boundary mis-classifies late upgraders in both directions. The two failure
modes are not symmetric — resetting a genuine opt-in is visible and one click
to undo, while leaving an artifact sends mail nobody consented to. The worker
also only runs behind `COMPOSE_PROFILES=digest`, so no `true` has ever produced
a delivery.

`user_preferences` enforces `FORCE ROW LEVEL SECURITY`, so 031 asserts that it
runs as a superuser or `BYPASSRLS` role — a restricted role would reset nothing
and still report success.

**Operators:** mention in release notes that digest recipients re-enable the
toggle under Settings → Analysis.

---

## Current state

| Piece                          | Status                                   |
| ------------------------------ | ---------------------------------------- |
| Preference default             | **false** (opt-in)                       |
| Settings toggle + preview link | Shipped                                  |
| `GET /insights/digest/latest`  | Shipped (prefers stored row)             |
| FE preview `/insights/digest`  | Shipped (auth redirect fixed)            |
| Compose `digest-worker`        | Profile `digest` on all stacks           |
| Persist vs recompute on GET    | Stored preferred; fall back to recompute |
| Push / email                   | Not shipped                              |

Enable:

```bash
COMPOSE_PROFILES=worker,digest docker compose -f docker-compose.quickstart.yml up -d
# or one-shot:
cd backend && uv run --python 3.12 python -m app.workers.digest --once
```

See [`docs/selfhost/COMPOSE_STACKS.md`](../selfhost/COMPOSE_STACKS.md).

---

## WP1 — Persistence contract (done)

1. `GET /insights/digest/latest` prefers the newest `insight_digests` row and hydrates insight payloads by ID.
2. Falls back to recompute when no row exists or hydration fails (deleted insights).
3. Worker always **computes** then **stores** (`compute_weekly_digest_for_user`) — never short-circuits via GET.
4. Tests: prefer-stored, missing-store fallback, disabled → error, hydrate order, store→hydrate roundtrip.

---

## Remaining work packages

### WP2 — Ops polish

1. INSTALL.md / docs-site mention of `digest` profile (if not already).
2. Worker run visibility in `/dev` when enabled.

### WP3 — Explicitly out of scope

- UnifiedPush / FCM
- SMTP digest mails
- LLM digest prose

---

## Acceptance for “done”

- [x] Opt-in default + compose profile
- [x] Stored digest preferred on GET
- [ ] INSTALL / docs-site document the profile
- [ ] No UI claims push delivery
