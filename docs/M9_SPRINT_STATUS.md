# M9 Sprint Status — Beta Hardening

Last updated: 2026-07-11

Tracking document for [`docs/M9_SPRINT_PLAN.md`](M9_SPRINT_PLAN.md).

**Milestone completeness:** M9 complete on `cursor/m9-sprint-6-closeout-2529` (Sprint 6 M9-C).

**Prerequisite:** M5.1 UX polish complete (2026-07-10) —
[`docs/M5_1_SPRINT_STATUS.md`](M5_1_SPRINT_STATUS.md).

## Overview

| Sprint | Title                     | Status |
| ------ | ------------------------- | ------ |
| 0      | Scope & audit             | Done   |
| 1      | GDPR self-service         | Done   |
| 2      | Observability             | Done   |
| 3      | Backup & install          | Done   |
| 4      | Security & CI             | Done   |
| 5      | Beta program              | Done   |
| 6      | Milestone closeout (M9-C) | Done   |

## Acceptance-criteria audit matrix

Audit date: 2026-07-11 (closeout refresh). Method: codebase grep, quality gate run,
acceptance criteria from [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) § M9.

| Criterion                               | Sprint | Code anchor                                                                                                                      | Test / doc evidence                                                                                                                               | Gap                                               |
| --------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `docs/PRIVACY.md` + in-app link         | 1      | [`docs/PRIVACY.md`](PRIVACY.md), [`privacy/+page.svelte`](../apps/web/src/routes/privacy/+page.svelte)                           | E2E [`gdpr-self-service.spec.ts`](../apps/web/tests/e2e/gdpr-self-service.spec.ts)                                                                | —                                                 |
| Account deletion self-service (Art. 17) | 1      | `DELETE /api/v1/user/me`; Settings dialog                                                                                        | [`test_user_endpoints.py`](../backend/tests/test_user_endpoints.py), E2E gdpr spec                                                                | —                                                 |
| Backup documented + restore test        | 3      | [`selfhost/INSTALL.md`](selfhost/INSTALL.md) §Backup                                                                             | [`quality/M9_BACKUP_RESTORE_TEST.md`](quality/M9_BACKUP_RESTORE_TEST.md) (PASS 2026-07-11)                                                        | Operator must run production restore log row      |
| GlitchTip active, no PII in reports     | 2      | [`error_tracking.py`](../backend/app/core/error_tracking.py), [`scrubEvent.ts`](../apps/web/src/lib/observability/scrubEvent.ts) | [`test_error_tracking.py`](../backend/tests/test_error_tracking.py), [`scrubEvent.test.ts`](../apps/web/src/lib/observability/scrubEvent.test.ts) | DSN optional — operator bootstrap for live events |
| Install-Guide (Compose, Traefik, DNS)   | 3      | [`selfhost/INSTALL.md`](selfhost/INSTALL.md), [`infra/docker/traefik/traefik.yml`](../infra/docker/traefik/traefik.yml)          | Path A (VPS) + Path B (homelab) documented                                                                                                        | Production operator restore log still manual      |
| Quality gate §9                         | 6      | CI workflows + local gate                                                                                                        | [`quality/M9_QUALITY_GATE.md`](quality/M9_QUALITY_GATE.md) (PASS 2026-07-11)                                                                      | —                                                 |
| ZIP export self-service (Art. 20)       | 1      | `GET /api/v1/user/export`                                                                                                        | [`test_export_service.py`](../backend/tests/test_export_service.py), E2E gdpr spec                                                                | —                                                 |
| GlitchTip selfhosted (DSGVO)            | 2      | Compose profile + healthcheck                                                                                                    | [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml)                                                                           | Operator sets `GLITCHTIP_DSN` after bootstrap     |
| Incident-response runbook               | 2      | —                                                                                                                                | [`docs/runbooks/incident-response.md`](runbooks/incident-response.md)                                                                             | —                                                 |
| Art. 18 restriction self-service        | 1      | —                                                                                                                                | [`DSGVO.md`](DSGVO.md) support workflow                                                                                                           | Documented; no API (by design)                    |
| `analytics_enabled` opt-out (DSGVO M3)  | 1      | Settings toggle + `PATCH /user/preferences`                                                                                      | [`test_user_preferences.py`](../backend/tests/test_user_preferences.py), E2E gdpr spec                                                            | —                                                 |
| DSFA for cloud deployment               | —      | —                                                                                                                                | Deferred to M12 in [`DSGVO.md`](DSGVO.md)                                                                                                         | M9: selfhost-only scope note only                 |
| AV-Vertrag template (Hetzner)           | 4      | [`legal/AV_VERTRAG_HETZNER_TEMPLATE.md`](legal/AV_VERTRAG_HETZNER_TEMPLATE.md)                                                   | Operator signs Hetzner AV at M12                                                                                                                  | Template + checklist done                         |
| External pentest                        | 4      | —                                                                                                                                | [`quality/M9_PENTEST.md`](quality/M9_PENTEST.md)                                                                                                  | Internal PASS; external vendor pending            |
| `pip-audit` / `pnpm audit` CI gate      | 4      | [`.github/workflows/ci-security.yml`](../.github/workflows/ci-security.yml)                                                      | `dependency-audit` job                                                                                                                            | ecdsa ignore documented                           |
| Style-contract lint                     | 4      | [`scripts/check-style-contract.mjs`](../scripts/check-style-contract.mjs)                                                        | CI `style-contract` job in `ci-web.yml`                                                                                                           | —                                                 |
| LUKS + restic in Install-Guide          | 3      | [`selfhost/INSTALL.md`](selfhost/INSTALL.md) §LUKS, §restic                                                                      | ADR-0005 aligned                                                                                                                                  | —                                                 |
| 5–10 beta testers + feedback            | 5      | [`selfhost/BETA_ONBOARDING.md`](selfhost/BETA_ONBOARDING.md), [`BETA_FEEDBACK_TRIAGE.md`](selfhost/BETA_FEEDBACK_TRIAGE.md)      | [`.github/ISSUE_TEMPLATE/beta_feedback.md`](../.github/ISSUE_TEMPLATE/beta_feedback.md)                                                           | Operator runs cohort; roster not in repo          |
| Symptom analytics beta review           | 5      | —                                                                                                                                | [`quality/M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md`](quality/M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md)                                                      | External round 1 pending                          |
| Notes-in-analysis threshold review      | 5      | Worker thresholds in config                                                                                                      | [`quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md`](quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md)                                                          | Per-entry opt-out → M10                           |

## GitHub issue mapping

| Issue | Title (expected)            | Sprint scope      | Status                                                               |
| ----- | --------------------------- | ----------------- | -------------------------------------------------------------------- |
| #29   | Beta hardening / monitoring | 0–2, 6 (umbrella) | **Ready to close** — operator action (integration cannot closeIssue) |

Per [`CLOSEOUT_SPRINT_PLAN.md`](CLOSEOUT_SPRINT_PLAN.md) §2: M9 = GlitchTip, external
testers, monitoring, GDPR self-service. #29 closed when all sprint slices exited.

## Sprint 0 — Completed checklist

- [x] [`M9_SPRINT_PLAN.md`](M9_SPRINT_PLAN.md) created (overview, API-minimization rules, sprints 0–6).
- [x] [`M9_SPRINT_STATUS.md`](M9_SPRINT_STATUS.md) created with acceptance audit matrix.
- [x] Gap list maps each DESIGN_DOCUMENT M9 criterion → code → tests → target sprint.
- [x] Out-of-scope items recorded (#147, #148, M8, M9+, M10, M12).
- [x] Baseline verification commands documented in sprint plan (M9-C quality gate).
- [x] Cross-links: `README.md`, `DESIGN_DOCUMENT.md`, `MOBILE_WEB_IMPLEMENTATION_PLAN.md`.

## API usage minimization — audit summary

| Area              | Current state                                    | M9 constraint                         |
| ----------------- | ------------------------------------------------ | ------------------------------------- |
| Cloud / local LLM | Not integrated; #147/#148 → M7-S8                | No new LLM calls                      |
| Error tracking    | Optional `GLITCHTIP_DSN`; PII scrub in API + Web | Selfhosted + optional DSN             |
| Analytics compute | Nightly worker + `analytics_enabled` gate        | No on-demand external APIs            |
| Beta feedback     | —                                                | No Hotjar/Mixpanel; GitHub/email only |
| GDPR APIs         | Delete, export, preferences exist                | Verify + document; no new endpoints   |
| Health Connect    | M8 scope                                         | Out of M9                             |

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

## Sprint 4 — Completed checklist

- [x] CI `dependency-audit` job: `pip-audit` + `pnpm audit --prod --audit-level=high`.
- [x] Backend dependency bumps (starlette, cryptography, multipart, aiosmtplib, idna).
- [x] `scripts/check-style-contract.mjs` + CI `style-contract` job.
- [x] `docs/quality/M9_PENTEST.md` — internal assessment PASS; external scope documented.
- [x] `docs/legal/AV_VERTRAG_HETZNER_TEMPLATE.md` — Hetzner AVV operator checklist.

## Sprint 5 — Completed checklist

- [x] `docs/selfhost/BETA_ONBOARDING.md` — instance URL, test accounts, email template, roster.
- [x] `docs/selfhost/BETA_FEEDBACK_TRIAGE.md` — P0/P1/P2 triage workflow.
- [x] `.github/ISSUE_TEMPLATE/beta_feedback.md` — structured feedback template.
- [x] `docs/quality/M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md` — internal review + intensity decision.
- [x] `docs/quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md` — worker threshold review (defaults kept).
- [x] Cross-links: `BETA_CHECKLIST.md`, `symptom-analytics.md`, `notes-in-analysis.md`.

## Sprint 6 — Completed checklist (M9-C)

- [x] `beforeSend` type fix in web error tracking (`errorTracking.client.ts`, `errorTracking.server.ts`).
- [x] Ruff F841 fix in `test_user_preferences.py`.
- [x] Full M9 quality gate executed — see [`quality/M9_QUALITY_GATE.md`](quality/M9_QUALITY_GATE.md).
- [x] [`quality/M9_VISUAL_QA.md`](quality/M9_VISUAL_QA.md) — Settings privacy + install doc flows.
- [x] `CHANGELOG.md`, `README.md`, `DESIGN_DOCUMENT.md` M9 exit checkboxes updated.
- [x] GitHub #29 ready for operator close (all M9 slices exited; see issue mapping).

## Next milestone

**M10 — Public Selfhost Release v1.0.** See [`M10_SPRINT_PLAN.md`](M10_SPRINT_PLAN.md),
[`M10_SPRINT_STATUS.md`](M10_SPRINT_STATUS.md), and [`selfhost/M10_COMPOSE_UPGRADE.md`](selfhost/M10_COMPOSE_UPGRADE.md).

## API usage note (unchanged)

No new external APIs across M9 Sprints 0–6 — documentation, optional GlitchTip DSN,
and verification only.
