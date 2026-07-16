# Weekly Digest — Completion Plan

Status: **Planned** (foundation exists; scheduled delivery not shipped)  
Last updated: 2026-07-16  
Related: Issue #147, `backend/app/workers/digest.py`, `/insights/digest`, Settings `digest_enabled`

---

## Current state (honest inventory)

| Piece | Status |
| ----- | ------ |
| Preference `digest_enabled` | Shipped (default on) |
| Settings toggle + preview link | Shipped (copy marks schedule as upcoming) |
| `GET /api/v1/insights/digest/latest` | Shipped (recomputes from insights) |
| FE preview route `/insights/digest` | Shipped (no main-nav entry) |
| Worker `python -m app.workers.digest --once` | Code exists; **not** in any compose service |
| Cron / in-process scheduler | Documented only; not wired |
| Persist + read stored digest rows | `store_weekly_digest` writes; GET path does not prefer stored rows |
| Push / email delivery | Fields exist; **no sender** |

---

## Goal

Ship a trustworthy Sunday weekly digest: eligible users get a stable summary of their top insights, viewable in-app (and optionally notified later), without promising push until a channel exists.

---

## Decisions required before implementation

| ID | Decision | Options | Recommendation |
| -- | -------- | ------- | -------------- |
| D-D1 | Delivery channel for v1 | In-app only vs email vs UnifiedPush | **In-app only** first; keep push fields dormant |
| D-D2 | Compose wiring | Always-on digest service vs cron sidecar vs analytics-worker flag | **Profile `digest`** or weekly cron on analytics worker |
| D-D3 | Default `digest_enabled` | Keep `true` vs default `false` until delivery ships | Flip to **`false`** until schedule is live, or keep true with honest copy (current) |
| D-D4 | Nav discoverability | Settings link only vs Insights sub-nav | Settings + Insights header link once schedule ships |

---

## Work packages

### WP1 — Persistence contract

1. Make `GET /insights/digest/latest` prefer the latest **stored** `insight_digests` row when present; fall back to recompute only for empty history.
2. Align response schema with stored payload (week_start/end, insight ids, statements).
3. Tests: store → get returns stored; missing store → recompute; `digest_enabled=false` → 403.

### WP2 — Scheduler

1. Add compose path: either `command: python -m app.workers.digest` with sleep-until-Sunday, or cron entry in docs + optional `COMPOSE_PROFILES=digest`.
2. Document operator runbook: `uv run python -m app.workers.digest --once`.
3. Worker run history via existing `worker_runs` (kind already present or extend).

### WP3 — Product surface

1. Insights page link “Weekly digest” when `digest_enabled`.
2. Empty states: no insights yet / digest disabled / next run hint.
3. i18n: remove “upcoming” wording once schedule is live.
4. Optional: email via existing SMTP when `SMTP_*` configured (separate flag).

### WP4 — Explicitly out of scope for this plan

- UnifiedPush / FCM (M11+ notifications track)
- LLM-written digest prose (`INSIGHTS_LLM_ENABLED`)
- Per-insight CSV export from digest cards

---

## Acceptance criteria

- [ ] Sunday slot (or documented cron) generates digests for eligible users without manual SSH
- [ ] In-app preview shows the **stored** digest for the past week
- [ ] Toggle off stops generation and returns clear 403/empty UX
- [ ] Compose / INSTALL docs describe how to enable the digest job
- [ ] No UI copy claims push delivery until a sender exists
- [ ] Unit + one integration/smoke test green

---

## Suggested sequence

1. Decide D-D1–D-D3  
2. WP1 persistence  
3. WP2 scheduler  
4. WP3 surface + copy cleanup  
5. QA + docs-site API row for digest
