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

---

## Current state

| Piece                          | Status                                       |
| ------------------------------ | -------------------------------------------- |
| Preference default             | **false** (opt-in)                           |
| Settings toggle + preview link | Shipped                                      |
| `GET /insights/digest/latest`  | Shipped (prefers stored row)                 |
| FE preview `/insights/digest`  | Shipped (auth redirect fixed)                |
| Compose `digest-worker`        | Profile `digest` on all stacks               |
| Persist vs recompute on GET    | Stored preferred; fall back to recompute     |
| Push / email                   | Not shipped                                  |

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
