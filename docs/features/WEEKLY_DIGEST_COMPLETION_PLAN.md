# Weekly Digest — Completion Plan

Status: **In progress** (opt-in + compose profile landed 2026-07-16)  
Last updated: 2026-07-16  
Related: Issue #147, `backend/app/workers/digest.py`, `/insights/digest`, Settings `digest_enabled`

---

## Decisions (locked)

| ID | Decision | Choice |
| -- | -------- | ------ |
| D-D1 | Delivery channel v1 | **In-app only** (no push/email yet) |
| D-D2 | Compose wiring | Profile **`digest`** → `digest-worker` (`python -m app.workers.digest`) |
| D-D3 | Default `digest_enabled` | **`false`** (opt-in); migration 028 |
| D-D4 | Discoverability | Settings toggle + preview link to `/insights/digest` |

---

## Current state

| Piece | Status |
| ----- | ------ |
| Preference default | **false** (opt-in) |
| Settings toggle + preview link | Shipped |
| `GET /insights/digest/latest` | Shipped |
| FE preview `/insights/digest` | Shipped (auth redirect fixed) |
| Compose `digest-worker` | Profile `digest` on all stacks |
| Persist vs recompute on GET | Still recomputes; store writes on worker run |
| Push / email | Not shipped |

Enable:

```bash
COMPOSE_PROFILES=worker,digest docker compose -f docker-compose.quickstart.yml up -d
# or one-shot:
cd backend && uv run --python 3.12 python -m app.workers.digest --once
```

See [`docs/selfhost/COMPOSE_STACKS.md`](../selfhost/COMPOSE_STACKS.md).

---

## Remaining work packages

### WP1 — Persistence contract

1. Prefer stored `insight_digests` row on GET; fall back to recompute.
2. Tests for store → get, missing store, `digest_enabled=false` → 403.

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
- [ ] Stored digest preferred on GET  
- [ ] INSTALL / docs-site document the profile  
- [ ] No UI claims push delivery  
