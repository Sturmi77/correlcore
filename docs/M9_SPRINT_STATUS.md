# M9 Sprint Status — Beta Hardening

Last updated: 2026-07-11

Tracking document for [`docs/M9_SPRINT_PLAN.md`](M9_SPRINT_PLAN.md).

**Milestone completeness:** Sprint 3 backup & install complete on `cursor/m9-sprint-3-backup-install-2529`.
Sprints 4–6 pending.

**Prerequisite:** M5.1 UX polish complete (2026-07-10) —
[`docs/M5_1_SPRINT_STATUS.md`](M5_1_SPRINT_STATUS.md).

## Overview

| Sprint | Title                     | Status  |
| ------ | ------------------------- | ------- |
| 0      | Scope & audit             | Done    |
| 1      | GDPR self-service         | Done    |
| 2      | Observability             | Done    |
| 3      | Backup & install          | Done    |
| 4      | Security & CI             | Pending |
| 5      | Beta program              | Pending |
| 6      | Milestone closeout (M9-C) | Pending |

## Acceptance-criteria audit matrix

Audit date: 2026-07-11. Method: codebase grep, sprint status docs on `main`,
acceptance criteria from [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) § M9.

| Criterion | Sprint | Code anchor | Test / doc evidence | Gap |
| --------- | ------ | ----------- | ------------------- | --- |
| `docs/PRIVACY.md` + in-app link | 1 | [`docs/PRIVACY.md`](PRIVACY.md), [`privacy/+page.svelte`](../apps/web/src/routes/privacy/+page.svelte) | E2E [`gdpr-self-service.spec.ts`](../apps/web/tests/e2e/gdpr-self-service.spec.ts) | — |
| Account deletion self-service (Art. 17) | 1 | `DELETE /api/v1/user/me`; Settings dialog | [`test_user_endpoints.py`](../backend/tests/test_user_endpoints.py), E2E gdpr spec | — |
| Backup documented + restore test | 3 | [`selfhost/INSTALL.md`](selfhost/INSTALL.md) §Backup | [`quality/M9_BACKUP_RESTORE_TEST.md`](quality/M9_BACKUP_RESTORE_TEST.md) (PASS 2026-07-11) | Operator must run production restore log row |
| GlitchTip active, no PII in reports | 2 | [`error_tracking.py`](../backend/app/core/error_tracking.py), [`scrubEvent.ts`](../apps/web/src/lib/observability/scrubEvent.ts) | [`test_error_tracking.py`](../backend/tests/test_error_tracking.py), [`scrubEvent.test.ts`](../apps/web/src/lib/observability/scrubEvent.test.ts) | DSN optional — no traffic when unset |
| Install-Guide (Compose, Traefik, DNS) | 3 | [`selfhost/INSTALL.md`](selfhost/INSTALL.md), [`infra/docker/traefik/traefik.yml`](../infra/docker/traefik/traefik.yml) | Path A (VPS) + Path B (homelab) documented | Production operator restore log still manual |
| Quality gate §9 | 6 | CI workflows green on `main` | Per-milestone gates (M7 pattern) | `M9_QUALITY_GATE.md` not yet created |
| ZIP export self-service (Art. 20) | 1 | `GET /api/v1/user/export` | [`test_export_service.py`](../backend/tests/test_export_service.py), [`test_user_endpoints.py`](../backend/tests/test_user_endpoints.py), E2E gdpr spec | — |
| GlitchTip selfhosted (DSGVO) | 2 | Compose profile + healthcheck | [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml), [`infra/docker/.env.example`](../infra/docker/.env.example) | Operator sets `GLITCHTIP_DSN` after bootstrap |
| Incident-response runbook | 2 | — | [`docs/runbooks/incident-response.md`](runbooks/incident-response.md) | — |
| Art. 18 restriction self-service | 1 | — | [`DSGVO.md`](DSGVO.md) support workflow | Documented; no API (by design) |
| `analytics_enabled` opt-out (DSGVO M3) | 1 | Settings toggle + `PATCH /user/preferences` | [`test_user_preferences.py`](../backend/tests/test_user_preferences.py), E2E gdpr spec | DSGVO.md M3 checkbox closed |
| DSFA for cloud deployment | — | — | Deferred to M12 in [`DSGVO.md`](DSGVO.md) | M9: selfhost-only scope note only |
| AV-Vertrag template (Hetzner) | 4 | — | — | Static template pending |
| External pentest | 4 | — | [`M4_RELEASE_READINESS.md`](quality/M4_RELEASE_READINESS.md) P1 | Not yet commissioned |
| `pip-audit` / `pnpm audit` CI gate | 4 | — | — | Not in [`.github/workflows/`](../.github/workflows/) |
| Style-contract lint | 4 | — | [`UI_COMPONENT_SYSTEM.md`](frontend/UI_COMPONENT_SYSTEM.md) §9 | Lint rule not implemented |
| LUKS + restic in Install-Guide | 3 | [`selfhost/INSTALL.md`](selfhost/INSTALL.md) §LUKS, §restic | ADR-0005 aligned | — |
| 5–10 beta testers + feedback | 5 | — | — | Program not started |
| Symptom analytics beta review | 5 | — | [`features/symptom-analytics.md`](features/symptom-analytics.md) §M9 | Review pending |
| Notes-in-analysis threshold review | 5 | Worker thresholds in config | [`features/notes-in-analysis.md`](features/notes-in-analysis.md) | Config review only; per-entry opt-out → M10 |

## GitHub issue mapping

| Issue | Title (expected)              | Sprint scope        | Status  |
| ----- | ----------------------------- | ------------------- | ------- |
| #29   | Beta hardening / monitoring   | 0–2, 6 (umbrella) | Open — sliced per sprint in this matrix |

Per [`CLOSEOUT_SPRINT_PLAN.md`](CLOSEOUT_SPRINT_PLAN.md) §2: M9 = GlitchTip, external
testers, monitoring, GDPR self-service. Close #29 in Sprint 6 when all slices exit.

## Sprint 0 — Completed checklist

- [x] [`M9_SPRINT_PLAN.md`](M9_SPRINT_PLAN.md) created (overview, API-minimization rules, sprints 0–6).
- [x] [`M9_SPRINT_STATUS.md`](M9_SPRINT_STATUS.md) created with acceptance audit matrix.
- [x] Gap list maps each DESIGN_DOCUMENT M9 criterion → code → tests → target sprint.
- [x] Out-of-scope items recorded (#147, #148, M8, M9+, M10, M12).
- [x] Baseline verification commands documented in sprint plan (M9-C quality gate).
- [x] Cross-links: `README.md`, `DESIGN_DOCUMENT.md`, `MOBILE_WEB_IMPLEMENTATION_PLAN.md`.

## API usage minimization — audit summary

| Area | Current state | M9 constraint |
| ---- | ------------- | ------------- |
| Cloud / local LLM | Not integrated; #147/#148 → M7-S8 | No new LLM calls |
| Error tracking | Optional `GLITCHTIP_DSN`; PII scrub in API + Web | Selfhosted + optional DSN |
| Analytics compute | Nightly worker + `analytics_enabled` gate | No on-demand external APIs |
| Beta feedback | — | No Hotjar/Mixpanel; GitHub/email only |
| GDPR APIs | Delete, export, preferences exist | Verify + document; no new endpoints |
| Health Connect | M8 scope | Out of M9 |

## Sprint 1 — Completed checklist

- [x] `docs/PRIVACY.md` created; in-app `/privacy` route + Settings link.
- [x] Playwright `gdpr-self-service.spec.ts` (privacy link, ZIP export, analytics opt-out, account delete).
- [x] Backend HTTP test `GET /api/v1/user/export` in `test_user_endpoints.py`.
- [x] Backend HTTP test `PATCH /api/v1/user/preferences` analytics opt-out.
- [x] Art. 18 support workflow documented in `DSGVO.md`.
- [x] DSGVO M3 `analytics_enabled` checkpoint closed.

## Sprint 2 — Completed checklist

- [x] `sentry-sdk` integration in API with optional `GLITCHTIP_DSN` and `before_send` PII scrub.
- [x] Web client/server error tracking (`hooks.client.ts`, `hooks.server.ts`) with shared scrub.
- [x] GlitchTip Compose healthcheck (profile `monitoring`).
- [x] `docs/runbooks/incident-response.md` created; linked from `DSGVO.md`.
- [x] `GLITCHTIP_DSN` documented in `infra/docker/.env.example`; wired to `api` + `web` services.

## Sprint 3 — Completed checklist

- [x] `docs/selfhost/INSTALL.md` — consolidated VPS (Traefik, DNS, secrets) + homelab pointer.
- [x] `infra/docker/traefik/traefik.yml` — static Traefik config for production compose.
- [x] Backup section: `pg_dump` + restic + LUKS notes (ADR-0005).
- [x] `docs/quality/M9_BACKUP_RESTORE_TEST.md` — protocol + PASS result (2026-07-11).
- [x] `docs/selfhost/BETA_CHECKLIST.md` + link to `USER_WORKFLOWS.md`.
- [x] README Quickstart points to install guide.

## Next sprint (4 — Security & CI)

Priority gaps from audit:

1. CI job: `pip-audit` + `pnpm audit --audit-level=high`.
2. Style-contract lint for design tokens.
3. External pentest → `docs/quality/M9_PENTEST.md`.
4. AV-Vertrag template (Hetzner).

## API usage note (unchanged)

No new external APIs in Sprint 3 — documentation and local restore test only.
