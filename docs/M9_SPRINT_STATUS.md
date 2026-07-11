# M9 Sprint Status — Beta Hardening

Last updated: 2026-07-11

Tracking document for [`docs/M9_SPRINT_PLAN.md`](M9_SPRINT_PLAN.md).

**Milestone completeness:** Sprint 0 audit complete on `cursor/m9-sprint-0-audit-2529`.
Sprints 1–6 pending.

**Prerequisite:** M5.1 UX polish complete (2026-07-10) —
[`docs/M5_1_SPRINT_STATUS.md`](M5_1_SPRINT_STATUS.md).

## Overview

| Sprint | Title                     | Status  |
| ------ | ------------------------- | ------- |
| 0      | Scope & audit             | Done    |
| 1      | GDPR self-service         | Pending |
| 2      | Observability             | Pending |
| 3      | Backup & install          | Pending |
| 4      | Security & CI             | Pending |
| 5      | Beta program              | Pending |
| 6      | Milestone closeout (M9-C) | Pending |

## Acceptance-criteria audit matrix

Audit date: 2026-07-11. Method: codebase grep, sprint status docs on `main`,
acceptance criteria from [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) § M9.

| Criterion                               | Sprint | Code anchor                                                                                                                                                                  | Test / doc evidence                                                                                                                                                                                                     | Gap                                                                               |
| --------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `docs/PRIVACY.md` + in-app link         | 1      | —                                                                                                                                                                            | —                                                                                                                                                                                                                       | File missing; Settings has delete UI only, no policy link                         |
| Account deletion self-service (Art. 17) | 1      | `DELETE /api/v1/user/me` in [`user.py`](../backend/app/api/v1/endpoints/user.py); Settings dialog in [`settings/+page.svelte`](../apps/web/src/routes/settings/+page.svelte) | [`test_user_endpoints.py`](../backend/tests/test_user_endpoints.py), [`test_user_service.py`](../backend/tests/test_user_service.py); unit test [`settings/page.test.ts`](../apps/web/src/routes/settings/page.test.ts) | No Playwright E2E; DSGVO.md M9 checkbox open                                      |
| Backup documented + restore test        | 3      | restic mentioned in [`DSGVO.md`](DSGVO.md), [`adr/0005`](adr/0005-verschluesselung-at-rest.md)                                                                               | [`RUNBOOK_KEY_ROTATION.md`](RUNBOOK_KEY_ROTATION.md) mentions `pg_dump`                                                                                                                                                 | No consolidated backup runbook; no restore test protocol                          |
| GlitchTip active, no PII in reports     | 2      | Compose profile `monitoring` in [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml)                                                                      | [`test_log_scrubbing.py`](../backend/tests/test_log_scrubbing.py) (logs only)                                                                                                                                           | No `sentry-sdk` in backend/web; no GlitchTip healthcheck; DSN integration missing |
| Install-Guide (Compose, Traefik, DNS)   | 3      | [`infra/dockhand/README.md`](../infra/dockhand/README.md), [`RUNBOOK_DEPLOYMENT.md`](RUNBOOK_DEPLOYMENT.md)                                                                  | Partial homelab/Tailscale notes                                                                                                                                                                                         | No single `docs/selfhost/INSTALL.md`; Traefik+DNS path fragmented                 |
| Quality gate §9                         | 6      | CI workflows green on `main`                                                                                                                                                 | Per-milestone gates (M7 pattern)                                                                                                                                                                                        | `M9_QUALITY_GATE.md` not yet created                                              |
| ZIP export self-service (Art. 20)       | 1      | `GET /api/v1/user/export` in [`user.py`](../backend/app/api/v1/endpoints/user.py)                                                                                            | [`test_export_service.py`](../backend/tests/test_export_service.py); [`export.test.ts`](../apps/web/src/lib/api/export.test.ts)                                                                                         | No HTTP endpoint integration test; no E2E download flow                           |
| GlitchTip selfhosted (DSGVO)            | 2      | Same as GlitchTip row                                                                                                                                                        | [`infra/dockhand/README.md`](../infra/dockhand/README.md) profile docs                                                                                                                                                  | Activation + SDK wiring pending                                                   |
| Incident-response runbook               | 2      | —                                                                                                                                                                            | Referenced in [`DSGVO.md`](DSGVO.md) §8                                                                                                                                                                                 | `docs/runbooks/incident-response.md` missing                                      |
| Art. 18 restriction self-service        | 1      | —                                                                                                                                                                            | [`DSGVO.md`](DSGVO.md): manual via support                                                                                                                                                                              | Document support workflow; no API (by design — API minimization)                  |
| `analytics_enabled` opt-out (DSGVO M3)  | 1      | [`user_preferences_service`](../backend/app/services/user_preferences_service.py); Settings toggle                                                                           | [`test_user_preferences.py`](../backend/tests/test_user_preferences.py), [`test_m3_foundation.py`](../backend/tests/test_m3_foundation.py)                                                                              | DSGVO.md M3 checkbox still open; E2E toggle not covered                           |
| DSFA for cloud deployment               | —      | —                                                                                                                                                                            | Deferred to M12 in [`DSGVO.md`](DSGVO.md)                                                                                                                                                                               | M9: selfhost-only scope note only                                                 |
| AV-Vertrag template (Hetzner)           | 4      | —                                                                                                                                                                            | —                                                                                                                                                                                                                       | Static template pending                                                           |
| External pentest                        | 4      | —                                                                                                                                                                            | [`M4_RELEASE_READINESS.md`](quality/M4_RELEASE_READINESS.md) P1                                                                                                                                                         | Not yet commissioned                                                              |
| `pip-audit` / `pnpm audit` CI gate      | 4      | —                                                                                                                                                                            | —                                                                                                                                                                                                                       | Not in [`.github/workflows/`](../.github/workflows/)                              |
| Style-contract lint                     | 4      | —                                                                                                                                                                            | [`UI_COMPONENT_SYSTEM.md`](frontend/UI_COMPONENT_SYSTEM.md) §9                                                                                                                                                          | Lint rule not implemented                                                         |
| LUKS + restic in Install-Guide          | 3      | —                                                                                                                                                                            | ADR-0005 M9 row                                                                                                                                                                                                         | Documentation pending                                                             |
| 5–10 beta testers + feedback            | 5      | —                                                                                                                                                                            | —                                                                                                                                                                                                                       | Program not started                                                               |
| Symptom analytics beta review           | 5      | —                                                                                                                                                                            | [`features/symptom-analytics.md`](features/symptom-analytics.md) §M9                                                                                                                                                    | Review pending                                                                    |
| Notes-in-analysis threshold review      | 5      | Worker thresholds in config                                                                                                                                                  | [`features/notes-in-analysis.md`](features/notes-in-analysis.md)                                                                                                                                                        | Config review only; per-entry opt-out → M10                                       |

## GitHub issue mapping

| Issue | Title (expected)            | Sprint scope      | Status                                  |
| ----- | --------------------------- | ----------------- | --------------------------------------- |
| #29   | Beta hardening / monitoring | 0–2, 6 (umbrella) | Open — sliced per sprint in this matrix |

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

| Area              | Current state                             | M9 constraint                         |
| ----------------- | ----------------------------------------- | ------------------------------------- |
| Cloud / local LLM | Not integrated; #147/#148 → M7-S8         | No new LLM calls                      |
| Error tracking    | Compose-only GlitchTip; no SDK            | Selfhosted + optional DSN             |
| Analytics compute | Nightly worker + `analytics_enabled` gate | No on-demand external APIs            |
| Beta feedback     | —                                         | No Hotjar/Mixpanel; GitHub/email only |
| GDPR APIs         | Delete, export, preferences exist         | Verify + document; no new endpoints   |
| Health Connect    | M8 scope                                  | Out of M9                             |

## Next sprint (1 — GDPR self-service)

Priority gaps from audit:

1. Create `docs/PRIVACY.md` and link from Settings.
2. Add Playwright `gdpr-self-service.spec.ts` (delete + ZIP export).
3. Add backend HTTP test for `GET /api/v1/user/export` if still missing.
4. Close DSGVO M3 `analytics_enabled` checkpoint with evidence.
5. Document Art. 18 support workflow in `DSGVO.md`.

No new REST endpoints planned unless audit during Sprint 1 reveals a regression.
