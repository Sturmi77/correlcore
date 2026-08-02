# M8 Sprint Status — Sleep & Health Connect

Last updated: 2026-08-02

Tracking companion to `M8_SPRINT_PLAN.md` (PR #623 — merges separately) and
[`M8_NOTES.md`](M8_NOTES.md). Records what shipped per sprint and what was
deliberately deferred. Milestone context: [`M7_M8_MILESTONE_SWAP.md`](M7_M8_MILESTONE_SWAP.md).

## Sprint audit

| Sprint | Title                        | Status                     | Evidence                                                                                               |
| ------ | ---------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------ |
| 0      | Scope + HC-bridge decision   | ✅                         | Bridge strategy → [ADR-0042](adr/0042-health-connect-bridge-strategy.md); this status doc              |
| 1      | Manual sleep fields          | ✅                         | Migration 037, `sleep_minutes`/`sleep_quality` on entries, API/sync/export, `EntryForm` Schlaf section |
| 2      | Sleep↔mood insight extension | ✅                         | `_sleep_spearman_candidates` + sleep columns in `build_design_matrix` (guarded, imputed)               |
| 3      | Native Health Connect bridge | ✅ (native untested in CI) | `HealthConnectPlugin.kt`, manifest permissions + rationale, `/health-connect` page, TS bridge          |
| 4      | HC sleep import & sync       | ✅ (foreground)            | `POST /health-connect/import` (consent-gated, manual-wins), per-field toggle, `Sync now`               |
| 5      | Device QA, docs & closeout   | ✅ (docs) / ⏳ (device QA) | this doc, quality gate, visual-QA checklist, DESIGN_DOCUMENT exit boxes, CHANGELOG                     |

## Acceptance criteria (M8 core)

| Criterion                                                            | Status                                                                 |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Art. 9 consent architecture (#31)                                    | ✅ shipped earlier                                                     |
| HC permission requested with rationale screen                        | ✅ Sprint 3 (`/health-connect`)                                        |
| No third-party sharing (on-device only)                              | ✅ ADR-0042                                                            |
| Import limited to sleep + HR; sleep-only write; no movement/location | ✅ Sprint 3/4                                                          |
| HC permissions + rationale intent-filters in manifest                | ✅ Sprint 3                                                            |
| User can disable HC sync (per-field toggle)                          | ✅ Sprint 4                                                            |
| Manual values win over import                                        | ✅ Sprint 4                                                            |
| Account delete removes imported HC data                              | ✅ cascade + test (Sprint 5)                                           |
| Copy lint / style-contract pass                                      | ✅ Sprint 5                                                            |
| Quality gate performed                                               | ✅ [`quality/M8_QUALITY_GATE.md`](quality/M8_QUALITY_GATE.md)          |
| Sleep↔mood insight surfaced                                          | ✅ Sprint 2                                                            |
| Visual QA 375/768 light+dark                                         | ⏳ manual — [`quality/M8_VISUAL_QA.md`](quality/M8_VISUAL_QA.md)       |
| Device QA (HC permission flow on sideload APK)                       | ⏳ manual — [`features/HEALTH_CONNECT.md`](features/HEALTH_CONNECT.md) |

## Deferred / split out (not M8-core exit)

| Item                                                             | Target                                    |
| ---------------------------------------------------------------- | ----------------------------------------- |
| Cycle Health Connect (`READ_MENSTRUATION`) + phase bands         | **New Cycle-HC sub-milestone**            |
| Sleep×Symptom correlations (ADR-0025 Level-1)                    | Follow-up                                 |
| Heart-rate **persistence** (needs a `resting_heart_rate` column) | Follow-up                                 |
| Extended sleep fields (bedtime, deep-sleep stages)               | Follow-up                                 |
| Native WorkManager background sleep sync                         | Follow-up (foreground `Sync now` shipped) |
| Play Store health-apps data-safety declaration                   | Play-Store exit (#429)                    |

## Verification summary

- **Backend:** affected suites green (entries, export, sync, insight engine + multivariate, preferences, api-contract, HC import incl. cascade test).
- **Web:** `svelte-check` 0 errors; unit tests for the sleep field, sleep↔mood, HC bridge gating, and import aggregation; i18n parity + no-gamification copy lint; style-contract check.
- **In-browser:** entry Schlaf section (desktop + 375 px) and the `/health-connect` rationale page rendered with no console errors.
- **Not built in CI:** the native Kotlin/Gradle path (no Android SDK) — device build + QA per [`features/HEALTH_CONNECT.md`](features/HEALTH_CONNECT.md) precede a Play/sideload release.

## PRs

S1 #624 → S2 #625 → S3 #626 → S4 #634 → S5 (this branch), each stacked on the previous.
